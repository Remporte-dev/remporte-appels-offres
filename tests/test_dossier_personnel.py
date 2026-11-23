"""Le dossier personnel n'est pas un dossier de réponse.

`trouver_dossier` remontait les parents et s'arrêtait à la seule présence de
`.remporte/`. Or la base d'entreprise vit dans `~/.remporte/base/` : toute
session ouverte sous le dossier personnel prenait donc `~` pour un dossier de
réponse. Contrat : un dossier de réponse se reconnaît à son fichier d'état
`.remporte/etat.json`, celui qu'écrit `remporte init`.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from conftest import fabriquer_zip

from remporte import espace
from remporte.cli import main


@pytest.fixture()
def travail_sous_dossier_personnel(tmp_path: Path) -> Path:
    """Un « dossier personnel » qui ne contient que la base d'entreprise, et
    un travail ouvert en dessous (Documents/projet)."""
    (tmp_path / ".remporte" / "base").mkdir(parents=True)
    documents = tmp_path / "Documents" / "projet"
    documents.mkdir(parents=True)
    return documents


def test_le_dossier_personnel_n_est_pas_un_dossier_de_reponse(
        travail_sous_dossier_personnel: Path):
    """`.remporte/base/` seul ne fait pas du dossier personnel un dossier de
    réponse pour tout ce qui est en dessous."""
    assert espace.trouver_dossier(travail_sous_dossier_personnel) is None


def test_etat_sous_le_dossier_personnel_ne_trouve_pas_de_dossier(
        travail_sous_dossier_personnel: Path, monkeypatch, capsys):
    """La commande en dépend : sous le dossier personnel, `remporte etat` dit
    qu'aucun dossier de réponse n'est trouvé (code 2), il n'essaye pas de lire
    le dossier personnel comme un dossier de réponse."""
    monkeypatch.chdir(travail_sous_dossier_personnel)
    assert main(["etat"]) == 2
    assert "dossier de réponse" in capsys.readouterr().err


def test_un_vrai_dossier_init_reste_trouvable_depuis_un_sous_dossier(
        tmp_path: Path):
    """Un dossier créé par `init` (donc avec .remporte/etat.json) reste trouvé
    depuis un sous-dossier, même si un parent contient .remporte/base/."""
    (tmp_path / ".remporte" / "base").mkdir(parents=True)
    zip_dce = fabriquer_zip(
        tmp_path / "DCE.zip",
        {"RC.txt": "Règlement de consultation de l'acheteur."},
    )
    dossier = tmp_path / "reponse"
    espace.initialiser(zip_dce, dossier)
    profond = dossier / "sections" / "annexes"
    profond.mkdir(parents=True)
    assert espace.trouver_dossier(profond) == dossier.resolve()
