"""Tests de remporte.candidature : DC1/DC2/DC4 préparés puis remplis.

Chaque valeur est relue à l'endroit exact du XML (paragraphe visé, case
cochée) : une valeur écrite au mauvais endroit est pire qu'un champ vide.
Toutes les données sont manifestement fictives.
"""

from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree

import pytest
from conftest import fabriquer_docx

from remporte import espace, candidature


@pytest.fixture()
def dossier(tmp_path: Path) -> Path:
    """Dossier de réponse minimal (un RC), candidature préparée."""
    source = tmp_path / "DCE"
    source.mkdir()
    fabriquer_docx(source / "1-RC.docx")
    dossier = tmp_path / "reponse"
    espace.initialiser(source, dossier)
    candidature.preparer(dossier)
    return dossier


def ecrire_valeurs(dossier: Path, valeurs: dict) -> None:
    chemin = dossier / "candidature" / "valeurs.json"
    chemin.write_text(
        json.dumps(valeurs, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def charger_valeurs(dossier: Path) -> dict:
    return json.loads(
        (dossier / "candidature" / "valeurs.json").read_text(encoding="utf-8")
    )


def paragraphs_xml(docx: Path) -> list[str]:
    """Textes concaténés des paragraphes du document.xml (pas les textbox)."""
    with zipfile.ZipFile(docx) as archive:
        xml = archive.read("word/document.xml").decode("utf-8")
    return [
        "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", m.group(0)))
        for m in re.finditer(r"<w:p[ >].*?</w:p>", xml, re.S)
    ], xml


def cases_cochees(xml: str) -> list[int]:
    """Index 1-based des `<w:checkBox>` cochés, ordre du document."""
    cases = list(re.finditer(r"<w:checkBox>.*?</w:checkBox>", xml, re.S))
    return [i + 1 for i, m in enumerate(cases) if 'w:val="1"' in m.group(0)]


def cases_noircies(xml: str) -> list[int]:
    """Index 1-based des cases dessinées du DC4 noircies (fallback VML)."""
    blocs = [
        m.group(0)
        for m in re.finditer(
            r"<mc:AlternateContent>.*?</mc:AlternateContent>", xml, re.S
        )
        if 'coordsize="147955,147955"' in m.group(0)
    ]
    return [i + 1 for i, b in enumerate(blocs) if 'filled="t"' in b]


def remplir_dc1(dossier: Path) -> None:
    valeurs = charger_valeurs(dossier)
    champs = valeurs["DC1"]["champs"]
    champs["acheteur"]["valeur"] = "Mairie d'Exemple"
    champs["reference_consultation"]["valeur"] = "[réf. : 2026-001]"
    champs["objet_consultation"]["valeur"] = "Prestations d'essai (fictif)"
    champs["objet_candidature"]["valeur"] = "lot_n"
    champs["lot_numero"]["valeur"] = "1 — Lot fictif"
    champs["presentation"]["valeur"] = "seul"
    champs["denomination"]["valeur"] = "Entreprise Exemple SAS"
    champs["adresse"]["valeur"] = "1 rue du Test, 00000 Nulle Part"
    champs["email"]["valeur"] = "contact@exemple.test"
    champs["telephone"]["valeur"] = "+33 1 00 00 00 00"
    champs["siret"]["valeur"] = "000 000 000 00000"
    champs["attestation_exclusions"]["valeur"] = "coche"
    champs["capacites"]["valeur"] = "dc2"
    ecrire_valeurs(dossier, valeurs)


def remplir_dc4(dossier: Path) -> None:
    valeurs = charger_valeurs(dossier)
    champs = valeurs["DC4"]["champs"]
    champs["sous_traitance"]["valeur"] = True
    champs["acheteur"]["valeur"] = "Mairie d'Exemple"
    champs["objet_marche"]["valeur"] = "Prestations d'essai (fictif)"
    champs["objet_declaration"]["valeur"] = "annexe_offre"
    champs["titulaire_denomination"]["valeur"] = "Entreprise Exemple SAS"
    champs["titulaire_email"]["valeur"] = "contact@exemple.test"
    champs["st_denomination"]["valeur"] = "Sous-Traitant Exemple SARL"
    champs["st_email"]["valeur"] = "st@exemple.test"
    champs["st_pme"]["valeur"] = "oui"
    champs["nature_prestations"]["valeur"] = "Assistance fictive"
    champs["taux_tva"]["valeur"] = "20 %"
    champs["montant_ht"]["valeur"] = "1 000 EUR"
    champs["montant_ttc"]["valeur"] = "1 200 EUR"
    champs["paiement_direct"]["valeur"] = "oui"
    champs["avance"]["valeur"] = "non"
    champs["duree_mois"]["valeur"] = "12 mois"
    champs["attestation_exclusions_st"]["valeur"] = "coche"
    ecrire_valeurs(dossier, valeurs)


# ---------------------------------------------------------------------------
# preparer
# ---------------------------------------------------------------------------

