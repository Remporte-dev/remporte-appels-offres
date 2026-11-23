"""Publication groupée des fichiers d'un dossier de réponse."""

from __future__ import annotations

import errno
import os
import shutil
import stat
import sys
import time
from collections.abc import Collection
from contextlib import suppress
from pathlib import Path
from typing import BinaryIO
from uuid import uuid4

from remporte.chemins import diagnostic_chemin_trop_long
from remporte.espace import Erreur

_PREFIXE_ATTENTE = "ecritures-"
_VERROU_ATTENTE = ".publication"


def message_droits(chemin: Path, erreur: PermissionError) -> str:
    if sys.platform == "win32" and getattr(erreur, "winerror", None) in (32, 33):
        return f"Fermez {chemin.name} puis relancez."
    return f"Impossible d'écrire {chemin.name} : vérifiez les droits du dossier."


def publier(dossier: Path, fichiers: dict[Path, bytes], *,
            exclusifs: Collection[Path] = (), conflit: str | None = None) -> None:
    """Prépare les fichiers et sauvegarde les originaux avant tout remplacement."""
    if not fichiers:
        return
    debut = time.time_ns()
    attente = None
    verrou = None
    sauvegardes: dict[Path, Path] = {}
    prepares: dict[Path, tuple[Path, tuple[int, int]]] = {}
    reserves: dict[Path, tuple[int, int]] = {}
    dossiers_crees: list[Path] = []
    problemes: list[str] = []
    cible = next(iter(fichiers))
    try:
        interne = dossier / ".remporte"
        if interne.resolve() != interne:
            raise OSError
        _retirer_restes(interne, debut)
        chemin_attente = interne / f"{_PREFIXE_ATTENTE}{uuid4().hex}"
        chemin_attente.mkdir()
        attente = chemin_attente
        verrou = (attente / _VERROU_ATTENTE).open("xb")
        _verrouiller(verrou)
        if os.fstat(verrou.fileno()).st_size:
            raise OSError
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
            prepares[cible] = prepare, _empreinte(prepare.lstat())

        try:
            for cible, (prepare, _) in prepares.items():
                _creer_parents(cible.parent, dossier, dossiers_crees)
                if cible not in sauvegardes:
                    # Réserve le nom sans écraser un fichier arrivé entre-temps.
                    with cible.open("xb") as fichier:
                        reserves[cible] = _empreinte(os.fstat(fichier.fileno()))
                prepare.replace(cible)
        except BaseException as erreur:
            for chemin, (prepare, empreinte) in reversed(prepares.items()):
                try:
                    # Le fichier préparé disparaît dès que son remplacement aboutit.
                    if not prepare.exists():
                        _retablir(chemin, empreinte, sauvegardes.get(chemin), problemes)
                    elif chemin in reserves:
                        _retablir(chemin, reserves[chemin], None, problemes)
                except OSError:
                    problemes.append(f"Impossible de rétablir {chemin.name}.")
            for parent in reversed(dossiers_crees):
                try:
                    parent.rmdir()
                except OSError as suppression:
                    if suppression.errno not in (errno.ENOENT, errno.ENOTEMPTY, errno.EEXIST):
                        problemes.append(f"Impossible de retirer le dossier {parent.name}.")
            if problemes and not isinstance(erreur, OSError):
                erreur.args += tuple(problemes)
            raise
    except OSError as erreur:
        if isinstance(erreur, PermissionError):
            message = message_droits(cible, erreur)
        elif isinstance(erreur, FileExistsError) and conflit and cible in exclusifs:
            message = conflit.format(nom=cible.name)
        else:
            message = diagnostic_chemin_trop_long(erreur) or (
                f"Impossible d'écrire le fichier {cible.name} dans le dossier de réponse."
            )
        raise Erreur(" ".join([message, *problemes])) from None
    finally:
        if verrou is not None:
            with suppress(OSError):
                verrou.close()
        if attente is not None:
            _nettoyer(attente)


def _empreinte(infos: os.stat_result) -> tuple[int, int]:
    return infos.st_size, infos.st_mtime_ns


def _retablir(chemin: Path, empreinte: tuple[int, int], sauvegarde: Path | None,
              problemes: list[str]) -> None:
    try:
        infos = chemin.lstat()
    except FileNotFoundError:
        infos = None
    if infos is None or not stat.S_ISREG(infos.st_mode) or _empreinte(infos) != empreinte:
        problemes.append(f"{chemin.name} a été modifié pendant l'opération : il est conservé.")
    elif sauvegarde is not None:
        sauvegarde.replace(chemin)
    else:
        chemin.unlink()


def _nettoyer(attente: Path) -> None:
    with suppress(OSError):
        shutil.rmtree(attente)


def _retirer_restes(interne: Path, debut: int) -> None:
    for reste in interne.glob(f"{_PREFIXE_ATTENTE}*"):
        try:
            infos = reste.lstat()
            if not stat.S_ISDIR(infos.st_mode) or infos.st_mtime_ns >= debut:
                continue
            # Une autre commande peut être en train de publier dans ce dossier.
            chemin_verrou = reste / _VERROU_ATTENTE
            if chemin_verrou.is_symlink():
                continue
            with chemin_verrou.open("ab") as verrou:
                _verrouiller(verrou)
                # Réserve la suppression avant de fermer le fichier.
                verrou.write(b"\0")
        except OSError:
            continue
        _nettoyer(reste)


def _verrouiller(verrou: BinaryIO) -> None:
    if os.name == "nt":
        import msvcrt

        verrou.seek(0)
        msvcrt.locking(verrou.fileno(), msvcrt.LK_NBLCK, 1)
    else:
        import fcntl

        fcntl.flock(verrou.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)


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
