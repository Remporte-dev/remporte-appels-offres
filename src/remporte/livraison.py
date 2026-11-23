"""Dossier des pièces à remettre pour le marché ou pour un lot retenu."""

from __future__ import annotations

import json
import re
from pathlib import Path

from remporte import espace


def lire_tri(dossier: Path) -> tuple[str | None, dict[str, str], list[str]]:
    """Lit l'allotissement, les intitulés et le choix inscrit dans le tri."""
    chemin = dossier / "memoire" / "lots.json"
    try:
        tri = json.loads(chemin.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None, {}, []
    except (OSError, ValueError) as erreur:
        raise espace.Erreur("Le tri des lots est illisible.") from erreur
    if (not isinstance(tri, dict) or tri.get("allotissement") not in ("lots", "unique")
            or not isinstance(tri.get("lots"), list)):
        raise espace.Erreur("Le tri des lots est incomplet.")

    lots = {}
    for lot in tri["lots"]:
        if not isinstance(lot, dict):
            raise espace.Erreur("Un lot est incomplet dans le tri.")
        id_, intitule = lot.get("id"), lot.get("intitule")
        if (not isinstance(id_, str) or not re.fullmatch(r"[\w. -]+", id_)
                or id_ in (".", "..") or id_ in lots
                or not isinstance(intitule, str) or not intitule.strip()):
            raise espace.Erreur("Un numéro ou un intitulé de lot est incorrect dans le tri.")
        lots[id_] = intitule

    choix = tri.get("choix")
    if choix is None:
        return tri["allotissement"], lots, []
    retenus = choix.get("retenus") if isinstance(choix, dict) else None
    if (not isinstance(retenus, list)
            or any(not isinstance(id_, str) or id_ not in lots for id_ in retenus)
            or len(set(retenus)) != len(retenus)):
        raise espace.Erreur("Le choix des lots ne correspond pas au tri.")
    return tri["allotissement"], lots, retenus


def chemin_dossier_lot(dossier: Path, lot: str | None = None) -> Path:
    """Détermine le dossier de remise avant toute écriture."""
    dossier = Path(dossier).resolve()
    allotissement, lots, retenus = lire_tri(dossier)
    if lot is not None and lot not in retenus:
        raise espace.Erreur(f"Le lot {lot} n'a pas été retenu.")

    reponse = dossier / "reponse"
    if reponse.is_symlink() or (reponse.exists() and not reponse.is_dir()):
        raise espace.Erreur("Le dossier de remise est inaccessible.")
    if allotissement != "lots":
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
        intitule = re.sub(r'[<>:"/\\|?*\x00-\x1f\x7f-\x9f]', "-", lots[lot]).strip(" .")
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
        raise espace.Erreur("Le dossier de remise est inaccessible.") from erreur
    return cible
