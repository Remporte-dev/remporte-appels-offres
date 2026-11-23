"""Dossier des pièces à remettre pour le marché ou pour un lot retenu."""

from __future__ import annotations

import re
from pathlib import Path

from remporte import espace, lots
from remporte.chemins import diagnostic_chemin_trop_long


def chemin_dossier_lot(dossier: Path, lot: str | None = None) -> Path:
    """Détermine le dossier de remise avant toute écriture."""
    dossier = Path(dossier).resolve()
    tri = lots.lire(dossier)
    choix = tri["choix"] if tri else None
    retenus = choix["retenus"] if choix else []
    if lot is not None and lot not in retenus:
        raise espace.Erreur(f"Le lot {lot} n'a pas été retenu.")

    reponse = dossier / "reponse"
    if reponse.is_symlink() or (reponse.exists() and not reponse.is_dir()):
        raise espace.Erreur("Le dossier de remise est inaccessible.")
    if tri is None or tri["allotissement"] != "lots":
        return reponse
    if not retenus:
        raise espace.Erreur("Choisissez d'abord les lots auxquels vous souhaitez répondre.")
    if lot is None:
        if len(retenus) > 1:
            raise espace.Erreur(f"Choisissez le lot avec --lot parmi : {', '.join(retenus)}.")
        lot = retenus[0]

    prefixe = f"Lot {lot} - "
    existants = []
    if reponse.is_dir():
        existants = [p for p in reponse.iterdir() if p.name.startswith(prefixe) and p.is_dir()]
    if len(existants) > 1:
        raise espace.Erreur(f"Plusieurs dossiers de remise existent pour le Lot {lot}.")
    if existants:
        cible = existants[0]
    else:
        intitule = next(entree["intitule"] for entree in tri["lots"] if entree["id"] == lot)
        if len(intitule) > 60:
            coupe = intitule[:60]
            intitule = coupe.rsplit(" ", 1)[0] if " " in coupe else coupe
        intitule = re.sub(r'[<>:"/\\|?*\x00-\x1f\x7f-\x9f]', "-", intitule).strip(" .")
        cible = reponse / (prefixe + (intitule or "-"))
    if cible.is_symlink() or (cible.exists() and not cible.is_dir()):
        raise espace.Erreur(f"Le dossier de remise du lot {lot} est inaccessible.")
    return cible


def dossier_lot(dossier: Path, lot: str | None = None) -> Path:
    """Crée le dossier des pièces à remettre et rend son chemin absolu."""
    try:
        cible = chemin_dossier_lot(dossier, lot)
        cible.mkdir(parents=True, exist_ok=True)
    except OSError as erreur:
        message = diagnostic_chemin_trop_long(erreur) or "Le dossier de remise est inaccessible."
        raise espace.Erreur(message) from erreur
    return cible