def test_preparer_cree_tous_les_champs_a_null(dossier: Path):
    valeurs = charger_valeurs(dossier)
    assert set(valeurs) == {"DC1", "DC2", "DC4"}
    champ = valeurs["DC2"]["champs"]["pme"]
    assert champ["valeur"] is None
    assert champ["type"] == "choix"
    assert champ["options"] == {"oui": 1, "non": 2}
    assert valeurs["DC1"]["champs"]["denomination"]["label"]
    assert valeurs["DC4"]["champs"]["sous_traitance"]["type"] == "drapeau"


def test_preparer_ne_remplace_jamais(dossier: Path, tmp_path: Path):
    valeurs = charger_valeurs(dossier)
    valeurs["DC1"]["champs"]["acheteur"]["valeur"] = "Mairie d'Exemple"
    ecrire_valeurs(dossier, valeurs)
    with pytest.raises(espace.Erreur):
        candidature.preparer(dossier)
    assert charger_valeurs(dossier)["DC1"]["champs"]["acheteur"]["valeur"] \
        == "Mairie d'Exemple"


def test_preparer_hors_dossier_reponse(tmp_path: Path):
    with pytest.raises(espace.Erreur):
        candidature.preparer(tmp_path)


# ---------------------------------------------------------------------------
# remplir
# ---------------------------------------------------------------------------

def test_remplir_sans_valeurs_echoue(tmp_path: Path):
    source = tmp_path / "DCE"
    source.mkdir()
    fabriquer_docx(source / "1-RC.docx")
    dossier = tmp_path / "reponse"
    espace.initialiser(source, dossier)
    with pytest.raises(espace.Erreur):
        candidature.remplir(dossier)


def test_remplir_dc1_ecrit_aux_bons_endroits(dossier: Path):
    remplir_dc1(dossier)
    resultat = candidature.remplir(dossier)
    assert [p["formulaire"] for p in resultat["produits"]] == ["DC1", "DC2"]
    assert resultat["non_produits"][0]["formulaire"] == "DC4"
    assert resultat["anomalies"] == {}

    paragraphes, xml = paragraphs_xml(dossier / "candidature" / "DC1.docx")
    assert "Mairie d'Exemple" in paragraphes[19]
    assert "[réf. : 2026-001]" in paragraphes[19]
    assert "Prestations d'essai (fictif)" in paragraphes[29]
    # le libellé reste intègre : la valeur tombe en fin de ligne, pas au
    # milieu du mot « unité » coupé entre deux runs
    assert "l’unité ou de l’établissement" in paragraphes[64]
    assert paragraphes[64].endswith("Entreprise Exemple SAS")
    assert paragraphes[68].endswith("1 rue du Test, 00000 Nulle Part")
    assert paragraphes[80].endswith("000 000 000 00000")
    assert "pour le lot n° 1 — Lot fictif ou les lots n°" in paragraphes[52]
    assert cases_cochees(xml) == [3, 4, 10, 11]


def test_remplir_dc1_laisse_vides_les_champs_sans_valeur(dossier: Path):
    valeurs = charger_valeurs(dossier)
    valeurs["DC1"]["champs"]["denomination"]["valeur"] = "Entreprise Exemple SAS"
    ecrire_valeurs(dossier, valeurs)
    resultat = candidature.remplir(dossier)
    assert "denomination" not in resultat["non_remplis"]["DC1"]
    assert "acheteur" in resultat["non_remplis"]["DC1"]
    assert "lot_numero" in resultat["optionnels_vides"]["DC1"]
    paragraphes, _ = paragraphs_xml(dossier / "candidature" / "DC1.docx")
    assert paragraphes[19] == "A - Identification de l’acheteur"
    assert paragraphes[64].endswith("Entreprise Exemple SAS")


def test_remplir_dc2_ecrit_aux_bons_endroits(dossier: Path):
    valeurs = charger_valeurs(dossier)
    champs = valeurs["DC2"]["champs"]
    champs["denomination"]["valeur"] = "Entreprise Exemple SAS"
    champs["adresse"]["valeur"] = "1 rue du Test"
    champs["email"]["valeur"] = "contact@exemple.test"
    champs["siret"]["valeur"] = "000 000 000 00000"
    champs["forme_juridique"]["valeur"] = "SAS (fictif)"
    champs["pme"]["valeur"] = "oui"
    champs["inscription_registre"]["valeur"] = "RCS Nulle Part 000 000 000"
    champs["ca_exercices"]["valeur"] = "2024 : 10 000 EUR HT (fictif)"
    champs["capacite_technique"]["valeur"] = "Références fictives"
    champs["preuves_en_ligne_eco"]["valeur"] = "https://exemple.test/eco"
    champs["preuves_en_ligne_technique"]["valeur"] = "https://exemple.test/tech"
    ecrire_valeurs(dossier, valeurs)
    candidature.remplir(dossier)

    paragraphes, xml = paragraphs_xml(dossier / "candidature" / "DC2.docx")
    # l'identité tombe bien sur la ligne du champ (2ᵉ occurrence du libellé),
    # pas sur l'encadré d'intro de la rubrique C1 (paragraphe 40)
    assert "Entreprise Exemple SAS" in paragraphes[42]
    assert "Entreprise Exemple SAS" not in paragraphes[40]
    assert paragraphes[45].endswith("1 rue du Test")
    assert "RCS Nulle Part" in paragraphes[166]
    assert "10 000 EUR HT (fictif)" in paragraphes[202]
    assert "Références fictives" in paragraphes[250]
    # preuves F4 et G2 : 2ᵉ et 3ᵉ occurrences de « - Adresse internet »,
    # pas la ligne de C3 (paragraphe 147)
    assert "https://exemple.test/eco" in paragraphes[237]
    assert "https://exemple.test/tech" in paragraphes[261]
    assert "https://exemple.test" not in "".join(paragraphes[145:152])
    assert cases_cochees(xml) == [1]


