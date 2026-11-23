"""Dossier de réponse : initialisation, état d'avancement, recherche du dossier.

Arborescence : inventaire et étapes à la racine, dce/, memoire/, analyse/,
sections/, export/, .remporte/ (etat.json, texte/, index.sqlite). Une étape-fichier est
« faite » quand elle n'a plus aucun marqueur `<!-- à remplir -->`.
"""

from __future__ import annotations

import datetime
import importlib.resources
import json
import re
from pathlib import Path
from tempfile import TemporaryDirectory

from remporte import formats, inventaire, recherche
from remporte.chemins import masquer_espace
from remporte.lecture import convertir, decompresser_avec_etat, lister_fichiers

ETAPES = ["pieces", "analyse", "go-no-go", "plan", "redaction", "relecture",
          "export"]

MARQUEUR = "<!-- à remplir -->"

FICHIERS_ETAPES = {
    "pieces": "01-pieces.md",
    "go-no-go": "03-go-no-go.md",
    "plan": "04-plan.md",
    "relecture": "05-relecture.md",
}

# Pièces dont le remplissage dans le format de l'acheteur est le métier de
# Remporte : la ligne correspondante est ajoutée à 01-pieces.md.
PIECES_REMPLISSABLES = {"AE", "BPU", "DPGF", "DQE"}

def _nom(chemin: str) -> str:
    """Nom de pièce sûr dans 01-pieces.md : un nom venu du DCE ne casse ni le
    tableau ni le code en ligne."""
    return chemin.replace("|", "/").replace("`", "'")


_RE_LIGNE_SECTION = re.compile(r"^- \[([ x])\] (\d+)(?:\s*[—–-]+\s*(.*))?$", re.M)


class Erreur(Exception):
    """Erreur d'usage, à afficher telle quelle à l'utilisateur."""


