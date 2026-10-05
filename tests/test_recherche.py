"""Tests de remporte.recherche : index FTS5, accents, base entreprise."""

from __future__ import annotations

from pathlib import Path

from conftest import fabriquer_docx

from remporte import recherche


def _dossier_indexe(tmp_path: Path) -> Path:
    dossier = tmp_path / "reponse"
    (dossier / ".remporte" / "texte" / "sous").mkdir(parents=True)
    (dossier / ".remporte" / "texte" / "RC.docx.md").write_text(
        "# Règlement de consultation\n\n"
        "Les critères de jugement sont : valeur technique 60 %, prix 40 %.\n",
        encoding="utf-8",
    )
    (dossier / ".remporte" / "texte" / "sous" / "cctp.md").write_text(
        "Le prestataire assure la supervision.\n" * 3, encoding="utf-8"
    )
    recherche.indexer_dce(dossier)
    return dossier


def test_indexer_puis_chercher(tmp_path: Path):
    dossier = _dossier_indexe(tmp_path)
    resultats = recherche.chercher_dce(dossier, "critères de jugement")
    assert resultats, "le passage du RC est retrouvé"
    premier = resultats[0]
    assert premier["piece"] == "RC.docx"
    assert "critères" in premier["passage"].lower()
    assert "**" in premier["extrait"]  # mise en évidence du snippet
    assert set(premier) == {"piece", "passage", "extrait", "score"}


def test_recherche_sans_accents(tmp_path: Path):
    dossier = _dossier_indexe(tmp_path)
    resultats = recherche.chercher_dce(dossier, "criteres")
    assert resultats, "remove_diacritics : « criteres » trouve « critères »"


def test_recherche_sans_resultat(tmp_path: Path):
    dossier = _dossier_indexe(tmp_path)
    assert recherche.chercher_dce(dossier, "zxqwj") == []


def test_requete_avec_apostrophe_ne_casse_pas(tmp_path: Path):
    dossier = _dossier_indexe(tmp_path)
    # ne doit lever aucune erreur SQL
    recherche.chercher_dce(dossier, "l'entreprise d'aujourd'hui")


def test_reindexation_remplace_l_index(tmp_path: Path):
    dossier = _dossier_indexe(tmp_path)
    (dossier / ".remporte" / "texte" / "RC.docx.md").write_text(
        "Seule une phrase sur la supervision.", encoding="utf-8"
    )
    recherche.indexer_dce(dossier)
    assert recherche.chercher_dce(dossier, "jugement") == []
    assert recherche.chercher_dce(dossier, "supervision")


def test_base_indexer_et_chercher(tmp_path: Path, monkeypatch):
    source = tmp_path / "entreprise"
    source.mkdir()
    fabriquer_docx(source / "references.docx")
    base = tmp_path / "base"
    monkeypatch.setenv("REMPORTE_BASE", str(base))
    assert recherche.chemin_base() == base
    nombre = recherche.indexer_base(source, base)
    assert nombre > 0
    assert (base / "index.sqlite").exists()
    assert (base / "texte" / "references.docx.md").exists()
    resultats = recherche.chercher_base(base, "références")
    assert resultats
    assert resultats[0]["piece"] == "references.docx"


def test_base_indexer_source_absente(tmp_path: Path):
    import pytest

    with pytest.raises(ValueError):
        recherche.indexer_base(tmp_path / "nulle part", tmp_path / "base")


def test_passages_environ_1200_caracteres():
    texte = "\n\n".join(f"Paragraphe numéro {i} avec du contenu." for i in range(200))
    passages = recherche.decouper_passages(texte)
    assert len(passages) > 1
    assert all(len(p) <= 2400 for p in passages)
    assert recherche.decouper_passages("") == []