def test_remplir_dc4_produit_seulement_avec_sous_traitance(dossier: Path):
    remplir_dc4(dossier)
    candidature.remplir(dossier)
    assert (dossier / "candidature" / "DC4.docx").exists()

    valeurs = charger_valeurs(dossier)
    valeurs["DC4"]["champs"]["sous_traitance"]["valeur"] = False
    ecrire_valeurs(dossier, valeurs)
    (dossier / "candidature" / "DC4.docx").unlink()
    resultat = candidature.remplir(dossier)
    assert not (dossier / "candidature" / "DC4.docx").exists()
    assert resultat["non_produits"][0]["formulaire"] == "DC4"


def test_remplir_dc4_distingue_titulaire_et_sous_traitant(dossier: Path):
    remplir_dc4(dossier)
    resultat = candidature.remplir(dossier)
    assert resultat["anomalies"] == {}
    paragraphes, xml = paragraphs_xml(dossier / "candidature" / "DC4.docx")
    # D (titulaire) et E (sous-traitant) portent les mêmes libellés : la
    # 1ʳᵉ occurrence va au titulaire, la 2ᵉ au sous-traitant
    assert paragraphes[51].endswith("Entreprise Exemple SAS")
    assert "Sous-Traitant Exemple SARL" not in paragraphes[51]
    assert paragraphes[73].endswith("Sous-Traitant Exemple SARL")
    assert "Entreprise Exemple SAS" not in paragraphes[73]
    assert "contact@exemple.test" in paragraphes[57]
    assert "st@exemple.test" in paragraphes[77]
    assert "20 %" in paragraphes[132]
    assert "1 000 EUR" in paragraphes[133]
    assert "1 200 EUR" in paragraphes[134]
    assert "12 mois" in paragraphes[168]
    assert cases_noircies(xml) == [1, 4, 10, 13, 14]
    # chaque case noircie l'est dans les deux représentations
    blocs = [
        m.group(0)
        for m in re.finditer(
            r"<mc:AlternateContent>.*?</mc:AlternateContent>", xml, re.S
        )
        if 'coordsize="147955,147955"' in m.group(0)
    ]
    for index in (1, 4, 10, 13, 14):
        bloc = blocs[index - 1]
        assert 'fillcolor="#000000"' in bloc
        assert "<a:solidFill><a:srgbClr val=\"000000\"/></a:solidFill>" in bloc


def test_choix_hors_liste_est_anomalie_et_ne_coche_rien(dossier: Path):
    valeurs = charger_valeurs(dossier)
    valeurs["DC1"]["champs"]["presentation"]["valeur"] = "improviste"
    ecrire_valeurs(dossier, valeurs)
    resultat = candidature.remplir(dossier)
    assert "presentation" in resultat["anomalies"]["DC1"]
    _, xml = paragraphs_xml(dossier / "candidature" / "DC1.docx")
    assert cases_cochees(xml) == []


def test_docx_produit_est_un_zip_et_un_xml_valides(dossier: Path):
    remplir_dc1(dossier)
    remplir_dc4(dossier)
    candidature.remplir(dossier)
    for nom in ("DC1.docx", "DC2.docx", "DC4.docx"):
        chemin = dossier / "candidature" / nom
        with zipfile.ZipFile(chemin) as archive:
            assert archive.testzip() is None
            ElementTree.fromstring(archive.read("word/document.xml"))
        from docx import Document

        Document(str(chemin))


def test_caracteres_xml_echappes(dossier: Path):
    valeurs = charger_valeurs(dossier)
    valeurs["DC1"]["champs"]["denomination"]["valeur"] = "A<R> & B"
    ecrire_valeurs(dossier, valeurs)
    candidature.remplir(dossier)
    _, xml = paragraphs_xml(dossier / "candidature" / "DC1.docx")
    assert "A&lt;R&gt; &amp; B" in xml
    from docx import Document

    textes = [p.text for p in Document(str(dossier / "candidature" / "DC1.docx")).paragraphs]
    assert any(t.endswith("A<R> & B") for t in textes)
