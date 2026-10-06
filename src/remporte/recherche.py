"""Index et recherche plein texte du DCE et de la base entreprise.

SQLite FTS5 (stdlib), tokenizer `unicode61 remove_diacritics 2` : la recherche
ignore les accents. Le texte est découpé en passages d'environ 1 200 caractères
sur les limites de paragraphes. Aucun réseau, aucune dépendance nouvelle.
"""

from __future__ import annotations

import os
import re
import sqlite3
from pathlib import Path

from remporte import lecture

_TAILLE_PASSAGE = 1200

_SCHEMA = (
    "CREATE VIRTUAL TABLE IF NOT EXISTS passages USING fts5("
    "piece UNINDEXED, passage, tokenize = 'unicode61 remove_diacritics 2')"
)


def chemin_base() -> Path:
    """Dossier de la base entreprise : ~/.remporte/base/ ou REMPORTE_BASE."""
    return Path(os.environ.get("REMPORTE_BASE") or Path.home() / ".remporte" / "base")


def indexer_dce(dossier: Path) -> int:
    """(Re)construit .remporte/index.sqlite depuis .remporte/texte/. Rend le
    nombre de passages indexés."""
    dossier = Path(dossier)
    racine_texte = dossier / ".remporte" / "texte"
    index = dossier / ".remporte" / "index.sqlite"
    index.parent.mkdir(parents=True, exist_ok=True)
    fichiers = sorted(racine_texte.rglob("*.md")) if racine_texte.is_dir() else []
    connexion = sqlite3.connect(index)
    try:
        connexion.execute("DROP TABLE IF EXISTS passages")
        connexion.execute(_SCHEMA)
        total = 0
        for fichier in fichiers:
            relatif = fichier.relative_to(racine_texte)
            # nom de la pièce d'origine : « RC.docx.md » (cache) → « RC.docx »
            piece = str(relatif)[:-3] if relatif.name.endswith(".md") else str(relatif)
            texte = fichier.read_text(encoding="utf-8", errors="replace")
            for passage in decouper_passages(texte):
                connexion.execute(
                    "INSERT INTO passages (piece, passage) VALUES (?, ?)",
                    (piece, passage),
                )
                total += 1
        connexion.commit()
    finally:
        connexion.close()
    return total


def chercher_dce(dossier: Path, requete: str, limite: int = 10) -> list[dict]:
    """Recherche plein texte dans le DCE du dossier de réponse."""
    return _chercher(Path(dossier) / ".remporte" / "index.sqlite", requete, limite)


def indexer_base(source: Path, base: Path) -> int:
    """Convertit les documents de `source` et les indexe dans `base`.

    Les textes convertis sont mis en cache dans `base/texte/`, l'index dans
    `base/index.sqlite`. Rend le nombre de passages indexés.
    """
    source = Path(source)
    base = Path(base)
    if not source.is_dir():
        raise ValueError(f"source introuvable ou pas un dossier : {source}")
    base_resolue = base.resolve()
    (base / "texte").mkdir(parents=True, exist_ok=True)
    connexion = sqlite3.connect(base / "index.sqlite")
    try:
        connexion.execute("DROP TABLE IF EXISTS passages")
        connexion.execute(_SCHEMA)
        total = 0
        for fichier in lecture.lister_fichiers(source):
            if base_resolue in fichier.resolve().parents:
                continue  # la base indexée vit dans la source : on la saute
            relatif = fichier.relative_to(source)
            conversion = lecture.convertir(fichier)
            if conversion.statut != "ok" or not conversion.texte.strip():
                continue
            cible = base / "texte" / Path(str(relatif) + ".md")
            cible.parent.mkdir(parents=True, exist_ok=True)
            cible.write_text(conversion.texte, encoding="utf-8")
            for passage in decouper_passages(conversion.texte):
                connexion.execute(
                    "INSERT INTO passages (piece, passage) VALUES (?, ?)",
                    (relatif.as_posix(), passage),
                )
                total += 1
        fiche = chemin_fiche(base)
        if fiche.exists():
            for passage in decouper_passages(fiche.read_text(encoding="utf-8")):
                connexion.execute(
                    "INSERT INTO passages (piece, passage) VALUES (?, ?)",
                    (fiche.name, passage),
                )
                total += 1
        connexion.commit()
    finally:
        connexion.close()
    return total


def chemin_fiche(base: Path | None = None) -> Path:
    """Fiche entreprise, rangée avec la base : lue en entier par les agents,
    et indexée avec les documents pour `remporte base chercher`."""
    return Path(base or chemin_base()) / "fiche-entreprise.md"


def chercher_base(base: Path, requete: str, limite: int = 10) -> list[dict]:
    """Recherche plein texte dans la base entreprise."""
    return _chercher(Path(base) / "index.sqlite", requete, limite)


def _chercher(index: Path, requete: str, limite: int) -> list[dict]:
    match = _requete_fts(requete)
    if not match or not index.exists():
        return []
    connexion = sqlite3.connect(f"file:{index}?mode=ro", uri=True)
    try:
        lignes = connexion.execute(
            "SELECT piece, passage, "
            "snippet(passages, 1, '**', '**', ' … ', 12), bm25(passages) "
            "FROM passages WHERE passages MATCH ? ORDER BY rank LIMIT ?",
            (match, limite),
        ).fetchall()
    finally:
        connexion.close()
    return [
        {"piece": piece, "passage": passage, "extrait": extrait.strip(),
         "score": score}
        for piece, passage, extrait, score in lignes
    ]


def _requete_fts(requete: str) -> str:
    """Termes quotés pour FTS5, reliés par OR : un passage qui contient une
    partie des termes remonte, et bm25 classe en tête ceux qui en ont le plus.
    Un agent écrit des requêtes de plusieurs mots ; exiger tous les termes ne
    ramenait souvent rien. Les mots d'une ou deux lettres sont ignorés."""
    termes = [t for t in re.findall(r"\w+", requete, re.UNICODE) if len(t) > 2]
    return " OR ".join(f'"{terme}"' for terme in termes)


def decouper_passages(texte: str, taille: int = _TAILLE_PASSAGE) -> list[str]:
    """Découpe un texte en passages d'environ `taille` caractères, sur les
    limites de paragraphes ; les blocs géants (tableaux) sont tranchés."""
    blocs: list[str] = []
    for brut in texte.split("\n\n"):
        brut = brut.strip()
        if not brut:
            continue
        while len(brut) > taille * 2:
            coupe = brut.rfind("\n", 0, taille)
            if coupe < taille // 2:
                coupe = taille
            blocs.append(brut[:coupe].strip())
            brut = brut[coupe:].strip()
        if brut:
            blocs.append(brut)
    passages: list[str] = []
    courant = ""
    for bloc in blocs:
        if courant and len(courant) + len(bloc) + 2 > taille:
            passages.append(courant)
            courant = bloc
        else:
            courant = f"{courant}\n\n{bloc}" if courant else bloc
    if courant:
        passages.append(courant)
    return passages
