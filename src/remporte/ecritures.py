"""Publication groupée des fichiers d'un dossier de réponse."""

from __future__ import annotations

import errno
import shutil
import stat
from collections.abc import Collection
from pathlib import Path
from tempfile import TemporaryDirectory

from remporte.chemins import diagnostic_chemin_trop_long
from remporte.espace import Erreur


def publier(dossier: Path, fichiers: dict[Path, bytes], *,
            exclusifs: Collection[Path] = (), conflit: str | None = None) -> None:
    """Prépare les fichiers et sauvegarde les originaux avant tout remplacement."""
    if not fichiers:
        return
    sauvegardes: dict[Path, Path] = {}
    prepares: dict[Path, Path] = {}
    publies: list[Path] = []
    dossiers_crees: list[Path] = []
    cible = next(iter(fichiers))
    try:
        interne = dossier / ".remporte"
        if interne.resolve() != interne:
            raise OSError
        with TemporaryDirectory(dir=interne) as attente:
            attente = Path(attente)
            for rang, (cible, contenu) in enumerate(fichiers.items()):
                if cible.parent.resolve() != cible.parent:
                    raise OSError
                try:
                    mode = cible.lstat().st_mode
                except FileNotFoundError:
                    mode = None
                if mode is not None:
                    if cible in exclusifs:
                        raise FileExistsError
                    if not stat.S_ISREG(mode):
                        raise OSError
                    sauvegardes[cible] = attente / f"avant-{rang}"
                    shutil.copy2(cible, sauvegardes[cible])
                prepare = attente / f"apres-{rang}"
                with prepare.open("xb") as fichier:
                    fichier.write(contenu)
                if mode is not None:
                    prepare.chmod(stat.S_IMODE(mode))
                prepares[cible] = prepare

            try:
                for cible, prepare in prepares.items():
                    _creer_parents(cible.parent, dossier, dossiers_crees)
                    if cible not in sauvegardes:
                        # Réserve le nom sans écraser un fichier arrivé entre-temps.
                        with cible.open("xb"):
                            publies.append(cible)
                    prepare.replace(cible)
                    if cible in sauvegardes:
                        publies.append(cible)
            except OSError:
                for publie in reversed(publies):
                    if publie in sauvegardes:
                        sauvegardes[publie].replace(publie)
                    else:
                        publie.unlink()
                for parent in reversed(dossiers_crees):
                    try:
                        parent.rmdir()
                    except OSError as erreur:
                        if erreur.errno not in (errno.ENOTEMPTY, errno.EEXIST):
                            raise
                raise
    except PermissionError:
        raise Erreur(f"Fermez {cible.name} puis relancez.") from None
    except OSError as erreur:
        if isinstance(erreur, FileExistsError) and conflit and cible in exclusifs:
            raise Erreur(conflit.format(nom=cible.name)) from None
        diagnostic = diagnostic_chemin_trop_long(erreur)
        raise Erreur(diagnostic or f"Impossible d'écrire le fichier {cible.name} "
                     "dans le dossier de réponse.") from None


def _creer_parents(parent: Path, dossier: Path, crees: list[Path]) -> None:
    if parent == dossier or parent.is_dir():
        return
    _creer_parents(parent.parent, dossier, crees)
    try:
        parent.mkdir()
    except FileExistsError:
        if not parent.is_dir():
            raise
    else:
        crees.append(parent)
