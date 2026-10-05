"""Tests de remporte.lecture : conversion et décompression."""

from __future__ import annotations

import zipfile
from pathlib import Path

from conftest import (
    ecrire_pdf,
    fabriquer_docx,
    fabriquer_ods,
    fabriquer_pptx,
    fabriquer_xlsx,
    fabriquer_zip,
)

from remporte.lecture import convertir, decompresser


def test_decompresser_zip_simple(tmp_path: Path):
    source = fabriquer_zip(
        tmp_path / "DCE.zip",
        {"RC.pdf": b"%PDF-faux", "sous/cctp.docx": b"PK-faux"},
    )
    fichiers = decompresser(source, tmp_path / "dce")
    noms = [f.relative_to(tmp_path / "dce").as_posix() for f in fichiers]
    assert "RC.pdf" in noms
    assert "sous/cctp.docx" in noms


def test_decompresser_zip_dans_zip(tmp_path: Path):
    source = fabriquer_zip(
        tmp_path / "DCE.zip",
        {"RC.pdf": b"%PDF-faux"},
        zips_internes={"lot2.zip": {"DQE.xls": "bordereau"}},
    )
    fichiers = decompresser(source, tmp_path / "dce")
    noms = [f.name for f in fichiers]
    assert "DQE.xls" in noms
    assert not list((tmp_path / "dce").rglob("*.zip")), "le zip interne disparaît"


def test_decompresser_bloque_zip_slip(tmp_path: Path):
    source = tmp_path / "malin.zip"
    with zipfile.ZipFile(source, "w") as zf:
        zf.writestr("ok.txt", "bon")
        zf.writestr("../malin.txt", "méchant")
        zf.writestr("/absolu.txt", "méchant")
    fichiers = decompresser(source, tmp_path / "dce")
    noms = [f.name for f in fichiers]
    assert noms == ["ok.txt"]
    assert not (tmp_path / "malin.txt").exists()


def test_decompresser_dossier(tmp_path: Path):
    source = tmp_path / "DCE"
    source.mkdir()
    (source / "RC.txt").write_text("reglement", encoding="utf-8")
    fichiers = decompresser(source, tmp_path / "dce")
    assert [f.name for f in fichiers] == ["RC.txt"]


def test_decompresser_signale_7z(tmp_path: Path, capsys):
    source = tmp_path / "DCE.zip"
    with zipfile.ZipFile(source, "w") as zf:
        zf.writestr("pieces/ancien.7z", b"7z\x27\xa1\xbc")
    fichiers = decompresser(source, tmp_path / "dce")
    assert any(f.suffix == ".7z" for f in fichiers)
    assert "7z" in capsys.readouterr().err


def test_convertir_pdf(tmp_path: Path):
    piece = ecrire_pdf(tmp_path / "RC.pdf", [
        "Reglement de consultation du marche d'assistance"
        "\nArticle 1 - objet : assister la maitrise d'ouvrage",
        "Article 2 - contenu du dossier de consultation"
        "\nLe dossier comprend le reglement, le CCTP et le CCAP.",
    ])
    conversion = convertir(piece)
    assert conversion.statut == "ok"
    assert conversion.pages == 2
    assert "<!-- page 2 -->" in conversion.texte
    assert "objet" in conversion.texte and "Article 2" in conversion.texte


def test_convertir_pdf_scanne_est_vide(tmp_path: Path):
    piece = ecrire_pdf(tmp_path / "scan.pdf", ["", ""])
    conversion = convertir(piece)
    assert conversion.statut == "vide"
    assert conversion.pages == 2
    assert "scanné" in conversion.motif
    assert conversion.texte == ""


def test_convertir_docx(tmp_path: Path):
    piece = fabriquer_docx(tmp_path / "rc.docx")
    conversion = convertir(piece)
    assert conversion.statut == "ok"
    assert "# Règlement de consultation" in conversion.texte
    assert "- Le critère" in conversion.texte
    assert "**doit**" in conversion.texte
    assert "| Critère | Pondération |" in conversion.texte
    assert "| --- | --- |" in conversion.texte


def test_convertir_xlsx(tmp_path: Path):
    piece = fabriquer_xlsx(tmp_path / "bpu.xlsx")
    conversion = convertir(piece)
    assert conversion.statut == "ok"
    assert "## Feuille BPU" in conversion.texte
    assert "## Feuille DQE" in conversion.texte
    assert "| Désignation | Quantité | Prix |" in conversion.texte


def test_convertir_ods(tmp_path: Path):
    piece = fabriquer_ods(tmp_path / "bpu.ods")
    conversion = convertir(piece)
    assert conversion.statut == "ok"
    assert "## Feuille Feuille1" in conversion.texte
    assert "Prestation X" in conversion.texte


def test_convertir_pptx(tmp_path: Path):
    piece = fabriquer_pptx(tmp_path / "presentation.pptx")
    conversion = convertir(piece)
    assert conversion.statut == "ok"
    assert "## Diapositive 1" in conversion.texte
    assert "Créée en 2010" in conversion.texte


def test_convertir_txt_et_csv(tmp_path: Path):
    (tmp_path / "a.txt").write_text("Bonjour\nDCE\n", encoding="utf-8")
    texte = convertir(tmp_path / "a.txt")
    assert texte.statut == "ok" and "Bonjour" in texte.texte
    (tmp_path / "b.csv").write_text("a;b\n1;2\n", encoding="utf-8")
    csv_conv = convertir(tmp_path / "b.csv")
    assert "| a | b |" in csv_conv.texte


def test_convertir_fichier_vide(tmp_path: Path):
    piece = tmp_path / "vide.txt"
    piece.write_text("", encoding="utf-8")
    conversion = convertir(piece)
    assert conversion.statut == "vide"


def test_convertir_format_inconnu(tmp_path: Path):
    piece = tmp_path / "logo.png"
    piece.write_bytes(b"\x89PNG")
    conversion = convertir(piece)
    assert conversion.statut == "non_pris_en_charge"


def test_convertir_docx_corrompu_ne_leve_pas(tmp_path: Path):
    piece = tmp_path / "casse.docx"
    piece.write_bytes(b"pas un zip")
    conversion = convertir(piece)
    assert conversion.statut == "illisible"
    assert conversion.motif
