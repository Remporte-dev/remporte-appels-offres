"""Tests de remporte.espace : init, arborescence, 01-pieces.md, état."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from conftest import ecrire_pdf, fabriquer_docx, fabriquer_xlsx

from remporte import espace
from remporte.lecture import decompresser


@pytest.fixture()
def source_dce(tmp_path: Path) -> Path:
    """Un DCE-source miniature sous forme de dossier."""
    source = tmp_path / "DCE"
    source.mkdir()
    fabriquer_docx(source / "1-RC.docx")
    fabriquer_xlsx(source / "2-BPU.xlsx")
    ecrire_pdf(source / "3-CCTP-scan.pdf", ["", ""])
    (source / "notes.txt").write_text(
        "Complément d'information : remise le 12 juin.", encoding="utf-8"
    )
    return source


def test_initialiser_arborescence(tmp_path: Path, source_dce: Path):
    dossier = tmp_path / "reponse"
    donnees = espace.initialiser(source_dce, dossier)
    for chemin in ("dce", "sections", "export", ".remporte/texte",
                   "AGENTS.md", "CLAUDE.md", "02-analyse.md", "03-go-no-go.md",
                   "04-plan.md", "05-relecture.md", "01-pieces.md",
                   ".remporte/etat.json", ".remporte/index.sqlite"):
        assert (dossier / chemin).exists(), chemin
    assert (dossier / "CLAUDE.md").read_text(encoding="utf-8").strip() == "@AGENTS.md"
    par_nom = {p["chemin"]: p for p in donnees["pieces"]}
    assert par_nom["1-RC.docx"]["type"] == "RC"
    assert par_nom["2-BPU.xlsx"]["type"] == "BPU"
    assert par_nom["3-CCTP-scan.pdf"]["statut"] == "vide"
    assert par_nom["notes.txt"]["statut"] == "ok"
    # le texte converti du RC est en cache, celui du scan absent
    assert (dossier / ".remporte/texte/1-RC.docx.md").exists()
    assert not (dossier / ".remporte/texte/3-CCTP-scan.pdf.md").exists()
    etat_json = json.loads((dossier / ".remporte/etat.json").read_text("utf-8"))
    assert etat_json["pieces"] == donnees["pieces"]


def test_initialiser_refuse_dossier_deja_la(tmp_path: Path, source_dce: Path):
    dossier = tmp_path / "reponse"
    espace.initialiser(source_dce, dossier)
    with pytest.raises(espace.Erreur):
        espace.initialiser(source_dce, dossier)


def test_initialiser_forcer_garde_fichiers_remplis(tmp_path: Path, source_dce: Path):
    dossier = tmp_path / "reponse"
    espace.initialiser(source_dce, dossier)
    rempli = dossier / "02-analyse.md"
    rempli.write_text(
        rempli.read_text(encoding="utf-8").replace("<!-- à remplir -->", "Fait."),
        encoding="utf-8",
    )
    espace.initialiser(source_dce, dossier, forcer=True)
    assert "Fait." in rempli.read_text(encoding="utf-8")
    # un gabarit non rempli est réinitialisé : il contient encore son marqueur
    assert "à remplir" in (dossier / "03-go-no-go.md").read_text(encoding="utf-8")


def test_01_pieces_contenu(tmp_path: Path, source_dce: Path):
    dossier = tmp_path / "reponse"
    espace.initialiser(source_dce, dossier)
    inventaire_md = (dossier / "01-pieces.md").read_text(encoding="utf-8")
    assert "| RC |" in inventaire_md
    assert "PDF probablement scanné" in inventaire_md
    assert "CRT (cahier des réponses) absent" in inventaire_md
    assert "remplissage de cette pièce dans le format de l'acheteur" in inventaire_md
    assert "remporte.fr/produit?utm_source=cli" in inventaire_md
    assert "utm_content=piece-" in inventaire_md  # provenance mesurable par pièce
    assert espace.MARQUEUR not in inventaire_md  # étape « pieces » sans marqueur


def test_etat_initial(tmp_path: Path, source_dce: Path):
    dossier = tmp_path / "reponse"
    espace.initialiser(source_dce, dossier)
    etat = espace.etat(dossier)
    assert etat["etapes"]["pieces"]["etat"] == "faite"
    assert etat["etapes"]["analyse"]["etat"] == "a_faire"
    assert etat["etapes"]["analyse"]["marqueurs"] > 0
    assert etat["etapes"]["export"]["etat"] == "a_faire"
    assert etat["prochaine"] == "analyse"
    assert etat["commande"] == "remporte guide analyse"


def test_etat_redaction_suivant_le_plan(tmp_path: Path, source_dce: Path):
    dossier = tmp_path / "reponse"
    espace.initialiser(source_dce, dossier)
    (dossier / "04-plan.md").write_text(
        "# Plan\n\n- [ ] 01 — Moyens\n- [ ] 02 — Références\n",
        encoding="utf-8",
    )
    etat = espace.etat(dossier)
    assert etat["etapes"]["redaction"]["etat"] == "en_cours"
    assert etat["etapes"]["redaction"]["marqueurs"] == 2
    (dossier / "sections/01-moyens.md").write_text(
        "## Moyens\n\n" + "Ingénieurs certifiés mobilisés sur le site. " * 10 + "\n", encoding="utf-8"
    )
    etat = espace.etat(dossier)
    assert etat["etapes"]["redaction"]["marqueurs"] == 1
    (dossier / "sections/02-references.md").write_text(
        "## Références\n\n" + "Trois références comparables chez des acheteurs publics. " * 10 + "\n", encoding="utf-8"
    )
    etat = espace.etat(dossier)
    assert etat["etapes"]["redaction"]["etat"] == "faite"


def test_section_reduite_a_son_titre_non_redigee(tmp_path: Path, source_dce: Path):
    dossier = tmp_path / "reponse"
    espace.initialiser(source_dce, dossier)
    (dossier / "04-plan.md").write_text("- [ ] 01 — Moyens\n", encoding="utf-8")
    (dossier / "sections/01-moyens.md").write_text("# 01 — Moyens\n", encoding="utf-8")
    assert espace.etat(dossier)["etapes"]["redaction"]["etat"] == "en_cours"


def test_etat_refuse_hors_dossier(tmp_path: Path):
    with pytest.raises(espace.Erreur):
        espace.etat(tmp_path)


def test_trouver_dossier(tmp_path: Path, source_dce: Path):
    dossier = tmp_path / "reponse"
    espace.initialiser(source_dce, dossier)
    profond = dossier / "sections" / "annexes"
    profond.mkdir(parents=True)
    assert espace.trouver_dossier(profond) == dossier.resolve()
    assert espace.trouver_dossier(tmp_path) is None


def test_decompresser_zip_source(tmp_path: Path):
    """init accepte un zip : mêmes résultats qu'avec un dossier."""
    from conftest import fabriquer_zip

    zip_dce = fabriquer_zip(
        tmp_path / "DCE.zip",
        {"RC.txt": "Règlement de consultation", "notes.txt": "Divers."},
    )
    dossier = tmp_path / "reponse"
    donnees = espace.initialiser(zip_dce, dossier)
    assert [p["chemin"] for p in donnees["pieces"]] == ["RC.txt", "notes.txt"]
