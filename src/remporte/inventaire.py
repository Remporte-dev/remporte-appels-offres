"""Classification déterministe des pièces du DCE : type, lot, indice.

D'abord d'après le nom du fichier, puis, à défaut, d'après les 800 premiers
caractères du texte converti. Aucun appel réseau, aucun modèle : des motifs.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

TYPES = ["RC", "CCAP", "CCTP", "CRT", "AE", "BPU", "DPGF", "DQE", "AAPC",
         "DC1", "DC2", "DC4", "DUME", "ANNEXE", "QR", "AUTRE"]

# Longueur d'en-tête examinée pour la classification par contenu.
_LONGUEUR_ENTETE = 800  # le titre et la page de garde, pas le corps

# Les bornes des sigles sont écrites à la main plutôt qu'avec \b : en regex,
# _ est un caractère de mot, donc \bae\b ne coupe pas « AE_lot2 ». On exige
# seulement que le sigle ne soit pas collé à une lettre ou un chiffre.
# Ordre volontaire : les pièces de cadre d'abord, les bordereaux ensuite
# (un « 4-DPGF-AE.xls » est d'abord une DPGF), l'acte d'engagement après,
# les imprimés DC puis le reste.
_PATTERNS_NOM = [
    ("RC", re.compile(
        r"(?<![a-z0-9])rc(?![a-z0-9])"
        r"|r[èe]glement[\s_.-]*(?:de[\s_.-]*(?:la[\s_.-]*)?)?consultation", re.I)),
    ("CCAP", re.compile(
        r"(?<![a-z0-9])ccap(?![a-z0-9])"
        r"|cahier[\s_.-]*des[\s_.-]*clauses[\s_.-]*(?:administrat|particulier)", re.I)),
    ("CCTP", re.compile(
        r"(?<![a-z0-9])cctp(?![a-z0-9])"
        r"|cahier[\s_.-]*des[\s_.-]*clauses[\s_.-]*techniques"
        r"|descriptif[\s_.-]*des[\s_.-]*travaux|sp[ée]cifications[\s_.-]*techniques",
        re.I)),
    ("CRT", re.compile(
        r"(?<![a-z0-9])crt(?![a-z0-9])"
        r"|cahier[\s_.-]*des[\s_.-]*r[ée]ponses?"
        r"|cadre[\s_.-]*de[\s_.-]*r[ée]ponse", re.I)),
    ("DPGF", re.compile(
        r"(?<![a-z0-9])dpgf(?![a-z0-9])"
        r"|d[ée]composition[\s_.-]*du[\s_.-]*prix[\s_.-]*global"
        r"|d[ée]tail[\s_.-]*(?:estimatif[\s_.-]*)?quantitatif", re.I)),
    ("DQE", re.compile(
        r"(?<![a-z0-9])dqe(?![a-z0-9])"
        r"|devis[\s_.-]*quantitatif[\s_.-]*estimatif", re.I)),
    ("BPU", re.compile(
        # règles de pricing_template.py : bpu|dpgf|dqe|bordereau|annexe financ|prix
        r"(?<![a-z0-9])bpu(?![a-z0-9])|bordereau|ann(?:exe)?\.?[ _.-]*financ"
        r"|grille[\s_.-]*de[\s_.-]*prix|prix", re.I)),
    ("AE", re.compile(
        # ae_document.py : ATTRI1, « acte d'engagement », sigle AE non collé.
        r"attri\s*1|acte[-_\s]*(?:d['’]?[-_\s]*)?engagement"
        r"|(?<![a-z0-9])ae(?![a-z0-9])", re.I)),
    ("AAPC", re.compile(
        r"(?<![a-z0-9])aapc(?![a-z0-9])"
        r"|avis[\s_.-]*d['’]?appel[\s_.-]*public"
        r"|appel[\s_.-]*d['’]?offres", re.I)),
    ("DC1", re.compile(
        r"(?<![a-z0-9])dc[\s_.-]?1(?![0-9])"
        r"|pr[ée]sentation[\s_.-]*du[\s_.-]*candidat", re.I)),
    ("DC2", re.compile(
        r"(?<![a-z0-9])dc[\s_.-]?2(?![0-9])"
        r"|d[ée]claration[\s_.-]*du[\s_.-]*candidat", re.I)),
    ("DC4", re.compile(r"(?<![a-z0-9])dc[\s_.-]?4(?![0-9])", re.I)),
    ("DUME", re.compile(r"(?<![a-z0-9])dume(?![a-z0-9])", re.I)),
    ("ANNEXE", re.compile(r"annexe", re.I)),
    ("QR", re.compile(
        r"(?<![a-z0-9])qr(?![a-z0-9])"
        r"|questions?[\s_.-]*(?:et[\s_.-]*)?(?:r[ée]ponses?|candidat)", re.I)),
]

# Classification par contenu : sur texte normalisé (sans accents, apostrophes
# unifiées, blancs compactés). Lexique repris de classify.py de remporte-pi.
_PATTERNS_CONTENU = [
    ("RC", re.compile(
        r"reglement(?: particulier)? de la? consultation|modalites de remise")),
    ("CCAP", re.compile(
        r"cahier des clauses (?:administratives|particulieres)|\bccap\b")),
    ("CCTP", re.compile(
        r"cahier des clauses techniques|\bcctp\b")),
    ("CRT", re.compile(r"cahier des reponses|cadre de reponse|\bcrt\b")),
    ("AE", re.compile(r"acte d'?engagement|attri ?1")),
    ("DPGF", re.compile(
        r"decomposition du prix global|detail (?:estimatif )?quantitatif"
        r"|\bdpgf\b")),
    ("DQE", re.compile(r"devis quantitatif estimatif|\bdqe\b")),
    ("BPU", re.compile(r"bordereau des prix|\bbpu\b")),
    ("AAPC", re.compile(
        r"avis d'appel public|appel public a la concurrence")),
    ("DC1", re.compile(r"presentation du candidat")),
    ("DC2", re.compile(r"declaration du candidat")),
    ("DUME", re.compile(r"\bdume\b|declaration unique du marche europeen")),
]


@dataclass
class Classement:
    """Résultat de classification d'une pièce."""

    type: str            # un des TYPES
    lot: str | None      # « 2 » si « lot 2 », « LOT02 », « L2_ » dans le nom
    indice: str          # "nom" | "contenu" | "aucun"