def initialiser(source: Path, dossier: Path, *, forcer: bool = False) -> dict:
    """Crée l'arborescence, convertit et classe les pièces, indexe le DCE.

    Refuse si `dossier` contient déjà `.remporte/`, sauf `forcer=True` — qui
    préserve les fichiers remplis et retire les pièces importées devenues
    absentes de la source. Rend les données écrites dans etat.json.
    """
    source = Path(source)
    dossier = Path(dossier)
    if not source.exists():
        raise Erreur(f"source introuvable : {source}")
    if (dossier / ".remporte").exists() and not forcer:
        raise Erreur(
            f"{dossier} contient déjà un dossier de réponse (.remporte/). "
            "Relancez avec --forcer pour réindexer sans toucher aux fichiers "
            "remplis."
        )
    for sous_dossier in ("dce", "memoire", "analyse", "sections", "export", ".remporte/texte"):
        (dossier / sous_dossier).mkdir(parents=True, exist_ok=True)
    masquer_espace(dossier / ".remporte")

    racine_dce = dossier / "dce"
    precedentes = _pieces_importees(dossier)
    importees, retirees = _importer_dce(source, racine_dce, precedentes)
    fichiers = lister_fichiers(racine_dce)
    pieces = _lister_et_convertir(fichiers, dossier)
    _ecrire_inventaire(dossier, pieces, source)
    _copier_gabarits(dossier, forcer)
    recherche.indexer_dce(dossier)

    donnees = {
        "version": 1,
        "cree_le": datetime.datetime.now().isoformat(timespec="seconds"),
        "source": str(source.resolve()),
        "pieces": pieces,
        "importees": sorted(importees),
        "retirees": retirees,
    }
    (dossier / ".remporte" / "etat.json").write_text(
        json.dumps(donnees, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return donnees


def _pieces_importees(dossier: Path) -> set[str]:
    """Chemins importés, distincts des ajouts manuels de l'inventaire."""
    chemin = dossier / ".remporte" / "etat.json"
    try:
        donnees = json.loads(chemin.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return set()
    if not isinstance(donnees, dict):
        return set()
    importees = donnees.get("importees")
    if not isinstance(importees, list):
        # Un dossier plus ancien ne distingue pas les pièces importées des pièces
        # ajoutées à la main : on n'en retire aucune.
        return set()
    return {chemin for chemin in importees if isinstance(chemin, str)}


def _importer_dce(source: Path, racine: Path, precedentes: set[str]) -> tuple[set[str], list[str]]:
    if source.samefile(racine):
        chemins = {p.relative_to(racine).as_posix() for p in lister_fichiers(racine)}
        return precedentes & chemins, []

    # Lire à part la nouvelle source isole ses pièces, y compris celles des ZIP imbriqués.
    with TemporaryDirectory(dir=racine.parent / ".remporte") as temporaire:
        base = Path(temporaire)
        fichiers, complet = decompresser_avec_etat(source, base)
        if precedentes and not complet:
            raise Erreur(f"Réimport du DCE arrêté : extraction incomplète de {source}")
        importees = {p.relative_to(base).as_posix() for p in fichiers}
        racine_resolue = racine.resolve()
        for chemin in importees:
            if not (racine / chemin).parent.resolve().is_relative_to(racine_resolue):
                raise Erreur(f"Pièce du DCE hors du dossier de réponse : {chemin}")

        retirees = _retirer_disparues(racine, precedentes - importees)
        for fichier in fichiers:
            destination = racine / fichier.relative_to(base)
            destination.parent.mkdir(parents=True, exist_ok=True)
            fichier.replace(destination)
    return importees, retirees


def _retirer_disparues(racine: Path, disparues: set[str]) -> list[str]:
    retirees: list[str] = []
    racine_texte = racine.parent / ".remporte" / "texte"
    for chemin in sorted(disparues):
        for base, nom in ((racine, chemin), (racine_texte, chemin + ".md")):
            piece = base / nom
            if not piece.resolve().is_relative_to(base.resolve()) or not piece.is_file():
                continue
            piece.unlink()
            if base == racine:
                retirees.append(chemin)
            for parent in piece.parents:
                if parent == base or any(parent.iterdir()):
                    break
                parent.rmdir()
    return retirees


def _lister_et_convertir(fichiers: list[Path], dossier: Path) -> list[dict]:
    """Convertit chaque pièce du DCE, met en cache le texte, classe, rend."""
    racine_dce = dossier / "dce"
    racine_texte = dossier / ".remporte" / "texte"
    pieces: list[dict] = []
    for fichier in fichiers:
        relatif = fichier.relative_to(racine_dce)
        conversion = convertir(fichier)
        if conversion.statut == "ok":
            cache = racine_texte / Path(str(relatif) + ".md")
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(conversion.texte, encoding="utf-8")
        classement = inventaire.classer(fichier, conversion.texte)
        pieces.append({
            "chemin": relatif.as_posix(),
            "type": classement.type,
            "lot": None,
            "indice": classement.indice,
            "statut": conversion.statut,
            "pages": conversion.pages,
            "texte": len(conversion.texte),
            "motif": conversion.motif,
        })
    return pieces


def _ecrire_inventaire(dossier: Path, pieces: list[dict], source: Path) -> None:
    """Génère 01-pieces.md : tableau, pièces non converties, attendues, ligne Remporte."""
    lignes = [
        "# Inventaire des pièces du DCE",
        "",
        f"Source : `{source}`. Généré par `remporte init`, ne pas remplir à la main.",
        "",
        "## Inventaire",
        "",
        "| Type | Lot | Pièce | Statut | Pages | Texte |",
        "|---|---|---|---|---|---|",
    ]
    for piece in pieces:
        pages = str(piece["pages"]) if piece["pages"] is not None else "—"
        texte = f"{piece['texte']:,}".replace(",", " ") + " car." if piece["texte"] else "—"
        lignes.append(
            f"| {piece['type']} | — | `dce/{_nom(piece['chemin'])}` "
            f"| {piece['statut']} | {pages} | {texte} |"
        )
    problemes = [p for p in pieces if p["statut"] != "ok"]
    lignes += ["", "## Pièces non converties", ""]
    if problemes:
        lignes += [
            f"- `dce/{_nom(p['chemin'])}` : {p['statut']} — {p['motif'] or 'sans motif'}"
            for p in problemes
        ]
    else:
        lignes.append("Toutes les pièces ont été converties.")
    manquantes = inventaire.pieces_attendues_absentes({p["type"] for p in pieces})
    lignes += ["", "## Pièces attendues manquantes", ""]
    lignes += [f"- {message}" for message in manquantes] if manquantes \
        else ["Rien à signaler."]
    constats = formats.detecter(dossier, pieces)
    lignes += ["", "## Formats attendus", ""]
    if constats:
        lignes += [
            f"- {formats.libelle(c)} — `dce/{_nom(c['piece'])}` : « {c['extrait']} »"
            for c in constats
        ]
    else:
        lignes.append("Aucune contrainte de forme détectée.")
    remplissables = [p for p in pieces if p["type"] in PIECES_REMPLISSABLES]
    if remplissables:
        lignes += ["", "## Pièces à remplir dans le format de l'acheteur", ""]
        for piece in remplissables:
            guide = "chiffrage" if piece["type"] in {"BPU", "DPGF", "DQE"} else "excel"
            lignes.append(
                f"- `dce/{_nom(piece['chemin'])}` ({piece['type']}) : à remplir dans le "
                "fichier de l'acheteur, sans toucher à ses formules "
                f"(`remporte guide {guide}`)"
            )
    (dossier / "01-pieces.md").write_text(
        "\n".join(lignes) + "\n", encoding="utf-8"
    )


def _gabarit(nom: str) -> str | None:
    """Texte d'origine d'un gabarit, pour reconnaître un fichier pas encore touché."""
    fichier = importlib.resources.files("remporte") / "gabarits" / nom
    return fichier.read_text(encoding="utf-8") if fichier.is_file() else None


def _copier_gabarits(dossier: Path, forcer: bool) -> None:
    """Copie les gabarits du dossier de réponse à sa racine.

    Avec `forcer`, un fichier déjà rempli (plus aucun marqueur) n'est jamais
    touché ; un fichier entamé est réinitialisé.
    """
    racine = importlib.resources.files("remporte") / "gabarits"
    for ressource in racine.iterdir():
        if ressource.name.startswith(".") or ressource.name == "analyse-lot.md":
            continue
        cible = dossier / ressource.name
        if cible.exists():
            if not forcer:
                continue
            if MARQUEUR not in cible.read_text(encoding="utf-8", errors="replace"):
                continue
        cible.write_bytes(ressource.read_bytes())


def etat(dossier: Path) -> dict:
    """État d'avancement par étape : faite / en_cours / a_faire, marqueurs,
    prochaine étape et commande `remporte guide <étape>` à lancer."""
    from remporte import lots

    dossier = Path(dossier)
    if not (dossier / ".remporte").is_dir():
        raise Erreur(
            f"{dossier} n'est pas un dossier de réponse (pas de .remporte/). "
            "Lancez `remporte init <DCE>` d'abord."
        )
    brut: dict[str, dict] = {}
    for etape, nom_fichier in FICHIERS_ETAPES.items():
        fichier = dossier / nom_fichier
        if not fichier.exists():
            brut[etape] = {"etat": "a_faire", "marqueurs": None}
            continue
        texte = fichier.read_text(encoding="utf-8", errors="replace")
        restants = texte.count(MARQUEUR)
        if restants == 0:
            etat_etape = "faite"
        elif texte == _gabarit(nom_fichier):
            etat_etape = "a_faire"
        else:
            etat_etape = "en_cours"
        brut[etape] = {
            "etat": etat_etape,
            "marqueurs": restants,
        }
    bilan_lots = lots.etat(dossier)
    brut["analyse"] = {"etat": bilan_lots["etat"], "marqueurs": None}
    brut["redaction"] = _etat_redaction(dossier)
    dossier_html = dossier / "export" / "dossier.html"
    brut["export"] = {
        "etat": "faite" if dossier_html.exists() else "a_faire",
        "marqueurs": None,
    }
    etapes = {etape: brut[etape] for etape in ETAPES}
    for etape in ETAPES:
        etapes[etape]["guide"] = f"remporte guide {etape}"
    prochaine = next((e for e in ETAPES if etapes[e]["etat"] != "faite"), None)
    return {
        "dossier": str(dossier.resolve()),
        "etapes": etapes,
        "lots": bilan_lots,
        "prochaine": prochaine,
        "commande": f"remporte guide {prochaine}" if prochaine else None,
    }


def _etat_redaction(dossier: Path) -> dict:
    """`redaction` est faite quand chaque section du plan a son fichier sans
    marqueur ; `marqueurs` compte ici les sections restantes."""
    sections = sections_plan(dossier)
    if not sections:
        return {"etat": "a_faire", "marqueurs": None}
    restantes = [s for s in sections if not s["faite"]]
    if not restantes:
        return {"etat": "faite", "marqueurs": 0}
    return {"etat": "en_cours", "marqueurs": len(restantes)}


_MOTS_MINIMUM = 50


def sections_plan(dossier: Path) -> list[dict]:
    """Sections annoncées par 04-plan.md (lignes `- [ ] NN — Titre`), avec
    l'état de leur fichier dans sections/."""
    dossier = Path(dossier)
    fichier_plan = dossier / "04-plan.md"
    if not fichier_plan.exists():
        return []
    texte = fichier_plan.read_text(encoding="utf-8", errors="replace")
    sections: list[dict] = []
    for trouve in _RE_LIGNE_SECTION.finditer(texte):
        numero = trouve.group(2)
        titre = (trouve.group(3) or "").strip()
        fichiers = sorted((dossier / "sections").glob(f"{numero}-*.md"), key=lambda p: p.as_posix())
        fichier = fichiers[0] if fichiers else None
        faite = False
        if fichier is not None:
            contenu = fichier.read_text(encoding="utf-8", errors="replace")
            # Une section vide ou réduite à son titre n'est pas rédigée.
            faite = MARQUEUR not in contenu and len(contenu.split()) >= _MOTS_MINIMUM
        sections.append({
            "numero": numero,
            "titre": titre,
            "fichier": fichier.name if fichier else None,
            "faite": faite,
        })
    return sections


def trouver_dossier(depart: Path) -> Path | None:
    """Remonte depuis `depart` jusqu'au premier dossier contenant .remporte/etat.json."""
    courant = Path(depart).resolve()
    for candidat in (courant, *courant.parents):
        if (candidat / ".remporte" / "etat.json").is_file():
            return candidat
    return None
