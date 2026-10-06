"""Extraction déterministe d'un cadre de réponse depuis la pièce de l'acheteur.

Port de `remporte-pi/apps/pipe/src/remporte_ai/ingestion/response_frame.py`
(lu sur origin/main). Deux voies : les paragraphes d'un style dédié du DOCX
(trame bien faite), puis les phrases « le candidat … » dans le texte converti.
En dessous de trois points, le cadre est jugé inexploitable : origine « aucune ».
"""

from __future__ import annotations

import re
from collections import Counter
import unicodedata
from pathlib import Path

from remporte.lecture import convertir

_DEMANDE_CANDIDAT = re.compile(
    r"\b(?:le candidat|le soumissionnaire|l[' ]entreprise)\s+"
    r"(?:precise|decrit|detaille|fournit|indique|justifie"
    r"|precisera|decrira|detaillera|fournira|indiquera|justifiera)\b"
)
_STYLE_TITRE = re.compile(r"^(?:heading|titre|title)(?:\s+\d+)?(?:\s|$)")

_SEUIL_POINTS = 3
_LIMITE_TITRE = 140


def _normaliser(texte: str) -> str:
    """Normalise un texte pour les comparaisons et empreintes stables."""
    sans_accents = "".join(
        caractere
        for caractere in unicodedata.normalize("NFKD", texte)
        if not unicodedata.combining(caractere)
    )
    return " ".join(sans_accents.lower().replace("’", "'").split())


def _est_demande_candidat(texte: str) -> bool:
    return bool(_DEMANDE_CANDIDAT.search(_normaliser(texte)))


def _est_titre(nom_style: str) -> bool:
    return bool(_STYLE_TITRE.match(_normaliser(nom_style)))


def _est_style_dedie(style) -> bool:
    """Écarte les styles Word intégrés, notamment le style Normal."""
    return not style.builtin


def _finalise(origine: str, points_bruts: list[tuple[str, str]]) -> dict:
    """Applique le seuil minimal d'un cadre exploitable."""
    if len(points_bruts) < _SEUIL_POINTS:
        return {"origine": "aucune", "points": []}
    points = [
        {
            "numero": index,
            "titre": _tronquer(texte),
            "demande": texte,
            "niveau": chapitre,
        }
        for index, (texte, chapitre) in enumerate(points_bruts, 1)
    ]
    return {"origine": origine, "points": points}


def _tronquer(texte: str, limite: int = _LIMITE_TITRE) -> str:
    return texte if len(texte) <= limite else texte[: limite - 1].rstrip() + "…"


def _points_par_style(chemin: Path) -> list[tuple[str, str]]:
    """Extrait les paragraphes du style dédié le plus représentatif."""
    from docx import Document

    document = Document(str(chemin))
    paragraphes = list(document.paragraphs)
    candidats: list[tuple[int, int, str]] = []

    for style in document.styles:
        try:
            if not _est_style_dedie(style):
                continue
        except Exception:  # noqa: BLE001 — style exotique : ignoré
            continue
        indices = [
            index
            for index, paragraphe in enumerate(paragraphes)
            if (
                paragraphe.text.strip()
                and paragraphe.style
                and paragraphe.style.name == style.name
                and _est_demande_candidat(paragraphe.text)
            )
        ]
        if indices:
            candidats.append((len(indices), indices[0], style.name))

    if not candidats:
        return []

    _, _, nom_style = min(
        candidats,
        key=lambda candidat: (-candidat[0], candidat[1], candidat[2]),
    )

    chapitre = ""
    points: list[tuple[str, str]] = []
    for paragraphe in paragraphes:
        texte = " ".join(paragraphe.text.split())
        if not texte:
            continue
        nom = paragraphe.style.name if paragraphe.style else ""
        if _est_titre(nom):
            chapitre = texte
            continue
        if nom == nom_style:
            points.append((texte, chapitre))
    return points


def _points_par_motif(texte: str) -> list[tuple[str, str]]:
    """Extrait les demandes explicites depuis un texte déjà converti."""
    chapitre = ""
    points: list[tuple[str, str]] = []
    for ligne in texte.splitlines():
        contenu = " ".join(ligne.split())
        titre = re.match(r"^#{1,6}\s+(.+?)\s*$", contenu)
        if titre:
            chapitre = titre.group(1)
            continue
        if contenu and _est_demande_candidat(contenu):
            points.append((contenu, chapitre))
    return points


