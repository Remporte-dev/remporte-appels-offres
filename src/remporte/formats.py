"""Formats attendus par l'acheteur : contraintes de forme trouvées dans le DCE.

`detecter` lit l'inventaire des pièces et leurs textes convertis
(`.remporte/texte/`) et rend une liste de constats sourcés : soutenance ou
présentation orale, limite de pages du mémoire, classeur Excel à compléter,
cadre de réponse Word. Chaque constat porte la pièce et un extrait du texte
qui le justifie — l'agent et le relecteur doivent pouvoir vérifier.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

_LONGUEUR_EXTRAIT = 200
_PIECES_PROCEDURE = {"RC", "AAPC", "CRT"}

# Chaque motif peut porter un groupe : le nombre de pages (limite_pages).
_MOTIFS = {
    "soutenance": [
        r"\bauditions?\b|\bauditionn\w+",
        r"\bsoutenances?\b",
        r"pr[ée]sentation\s+orale",
        r"entretien\s+avec\s+les?\s+candidats",
    ],
    "limite_pages": [
        r"(?P<n>\d+)\s+pages?\s+maximum",
        r"(?P<n>\d+)\s+pages?\s+au\s+maximum",
        r"(?P<n>\d+)\s+pages?\s+maximal\w*",
        r"maximum\s+de\s+(?P<n>\d+)\s+pages?",
        r"ne\s+doit\s+pas\s+d[ée]passer\s+(?P<n>\d+)\s+pages?",
        r"limit[ée]e?s?\s+à\s+(?P<n>\d+)\s+pages?",
    ],
}

LIBELLES = {
    "soutenance": "Soutenance ou présentation orale",
    "limite_pages": "Limite de pages",
    "excel_impose": "Classeur Excel à compléter (cadre de réponse, questionnaire "
                    "ou annexe technique)",
    "cadre_word": "Cadre de réponse Word (CRT) fourni par l'acheteur",
}

_SUFFIXES_EXCEL = (".xlsx", ".xls", ".ods")

# Types de pièces qui, en classeur Excel, sont des cadres de réponse ou des
# questionnaires par nature ; les bordereaux de prix (BPU, DPGF, DQE) ne
# comptent jamais ici.
_TYPES_EXCEL_EVIDENTS = {"CRT", "QR"}
_TYPES_EXCEL_A_PREUVE = {"ANNEXE", "AUTRE"}
_PREUVE_A_COMPLETER = re.compile(r"compl[ée]ter|remplir|renseigner", re.I)


def detecter(dossier: Path, pieces: list[dict] | None = None) -> list[dict]:
    """Contraintes de forme du DCE, chacune avec sa source (pièce + extrait).

    `pieces` : inventaire du dossier (état.json) ; lu à défaut. Le texte
    converti de chaque pièce est relu dans `.remporte/texte/`.
    """
    dossier = Path(dossier)
    if pieces is None:
        chemin_etat = dossier / ".remporte" / "etat.json"
        pieces = json.loads(chemin_etat.read_text(encoding="utf-8"))["pieces"]
    constats: list[dict] = []
    for piece in pieces:
        if piece["statut"] != "ok":
            continue
        texte = _texte_converti(dossier, piece["chemin"])
        if texte is None:
            continue
        # L'audition des candidats est une étape de la procédure : elle se lit
        # dans le RC, l'avis ou le CRT. Le CCTP parle de réunions d'exécution,
        # qui donnaient de faux constats.
        motifs_soutenance = _MOTIFS["soutenance"] if piece.get("type") in _PIECES_PROCEDURE else []
        for motif in motifs_soutenance:
            trouve = re.search(motif, texte, re.I)
            if trouve:
                constats.append({
                    "type": "soutenance",
                    "piece": piece["chemin"],
                    "extrait": _extrait(texte, trouve.start(), trouve.end()),
                })
                break
        pages_vues: set[int] = set()
        for motif in _MOTIFS["limite_pages"]:
            for trouve in re.finditer(motif, texte, re.I):
                pages = int(trouve.group("n"))
                if pages in pages_vues:
                    continue
                pages_vues.add(pages)
                constats.append({
                    "type": "limite_pages",
                    "piece": piece["chemin"],
                    "pages": pages,
                    "extrait": _extrait(texte, trouve.start(), trouve.end()),
                })
        if _excel_impose(piece, texte):
            constats.append({
                "type": "excel_impose",
                "piece": piece["chemin"],
                "extrait": _extrait(texte, 0, 0),
            })
        if _cadre_word(piece):
            constats.append({
                "type": "cadre_word",
                "piece": piece["chemin"],
                "extrait": _extrait(texte, 0, 0),
            })
    return constats


def libelle(constat: dict) -> str:
    """Ligne lisible d'un constat, pour `01-pieces.md` et la sortie texte."""
    texte = LIBELLES[constat["type"]]
    if constat["type"] == "limite_pages":
        texte += f" ({constat['pages']} pages)"
    return texte


def _excel_impose(piece: dict, texte: str) -> bool:
    """Classeur Excel que le candidat doit compléter — jamais un bordereau
    de prix (BPU, DPGF, DQE), qui n'attend que des prix."""
    if not piece["chemin"].lower().endswith(_SUFFIXES_EXCEL):
        return False
    if piece["type"] in ("BPU", "DPGF", "DQE"):
        return False
    if piece["type"] in _TYPES_EXCEL_EVIDENTS:
        return True
    if piece["type"] in _TYPES_EXCEL_A_PREUVE:
        return _PREUVE_A_COMPLETER.search(texte) is not None
    return False


def _cadre_word(piece: dict) -> bool:
    """CRT fourni en .docx : le mémoire ou les réponses vont dans le fichier
    de l'acheteur, pas dans un document libre."""
    return piece["type"] == "CRT" and piece["chemin"].lower().endswith(".docx")


def _texte_converti(dossier: Path, chemin: str) -> str | None:
    cache = dossier / ".remporte" / "texte" / (chemin + ".md")
    if not cache.is_file():
        return None
    return cache.read_text(encoding="utf-8", errors="replace")


def _extrait(texte: str, debut: int, fin: int) -> str:
    """Passage qui justifie le constat, compacté, plafonné à 200 caractères."""
    if fin > debut:
        fenetre = texte[max(0, debut - 40):fin + _LONGUEUR_EXTRAIT - 40]
    else:
        fenetre = texte[:_LONGUEUR_EXTRAIT]
    return " ".join(fenetre.split())[:_LONGUEUR_EXTRAIT]
