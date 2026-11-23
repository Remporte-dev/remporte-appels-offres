"""Limites des systèmes de fichiers : chemins trop longs, dossier masqué.

Sous Windows, un nom de fichier trop long sort une erreur technique
brute (OSError : errno ENAMETOOLONG côté POSIX, winerror 206 ou un nom
invalide winerror 123 côté Windows). Contrat : le système reconnaît ces
erreurs et le CLI rend le message métier « Chemin trop long pour le
système… » au lieu de l'erreur brute.

Le dossier `.remporte` d'un dossier de réponse doit être masqué
(attribut caché) à sa création sous Windows ; ailleurs, rien ne change ; et
un échec du masquage n'empêche pas la création du dossier de réponse.
"""

from __future__ import annotations

import ctypes
import errno
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest
from conftest import fabriquer_zip

from remporte import espace
from remporte.cli import main


def _chemins():
    """Module des diagnostics de chemins."""
    from remporte import chemins
    return chemins


CHEMIN_LONG = str(Path("dce") / ("a" * 300 + ".docx"))


# ---------------------------------------------------------------------------
# 1.6 — diagnostic_chemin_trop_long
# ---------------------------------------------------------------------------

def _erreur_longueur(genre: str, chemin: str) -> OSError:
    """L'erreur construite à la main comme le système la pose : winerror est
    un attribut propre à Windows, errno à tout système."""
    if genre == "posix":
        return OSError(errno.ENAMETOOLONG, "File name too long", chemin)
    erreur = OSError(errno.ENOENT, "The filename or extension is too long", chemin)
    erreur.winerror = 206
    return erreur


@pytest.mark.parametrize("genre", ["posix", "windows"])
def test_erreur_de_longueur_diagnostiquee(genre: str):
    message = _chemins().diagnostic_chemin_trop_long(_erreur_longueur(genre, CHEMIN_LONG))
    assert message is not None
    assert "Chemin trop long pour le système" in message
    assert CHEMIN_LONG in message
    assert "Raccourcissez le nom" in message


def test_nom_invalide_windows_diagnostique_seulement_si_composant_trop_long(
        tmp_path: Path):
    """winerror 123 (nom invalide) ne vaut « chemin trop long » que si un
    composant du chemin dépasse la limite Windows."""
    for nom, trop_long in (("piece?.docx", False), ("a" * 300 + ".docx", True)):
        erreur = OSError(errno.EINVAL, "Nom de fichier incorrect", str(tmp_path / nom))
        erreur.winerror = 123
        assert (_chemins().diagnostic_chemin_trop_long(erreur) is not None) is trop_long


def test_erreur_de_longueur_sans_chemin_diagnostiquee_sans_precision():
    message = _chemins().diagnostic_chemin_trop_long(
        OSError(errno.ENAMETOOLONG, "File name too long"))
    assert message is not None
    assert "Chemin trop long pour le système" in message
    assert "Raccourcissez le nom" in message


@pytest.mark.parametrize("erreur", [
    PermissionError(errno.EACCES, "accès refusé", "dce/piece.docx"),
    ValueError("pas une erreur système"),
])
def test_les_autres_erreurs_ne_sont_pas_annoncees_comme_trop_longues(erreur):
    assert _chemins().diagnostic_chemin_trop_long(erreur) is None