def classer(chemin: Path, texte: str) -> Classement:
    """Type de la pièce, d'après le nom puis, à défaut, le début du texte."""
    chemin = Path(chemin)
    lot = _lot_du_nom(chemin.name)
    for type_, motif in _PATTERNS_NOM:
        if motif.search(chemin.name):
            return Classement(type_, lot, "nom")
    entete = _normaliser(texte[:_LONGUEUR_ENTETE])
    for type_, motif in _PATTERNS_CONTENU:
        if motif.search(entete):
            return Classement(type_, lot, "contenu")
    return Classement("AUTRE", lot, "aucun")


def pieces_attendues_absentes(types: set[str]) -> list[str]:
    """Messages sur les pièces attendues manquantes (RC toujours ; CRT à dire)."""
    messages: list[str] = []
    if "RC" not in types:
        messages.append(
            "RC (règlement de consultation) non identifié : pièce attendue du DCE."
        )
    if "CRT" not in types:
        messages.append(
            "CRT (cahier des réponses) absent : le plan du mémoire suivra le RC."
        )
    return messages


def _normaliser(texte: str) -> str:
    """Minuscules, sans accents, apostrophes unifiées, blancs compactés."""
    sans_accents = "".join(
        caractere
        for caractere in unicodedata.normalize("NFKD", texte)
        if not unicodedata.combining(caractere)
    )
    return " ".join(
        sans_accents.lower().replace("’", "'").replace("'", "'").split()
    )


_LOT_RE = re.compile(r"(?:\blots?[\s_.-]*0*|\bl0*)([1-9]\d*)", re.I)


def _lot_du_nom(nom: str) -> str | None:
    trouve = _LOT_RE.search(nom)
    return str(int(trouve.group(1))) if trouve else None
