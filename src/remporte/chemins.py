"""Diagnostics et attributs des chemins propres aux systèmes de fichiers."""

from __future__ import annotations

import errno
import os
import sys
from pathlib import Path


def diagnostic_chemin_trop_long(erreur: BaseException) -> str | None:
    """Ne présume pas une limite fixe : les chemins longs peuvent être autorisés."""
    if not isinstance(erreur, OSError):
        return None
    chemin = erreur.filename2 or erreur.filename
    code_windows = getattr(erreur, "winerror", None)
    # Windows peut signaler un composant trop long comme nom invalide (123).
    composant_long = code_windows == 123 and chemin and any(
        len(partie.encode("utf-16-le", errors="surrogatepass")) > 510
        for partie in os.fsdecode(chemin).replace("\\", "/").split("/")
    )
    if erreur.errno != errno.ENAMETOOLONG and code_windows != 206 and not composant_long:
        return None
    precision = f" : {chemin}" if chemin else ""
    return (f"Chemin trop long pour le système{precision}. "
            "Raccourcissez le nom du fichier ou placez le dossier plus près "
            "de la racine du disque.")


def masquer_espace(repertoire: Path) -> None:
    """Demande l'attribut caché sous Windows sans bloquer l'initialisation."""
    if sys.platform != "win32":
        return
    import ctypes

    try:
        noyau = ctypes.windll.kernel32
        chemin = str(repertoire.resolve())
        attributs = noyau.GetFileAttributesW(chemin)
        if attributs != -1 and not attributs & 0x2:
            noyau.SetFileAttributesW(chemin, attributs | 0x2)
    except (AttributeError, OSError):
        pass
