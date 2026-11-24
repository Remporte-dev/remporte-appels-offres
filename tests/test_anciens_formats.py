"""Tests de lecture des anciens formats : .doc (Word 97-2003) et .xls (Excel 97-2003).

`.doc` et `.xls` entrent dans `lecture.FORMATS_LUS` et sont convertis en
markdown comme les autres pièces. Les pièces d'exemple de `tests/fixtures/`
sont fictives (voir LISEZMOI.md). Le contenu des pièces fabriquées vient de
`fabriquer_doc_minimal` (tests/conftest.py) : FIB, table des pièces et texte
cp1252, selon [MS-DOC].
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from conftest import (
    chemin_fixture,
    ecrire_ole,
    fabriquer_doc_minimal,
    fabriquer_fib_word,
)

from remporte.cli import main
from remporte.lecture import FORMATS_LUS, convertir


# ---------------------------------------------------------------------------
# Points 1 et 2 : FORMATS_LUS et la DPGF d'exemple en .xls
# ---------------------------------------------------------------------------

def test_formats_lus_inclut_doc_et_xls():
    assert {".doc", ".xls"} <= FORMATS_LUS


def test_convertir_xls_dpgf_exemple():
    conversion = convertir(chemin_fixture("dpgf-exemple.xls"))
    assert conversion.statut == "ok"
    texte = conversion.texte
    assert "## Feuille DPGF Lot 02" in texte
    assert "## Feuille PSE éclairage" in texte
    # la ligne d'en-tête du bordereau
    assert "| POSTE | DÉSIGNATION DES OUVRAGES | U | QTÉ | PRIX U. HT | PRIX TOT. HT |" in texte
    # les lignes de bordereau sont là, pas seulement les en-têtes ;
    # un entier ne sort jamais avec « .0 »
    assert "| 2.1 | Tableau électrique général | u | 1 | 1850 |" in texte
    assert "350.5" in texte
    assert "1850.0" not in texte
    assert "48.0" not in texte
    # la date rendue comme str(datetime), comme openpyxl pour un .xlsx ;
    # le booléen rendu True/False
    assert "2026-12-15 00:00:00" in texte
    assert "False" in texte


# ---------------------------------------------------------------------------
# Point 3 : les deux .doc d'exemple
# ---------------------------------------------------------------------------

def test_convertir_doc_dc1_exemple():
    conversion = convertir(chemin_fixture("dc1-exemple.doc"))
    assert conversion.statut == "ok"
    texte = conversion.texte
    assert "Lettre de candidature (DC1)" in texte
    # l'apostrophe typographique du fichier est conservée
    assert "Identification de l’acheteur : Communauté de communes du Val Fictif" in texte
    assert "Objet de la consultation : rénovation énergétique de l’école des Tilleuls" in texte
    assert "Voir les articles L. 2141-1 à L. 2141-5 du code de la commande publique." in texte
    assert "Date de la dernière mise à jour : 01/04/2019" in texte
    # les paragraphes sont conservés, pas une seule ligne
    assert "\n\n" in texte
    # les quatre cellules du tableau 2 × 2 sont présentes
    for cellule in ("Nom commercial", "Dénomination sociale",
                    "Entreprise Exemple", "Exemple SAS"):
        assert cellule in texte


def test_convertir_doc_attestation_visite_exemple():
    conversion = convertir(chemin_fixture("attestation-visite-exemple.doc"))
    assert conversion.statut == "ok"
    texte = conversion.texte
    assert "ATTESTATION DE VISITE" in texte
    assert ("Consultation : 2026-ECOLE-TILLEULS – travaux de rénovation "
            "énergétique") in texte
    assert "certifie m'être rendu sur le site" in texte


# ---------------------------------------------------------------------------
# Point 4 : .xls endommagé
# ---------------------------------------------------------------------------

def test_convertir_xls_tronque_statut_propre(tmp_path: Path):
    """Un .xls coupé net : statut illisible, texte vide, jamais une exception."""
    piece = tmp_path / "travaille.xls"
    piece.write_bytes(chemin_fixture("dpgf-exemple.xls").read_bytes()[:600])
    conversion = convertir(piece)
    assert conversion.statut == "illisible"
    assert conversion.texte == ""
    assert conversion.motif


def test_convertir_xls_bruit_statut_propre(tmp_path: Path):
    piece = tmp_path / "bruit.xls"
    piece.write_bytes(b"\x09\x08\x10\x00\x00\x06\x05\x00 du bruit, pas un classeur")
    conversion = convertir(piece)
    assert conversion.statut == "illisible"
    assert conversion.texte == ""


# ---------------------------------------------------------------------------
# Point 5 : .doc endommagé ou non reconnu
# ---------------------------------------------------------------------------

def test_convertir_doc_tronque_statut_propre(tmp_path: Path):
    piece = tmp_path / "travaille.doc"
    piece.write_bytes(chemin_fixture("dc1-exemple.doc").read_bytes()[:600])
    conversion = convertir(piece)
    assert conversion.statut == "illisible"
    assert conversion.texte == ""
    assert "illisible" in conversion.motif


def test_convertir_doc_pas_un_ole(tmp_path: Path):
    piece = tmp_path / "faux.doc"
    piece.write_bytes(b"\xd0\xcf du bruit qui ne va pas loin")
    conversion = convertir(piece)
    assert conversion.statut == "illisible"
    assert "illisible" in conversion.motif
    assert conversion.texte == ""


def test_convertir_doc_sans_flux_worddocument_le_dit(tmp_path: Path):
    piece = ecrire_ole(tmp_path / "vide.doc", {"AutreFlux": b"pas du Word"})
    conversion = convertir(piece)
    assert conversion.statut == "illisible"
    assert "WordDocument" in conversion.motif
    assert conversion.texte == ""


def test_convertir_doc_word6_trop_ancien(tmp_path: Path):
    piece = ecrire_ole(tmp_path / "ancien.doc",
                       {"WordDocument": fabriquer_fib_word(0xA5DC, 0x0065)})
    conversion = convertir(piece)
    assert conversion.statut == "non_pris_en_charge"
    assert "trop ancien" in conversion.motif
    assert conversion.texte == ""


def test_convertir_doc_word95_trop_ancien(tmp_path: Path):
    """0xA5EC mais nFib < 0x00C1 : Word 95, refusé comme Word 6."""
    piece = ecrire_ole(tmp_path / "ancien95.doc",
                       {"WordDocument": fabriquer_fib_word(0xA5EC, 0x0065)})
    conversion = convertir(piece)
    assert conversion.statut == "non_pris_en_charge"
    assert "trop ancien" in conversion.motif


def test_convertir_doc_signature_inconnue(tmp_path: Path):
    piece = ecrire_ole(tmp_path / "inconnu.doc",
                       {"WordDocument": fabriquer_fib_word(0xABCD, 0x00C1)})
    conversion = convertir(piece)
    assert conversion.statut == "illisible"
    assert "non reconnu" in conversion.motif


def test_convertir_doc_protege(tmp_path: Path):
    piece = ecrire_ole(tmp_path / "protege.doc",
                       {"WordDocument": fabriquer_fib_word(0xA5EC, 0x00C1,
                                                           drapeaux=0x0100)})
    conversion = convertir(piece)
    assert conversion.statut == "illisible"
    assert "protégé" in conversion.motif
    assert conversion.texte == ""


def test_convertir_doc_sans_texte_est_vide(tmp_path: Path):
    piece = fabriquer_doc_minimal(tmp_path / "vide.doc", "")
    conversion = convertir(piece)
    assert conversion.statut == "vide"
    assert conversion.texte == ""


# ---------------------------------------------------------------------------
# Point 6 : champs et marques Word sur un .doc fabriqué
# ---------------------------------------------------------------------------

def lignes_paragraphes(conversion) -> list[str]:
    assert conversion.statut == "ok"
    return conversion.texte.split("\n\n")


def test_fabrique_doc_minimal_deux_paragraphes(tmp_path: Path):
    """Vérification de la fabrique elle-même : « Bonjour\rMonde » rend deux
    paragraphes séparés par une ligne vide."""
    piece = fabriquer_doc_minimal(tmp_path / "simple.doc", "Bonjour\rMonde")
    conversion = convertir(piece)
    assert conversion.statut == "ok"
    assert conversion.texte == "Bonjour\n\nMonde"


def test_doc_code_de_champ_ecarte_resultat_garde(tmp_path: Path):
    piece = fabriquer_doc_minimal(
        tmp_path / "champ.doc", 'Champ : \x13 HYPERLINK "x" \x14articles\x15')
    lignes = lignes_paragraphes(convertir(piece))
    assert lignes == ["Champ : articles"]
    assert "HYPERLINK" not in "\n".join(lignes)


def test_doc_case_a_cocher_retiree(tmp_path: Path):
    piece = fabriquer_doc_minimal(
        tmp_path / "case.doc",
        'Déclaration :\x13 FORMCHECKBOX \x15\rEngagement confirmé')
    lignes = lignes_paragraphes(convertir(piece))
    assert "Déclaration :" in lignes
    assert "Engagement confirmé" in lignes
    assert "FORMCHECKBOX" not in "\n".join(lignes)


def test_doc_champ_imbrique_dans_le_code_ecarte(tmp_path: Path):
    """Un champ complet dans le code d'un autre champ : le code externe est
    écarté en entier, seul son résultat affiché est gardé."""
    piece = fabriquer_doc_minimal(
        tmp_path / "imbrique.doc",
        '\x13 \x13 interne \x14caché\x15 extérieur \x14visible\x15')
    lignes = lignes_paragraphes(convertir(piece))
    assert lignes == ["visible"]
    # le champ imbriqué part avec le code du champ externe
    assert "interne" not in "\n".join(lignes)
    assert "caché" not in "\n".join(lignes)
    assert "extérieur" not in "\n".join(lignes)


def test_doc_marques_cellule_et_page_separent_les_paragraphes(tmp_path: Path):
    piece = fabriquer_doc_minimal(
        tmp_path / "separateurs.doc",
        "cellule A\x07cellule B\x0cpage suivante")
    lignes = lignes_paragraphes(convertir(piece))
    assert lignes == ["cellule A", "cellule B", "page suivante"]


def test_doc_non_defini_devient_tiret_et_controles_retires(tmp_path: Path):
    piece = fabriquer_doc_minimal(tmp_path / "tiret.doc", "tiret\x1ecadençé")
    lignes = lignes_paragraphes(convertir(piece))
    assert lignes == ["tiret-cadençé"]
    piece = fabriquer_doc_minimal(
        tmp_path / "controles.doc", "avant\x01\x02\x05\x08\x0B\x1Faprès")
    lignes = lignes_paragraphes(convertir(piece))
    assert lignes == ["avantaprès"]


# ---------------------------------------------------------------------------
# Point 7 : init sur un DCE qui contient les trois pièces d'exemple
# ---------------------------------------------------------------------------

def _dce_exemples(tmp_path: Path) -> tuple[Path, Path]:
    source = tmp_path / "DCE"
    source.mkdir()
    for nom in ("attestation-visite-exemple.doc", "dc1-exemple.doc",
                "dpgf-exemple.xls"):
        shutil.copy(chemin_fixture(nom), source / nom)
    dossier = tmp_path / "reponse"
    return source, dossier


def test_init_lit_les_trois_pieces_anciennes(tmp_path: Path, capsys):
    source, dossier = _dce_exemples(tmp_path)
    assert main(["init", str(source), "--dossier", str(dossier)]) == 0
    capsys.readouterr()

    inventaire = (dossier / "01-pieces.md").read_text(encoding="utf-8")
    assert "Toutes les pièces ont été converties." in inventaire
    for nom in ("attestation-visite-exemple.doc", "dc1-exemple.doc",
                "dpgf-exemple.xls"):
        assert f"`dce/{nom}` | ok |" in inventaire

    etat = json.loads(
        (dossier / ".remporte" / "etat.json").read_text(encoding="utf-8"))
    statuts = {p["chemin"]: p["statut"] for p in etat["pieces"]}
    assert set(statuts.values()) == {"ok"}

    assert main(["chercher", "attestation de visite",
                 "--dossier", str(dossier)]) == 0
    assert "attestation-visite-exemple.doc" in capsys.readouterr().out
    assert main(["chercher", "prix u ht", "--dossier", str(dossier)]) == 0
    assert "dpgf-exemple.xls" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# Point 8 : formats — un CRT en .doc est un cadre de réponse Word
# ---------------------------------------------------------------------------

def test_formats_crt_en_doc_donne_cadre_word(tmp_path: Path, capsys):
    source = tmp_path / "DCE"
    source.mkdir()
    shutil.copy(chemin_fixture("attestation-visite-exemple.doc"),
                source / "2-CRT.doc")
    dossier = tmp_path / "reponse"
    assert main(["init", str(source), "--dossier", str(dossier)]) == 0
    capsys.readouterr()
    assert main(["formats", "--dossier", str(dossier), "--json"]) == 0
    constats = json.loads(capsys.readouterr().out)["constats"]
    cadres = [c for c in constats if c["type"] == "cadre_word"]
    assert [c["piece"] for c in cadres] == ["2-CRT.doc"]