# « {PP 001.}\t2.3.1 : Qualité des équipes : Le candidat précise …\t8 » :
# liste d'exigences numérotées, fréquente en fin de CRT (la dernière colonne
# est la page). Les styles n'en voient qu'une partie ; quand elle existe,
# c'est elle qui fait foi, car l'acheteur note point par point.
_LIGNE_EXIGENCE = re.compile(
    r"^\{?\s*([A-Z]{1,6}[ _-]?\d{1,4})\s*\.?\s*\}?\s+(.+?)(?:\s+\d{1,4})?\s*$",
    re.MULTILINE,
)
_SEUIL_LISTE = 5


def _points_par_liste(texte: str) -> list[tuple[str, str]]:
    """Exigences numérotées (identifiant + chapitre + demande), sans doublon.

    On garde le préfixe d'identifiant le plus fréquent (« PP ») : c'est lui qui
    signe la liste de l'acheteur, quelle que soit la tournure de la demande.
    """
    lignes: list[tuple[str, str, str]] = []
    for trouve in _LIGNE_EXIGENCE.finditer(texte):
        identifiant = " ".join(trouve.group(1).replace("_", " ").replace("-", " ").split())
        prefixe = re.match(r"[A-Z]+", identifiant).group(0)
        lignes.append((prefixe, identifiant, trouve.group(2).replace("\xa0", " ").strip()))
    if not lignes:
        return []
    prefixes = Counter(prefixe for prefixe, _, _ in lignes)
    dominant, nombre = prefixes.most_common(1)[0]
    if nombre < _SEUIL_LISTE:
        return []
    points: list[tuple[str, str]] = []
    vus: set[str] = set()
    for prefixe, identifiant, corps in lignes:
        if prefixe != dominant or identifiant in vus:
            continue
        vus.add(identifiant)
        chapitre, _, demande = corps.rpartition(" : ")
        if not chapitre:
            demande = corps
        points.append((f"{identifiant} — {' '.join(demande.split())}", " ".join(chapitre.split())))
    return points


def identifiant_du_point(point: dict) -> str | None:
    """« PP 009 » d'un point issu d'une liste numérotée, sinon None."""
    trouve = re.match(r"([A-Z]+) ?(\d+) — ", point["titre"])
    return f"{trouve.group(1)} {trouve.group(2)}" if trouve else None


def couverture(dossier: Path, resultat: dict) -> list[dict] | None:
    """Pour chaque exigence numérotée du CRT : les sections qui la citent.

    Une section « cite » l'exigence quand son texte contient l'identifiant
    (« PP 009 », tolérant sur séparateurs et zéros de tête). Rend une entrée
    {point, identifiant, sections (noms de fichiers), couverte} par point, ou
    None si le cadre n'est pas une liste numérotée (origine != « liste ») : le
    contrôle point par point n'a alors pas de sens.
    """
    if resultat.get("origine") != "liste":
        return None
    sections = {
        fichier.name: fichier.read_text(encoding="utf-8", errors="replace")
        for fichier in sorted((Path(dossier) / "sections").glob("*.md"))
    }
    entrees: list[dict] = []
    for point in resultat["points"]:
        identifiant = identifiant_du_point(point)
        citantes: list[str] = []
        if identifiant:
            prefixe, numero = identifiant.split()
            motif = rf"(?<![A-Za-z]){prefixe}[ _-]?0*{int(numero)}(?!\d)"
            citantes = [
                nom for nom, texte in sections.items() if re.search(motif, texte)
            ]
        entrees.append({
            "point": point,
            "identifiant": identifiant,
            "sections": citantes,
            "couverte": bool(citantes),
        })
    return entrees


def extraire_cadre(piece: Path) -> dict:
    """Trame imposée par l'acheteur (CRT Word).

    Rend {"origine": "liste"|"styles"|"motifs"|"aucune", "points": [{"numero", "titre",
    "demande", "niveau"}]} où `titre` est la demande (tronquée pour l'affichage),
    `demande` le texte intégral du paragraphe et `niveau` le chapitre (titre de
    section) sous lequel la demande figure.
    """
    piece = Path(piece)
    conversion = convertir(piece)
    liste = _points_par_liste(conversion.texte) if conversion.statut == "ok" else []
    if liste:
        return _finalise("liste", liste)
    if piece.suffix.lower() == ".docx":
        points = _points_par_style(piece)
        if points:
            return _finalise("styles", points)
        return _finalise("motifs", _points_par_motif(conversion.texte))
    if conversion.statut != "ok":
        return {"origine": "aucune", "points": []}
    return _finalise("motifs", _points_par_motif(conversion.texte))
