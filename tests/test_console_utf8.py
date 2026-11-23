"""Sortie du CLI en UTF-8, même sur une console Windows en cp1252.

Sous Windows, une console ou une redirection en cp1252 est l'encodage par
défaut de sys.stdout et sys.stderr : un caractère hors de ce jeu (une flèche
→, un ≥) fait planter la commande ou dénature la sortie qu'un agent lit.
Contrat : à l'entrée de `remporte.cli.main`, les deux flux sont reconfigurés
en UTF-8 ; la sortie part en UTF-8, sans erreur, où qu'elle soit lue.

Note de test : le remplacement des flux se fait dans le corps du test, pas
dans une fixture — pytest repose sa capture entre les phases setup et call
et un remplacement posé au setup est perdu au moment de l'appel.
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

import pytest

from remporte.cli import main


def _flux_cp1252() -> io.TextIOWrapper:
    """Un flux console de poche, encodé comme un poste Windows francophone."""
    return io.TextIOWrapper(io.BytesIO(), encoding="cp1252", write_through=True)


def _console_cp1252(monkeypatch) -> tuple[io.TextIOWrapper, io.TextIOWrapper]:
    sortie, erreurs = _flux_cp1252(), _flux_cp1252()
    monkeypatch.setattr(sys, "stdout", sortie)
    monkeypatch.setattr(sys, "stderr", erreurs)
    return sortie, erreurs


def _lire(flux: io.TextIOWrapper) -> str:
    flux.flush()
    return flux.buffer.getvalue().decode("utf-8")


def test_guide_affiche_ses_fleches_sur_une_console_cp1252(monkeypatch):
    """`remporte guide relecture` contient des flèches → : la sortie doit
    partir en UTF-8 sans erreur et les flux rester en UTF-8 après l'appel."""
    sortie, erreurs = _console_cp1252(monkeypatch)
    code = main(["guide", "relecture"])
    assert code == 0, _lire(erreurs)
    contenu = _lire(sortie)
    assert "→" in contenu, contenu
    assert sortie.encoding == "utf-8"
    assert erreurs.encoding == "utf-8"


def test_erreur_avec_fleche_dans_le_chemin_sur_une_console_cp1252(
        monkeypatch, tmp_path: Path):
    """Le nom d'une source peut porter un caractère hors cp1252 : le message
    d'erreur doit arriver complet en UTF-8, pas dénaturé ni refusé."""
    sortie, erreurs = _console_cp1252(monkeypatch)
    source = tmp_path / "DCE → essai.zip"
    code = main(["init", str(source)])
    assert code == 1
    message = _lire(erreurs)
    assert "source introuvable" in message
    assert "→" in message, message
    assert sortie.encoding == "utf-8"
    assert erreurs.encoding == "utf-8"