def test_init_rend_le_message_metier_quand_le_chemin_est_trop_long(
        tmp_path: Path, monkeypatch, capsys):
    """Passage par le CLI : Windows signale un composant trop long comme un
    fichier introuvable (errno 2, winerror 206). Le CLI doit rendre le
    message métier, pas l'erreur technique brute."""
    erreur = _erreur_longueur("windows", str(tmp_path / "reponse" / "dce"))
    mkdir_original = Path.mkdir

    def mkdir_trop_long(chemin, *args, **kwargs):
        if chemin.name == "dce" and chemin.parent.name == "reponse":
            raise erreur
        return mkdir_original(chemin, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", mkdir_trop_long)
    zip_dce = fabriquer_zip(
        tmp_path / "DCE.zip",
        {"RC.txt": "Règlement de consultation de l'acheteur."},
    )
    code = main(["init", str(zip_dce), "--dossier", str(tmp_path / "reponse")])
    message = capsys.readouterr().err
    assert code == 1
    assert "Chemin trop long pour le système" in message
    assert str(tmp_path / "reponse" / "dce") in message
    assert "Raccourcissez le nom" in message
    assert "FileNotFoundError" not in message
    assert "Traceback" not in message


# ---------------------------------------------------------------------------
# 1.7 — masquer_espace
# ---------------------------------------------------------------------------

class NoyauFaux:
    """kernel32 de poche : compte les appels, ne touche au disque de personne."""

    def __init__(self, attributs: int = 0x10, succes: bool = True):
        self.appels: list[tuple] = []
        self.attributs = attributs  # 0x10 : répertoire, pas caché
        self.succes = succes

    def GetFileAttributesW(self, chemin: str) -> int:
        self.appels.append(("get", chemin))
        return self.attributs

    def SetFileAttributesW(self, chemin: str, attributs: int) -> int:
        self.appels.append(("set", chemin, attributs))
        return 1 if self.succes else 0


def _installer_windows(monkeypatch, noyau: NoyauFaux) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(ctypes, "windll", Mock(kernel32=noyau), raising=False)


@pytest.fixture()
def noyau_windows(monkeypatch) -> NoyauFaux:
    faux = NoyauFaux()
    _installer_windows(monkeypatch, faux)
    return faux


@pytest.fixture()
def zip_dce(tmp_path: Path) -> Path:
    return fabriquer_zip(
        tmp_path / "DCE.zip",
        {"RC.txt": "Règlement de consultation de l'acheteur."},
    )


def test_masquer_demande_l_attribut_cache(noyau_windows, tmp_path: Path):
    dossier = tmp_path / ".remporte"
    dossier.mkdir()
    _chemins().masquer_espace(dossier)
    assert noyau_windows.appels == [
        ("get", str(dossier.resolve())),
        ("set", str(dossier.resolve()), 0x12),  # répertoire (0x10) | caché (0x2)
    ]


def test_init_masque_le_dossier_agent_sous_windows(
        noyau_windows, zip_dce: Path, tmp_path: Path):
    dossier = tmp_path / "reponse"
    espace.initialiser(zip_dce, dossier)
    cible = str((dossier / ".remporte").resolve())
    assert ("set", cible, 0x12) in noyau_windows.appels


@pytest.mark.parametrize("plateforme", ["linux", "darwin"])
def test_init_ne_masque_rien_hors_windows(monkeypatch, zip_dce: Path,
                                          tmp_path: Path, plateforme: str):
    """Hors Windows, rien ne change : aucun appel système de masquage, même
    si kernel32 était atteignable."""
    faux = NoyauFaux()
    monkeypatch.setattr(sys, "platform", plateforme)
    monkeypatch.setattr(ctypes, "windll", Mock(kernel32=faux), raising=False)
    espace.initialiser(zip_dce, tmp_path / "reponse")
    assert faux.appels == []


@pytest.mark.parametrize("genre_echec", ["ecriture_refusee", "chemin_introuvable"])
def test_init_reussit_meme_si_le_masquage_echoue(
        monkeypatch, zip_dce: Path, tmp_path: Path, genre_echec: str, capsys):
    """Un poste qui refuse l'attribut caché ne doit pas priver l'utilisateur
    du dossier de réponse : init réussit et écrit l'état."""
    faux = NoyauFaux(attributs=-1 if genre_echec == "chemin_introuvable" else 0x10,
                     succes=False)
    _installer_windows(monkeypatch, faux)
    dossier = tmp_path / "reponse"
    code = main(["init", str(zip_dce), "--dossier", str(dossier)])
    assert code == 0, capsys.readouterr().err
    assert (dossier / ".remporte" / "etat.json").is_file()
    assert (dossier / "01-pieces.md").is_file()
