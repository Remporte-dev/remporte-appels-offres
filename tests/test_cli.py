"""Tests de remporte.cli : commandes, --json, codes retour 0/1/2."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from conftest import ecrire_pdf, fabriquer_docx, fabriquer_xlsx

from remporte.cli import main


@pytest.fixture()
def zip_dce(tmp_path: Path) -> Path:
    """DCE zippé minimal : RC + BPU + CCTP scanné."""
    pieces = tmp_path / "brut"
    pieces.mkdir()
    fabriquer_docx(pieces / "1-RC.docx")
    fabriquer_xlsx(pieces / "2-BPU.xlsx")
    ecrire_pdf(pieces / "3-CCTP.pdf", [
        "Cahier des clauses techniques particulieres du marche"
        "\nAssistance a la maitrise d'ouvrage pour le systeme d'information",
        "Le prestataire assure la supervision de la transition."
        "\nLes criteres de jugement valent 60 pour cent pour la technique.",
    ])
    import zipfile

    zip_source = tmp_path / "DCE_TEST.zip"
    with zipfile.ZipFile(zip_source, "w") as zf:
        for fichier in pieces.iterdir():
            zf.write(fichier, fichier.name)
    return zip_source


def _initialiser(tmp_path: Path, zip_dce: Path) -> Path:
    dossier = tmp_path / "reponse"
    code = main(["init", str(zip_dce), "--dossier", str(dossier)])
    assert code == 0
    return dossier


def test_init_et_etat(tmp_path: Path, zip_dce: Path, capsys):
    dossier = _initialiser(tmp_path, zip_dce)
    assert (dossier / "01-pieces.md").exists()
    sortie = capsys.readouterr().out
    assert "Pièces : 3" in sortie

    code = main(["etat", "--dossier", str(dossier)])
    assert code == 0
    etat_sorti = capsys.readouterr().out
    assert "analyse" in etat_sorti
    assert "remporte guide analyse" in etat_sorti


def test_etat_depuis_le_dossier_courant(tmp_path: Path, zip_dce: Path,
                                       monkeypatch, capsys):
    dossier = _initialiser(tmp_path, zip_dce)
    monkeypatch.chdir(dossier)
    assert main(["etat"]) == 0
    assert "Prochaine étape : analyse" in capsys.readouterr().out


def test_etat_dossier_introuvable(tmp_path: Path, capsys):
    monkey_dir = tmp_path / "rien"
    monkey_dir.mkdir()
    code = main(["etat", "--dossier", str(monkey_dir)])
    assert code == 2


def test_init_source_absente(capsys, tmp_path):
    assert main(["init", str(tmp_path / "nulle.zip")]) == 1


def test_pieces(tmp_path: Path, zip_dce: Path, capsys):
    dossier = _initialiser(tmp_path, zip_dce)
    assert main(["pieces", "--dossier", str(dossier)]) == 0
    sortie = capsys.readouterr().out
    assert "RC" in sortie and "BPU" in sortie and "CCTP" in sortie

    assert main(["pieces", "--dossier", str(dossier), "--json"]) == 0
    donnees = json.loads(capsys.readouterr().out)
    assert {p["type"] for p in donnees["pieces"]} == {"RC", "BPU", "CCTP"}


def test_lire_ambigu_puis_unique(tmp_path: Path, zip_dce: Path, capsys):
    dossier = _initialiser(tmp_path, zip_dce)
    # fragment sans pièce → liste des pièces et code 1
    assert main(["lire", "inexistant", "--dossier", str(dossier)]) == 1
    # fragment ambigu : « . » est dans tous les chemins → liste des candidats
    assert main(["lire", ".", "--dossier", str(dossier)]) == 1
    # lecture unique
    assert main(["lire", "rc.docx", "--dossier", str(dossier)]) == 0
    texte = capsys.readouterr().out
    assert "Règlement de consultation" in texte


def test_lire_page_pdf(tmp_path: Path, zip_dce: Path, capsys):
    dossier = _initialiser(tmp_path, zip_dce)
    assert main(["lire", "cctp", "--dossier", str(dossier), "--page", "2"]) == 0
    assert "criteres de jugement" in capsys.readouterr().out.lower()
    assert main(["lire", "cctp", "--dossier", str(dossier), "--page", "99"]) == 1


def test_chercher(tmp_path: Path, zip_dce: Path, capsys):
    dossier = _initialiser(tmp_path, zip_dce)
    capsys.readouterr()
    assert main(["chercher", "criteres de jugement",
                 "--dossier", str(dossier)]) == 0
    sortie = capsys.readouterr().out
    assert "3-CCTP.pdf" in sortie
    assert "**" in sortie  # mise en évidence du snippet
    assert main(["chercher", "zxqwj", "--dossier", str(dossier), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["resultats"] == []


def test_cadre_sans_crt(tmp_path: Path, zip_dce: Path, capsys):
    dossier = _initialiser(tmp_path, zip_dce)
    assert main(["cadre", "--dossier", str(dossier)]) == 1
    assert "Aucun CRT" in capsys.readouterr().out


def test_cadre_avec_fragment(tmp_path: Path, zip_dce: Path, capsys):
    dossier = _initialiser(tmp_path, zip_dce)
    assert main(["cadre", "cctp", "--dossier", str(dossier)]) == 0
    sortie = capsys.readouterr().out
    assert "Cadre de réponse" in sortie
    assert main(["cadre", "cctp", "--dossier", str(dossier), "--json"]) == 0
    donnees = json.loads(capsys.readouterr().out)
    assert donnees["origine"] in {"motifs", "aucune"}


def test_base_indexer_et_chercher(tmp_path: Path, monkeypatch, capsys):
    source = tmp_path / "entreprise"
    source.mkdir()
    (source / "socle.txt").write_text(
        "L'entreprise compte 45 salariés certifiés ISO 27001.",
        encoding="utf-8",
    )
    monkeypatch.setenv("REMPORTE_BASE", str(tmp_path / "base"))
    assert main(["base", "indexer", str(source)]) == 0
    assert main(["base", "chercher", "salaries certifies"]) == 0
    sortie = capsys.readouterr().out
    assert "socle.txt" in sortie
    assert main(["base", "chercher", "zxqwj", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["resultats"] == []


def test_guide(tmp_path: Path, capsys):
    assert main(["guide"]) == 0
    sortie = capsys.readouterr().out
    for etape in ("pieces", "analyse", "go-no-go", "plan", "redaction",
                  "relecture", "export"):
        assert etape in sortie
    assert main(["guide", "bogus"]) == 1
    # les guides sont écrits en parallèle : présents, ils s'affichent (code 0) ;
    # absents, message clair et code 1 — les deux branches sont testées.
    code = main(["guide", "analyse"])
    sortie = capsys.readouterr().out
    if code == 0:
        assert sortie.strip()
    else:
        assert "Pas encore de guide" in sortie


def test_guide_absent_message_clair(tmp_path: Path, monkeypatch, capsys):
    import remporte.cli as module_cli

    monkeypatch.setattr(module_cli, "_lire_ressource", lambda *parties: None)
    assert main(["guide", "analyse"]) == 1
    assert "Pas encore de guide" in capsys.readouterr().out
    assert main(["offre"]) == 1
    assert "Pas encore de guide" in capsys.readouterr().out


def test_exporter(tmp_path: Path, zip_dce: Path, capsys):
    dossier = _initialiser(tmp_path, zip_dce)
    (dossier / "04-plan.md").write_text(
        "# Plan\n\n- [x] 01 — Approche\n", encoding="utf-8"
    )
    (dossier / "sections/01-approche.md").write_text(
        "# Approche\n\nNotre méthode en trois phases.\n", encoding="utf-8"
    )
    assert main(["exporter", "--dossier", str(dossier)]) == 0
    sortie = capsys.readouterr().out
    assert "memoire.docx" in sortie and "dossier.html" in sortie
    assert (dossier / "export" / "memoire.docx").exists()
    assert (dossier / "export" / "dossier.html").exists()
    # état : export devient « faite »
    assert main(["etat", "--dossier", str(dossier), "--json"]) == 0
    etat = json.loads(capsys.readouterr().out)
    assert etat["etapes"]["export"]["etat"] == "faite"


def test_exporter_formats_invalides(tmp_path: Path, zip_dce: Path):
    dossier = _initialiser(tmp_path, zip_dce)
    assert main(["exporter", "--dossier", str(dossier),
                 "--formats", "pdf"]) == 1


def test_json_unique_sur_stdout(tmp_path: Path, zip_dce: Path, capsys):
    dossier = _initialiser(tmp_path, zip_dce)
    capsys.readouterr()
    assert main(["etat", "--dossier", str(dossier), "--json"]) == 0
    brut = capsys.readouterr()
    assert json.loads(brut.out)  # objet JSON unique, pas de texte mêlé
    assert brut.err == ""


def test_cadre_couverture(tmp_path, capsys):
    """Les exigences « PP » non citées dans les sections sont listées."""
    from docx import Document

    from remporte import cli, espace

    source = tmp_path / "DCE"
    source.mkdir()
    document = Document()
    for rang in range(1, 6):
        document.add_paragraph(f"{{PP {rang:03d}.}}\t1.{rang} : Chapitre : Le candidat précise {rang}.\t3")
    document.save(source / "CRT.docx")
    dossier = tmp_path / "reponse"
    espace.initialiser(source, dossier)
    (dossier / "sections" / "01-a.md").write_text("### PP 001 — oui\n### PP 3 — oui\n", encoding="utf-8")
    assert cli.main(["cadre", "--couverture", "--dossier", str(dossier)]) == 0
    sortie = capsys.readouterr().out
    assert "2 sur 5" in sortie
    assert "PP 002" in sortie and "PP 003" not in sortie
