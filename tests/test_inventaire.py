"""Tests de remporte.inventaire : classification par nom et par contenu."""

from __future__ import annotations

from pathlib import Path

from remporte.inventaire import classer, pieces_attendues_absentes


def test_classer_par_nom():
    cas = [
        ("RC.pdf", "RC"),
        ("reglement_consultation.docx", "RC"),
        ("2-CCAP-v2.pdf", "CCAP"),
        ("cctp_lot1.pdf", "CCTP"),
        ("CRT.docx", "CRT"),
        ("cahier-des-reponses.docx", "CRT"),
        ("ATTRI1.pdf", "AE"),
        ("acte d'engagement.docx", "AE"),
        ("AE_lot2.docx", "AE"),
        ("04-AE.doc", "AE"),
        ("BPU.xlsx", "BPU"),
        ("bordereau_prix.xls", "BPU"),
        ("4-DPGF-AE.xls", "DPGF"),
        ("DQE.xlsx", "DQE"),
        ("Ann._financ._BPU.ods", "BPU"),
        ("aapc.pdf", "AAPC"),
        ("DC1.pdf", "DC1"),
        ("DC2.docx", "DC2"),
        ("dc-4.pdf", "DC4"),
        ("DUME.docx", "DUME"),
        ("annexe technique.pdf", "ANNEXE"),
        ("questions-reponses.pdf", "QR"),
        ("plan- intervention.pdf", "AUTRE"),
    ]
    for nom, attendu in cas:
        resultat = classer(Path(nom), "")
        assert resultat.type == attendu, f"{nom} → {resultat.type} ≠ {attendu}"
        if attendu != "AUTRE":
            assert resultat.indice == "nom"


def test_classer_sigle_non_colle_aux_lettres():
    # « Maecenas » contient « ae » : le sigle AE ne doit pas s'y accrocher.
    assert classer(Path("Maecenas.pdf"), "").type == "AUTRE"
    # « circuit » contient « rc » : pas un RC.
    assert classer(Path("circuit.pdf"), "").type == "AUTRE"


def test_classer_par_contenu():
    texte_rc = "EN-TÊTE\n\nRèglement de la consultation\n\nArticle 1 : objet."
    assert classer(Path("piece1.pdf"), texte_rc).type == "RC"
    assert classer(Path("piece1.pdf"), texte_rc).indice == "contenu"
    texte_ae = "ACTE D’ENGAGEMENT\n\n Identification du pouvoir adjudicateur"
    assert classer(Path("piece2.pdf"), texte_ae).type == "AE"
    texte_cctp = "CAHIER DES CLAUSES TECHNIQUES PARTICULIÈRES"
    assert classer(Path("piece3.pdf"), texte_cctp).type == "CCTP"


def test_classer_sans_indice():
    resultat = classer(Path("document.pdf"), "")
    assert resultat.type == "AUTRE"
    assert resultat.indice == "aucun"


def test_lot_detecte_dans_le_nom():
    cas = [
        ("cctp lot 2.pdf", "2"),
        ("DQE-LOT02.xls", "2"),
        ("L2_CCTP.docx", "2"),
        ("planning-l12.pdf", "12"),
    ]
    for nom, lot in cas:
        assert classer(Path(nom), "").lot == lot
    assert classer(Path("cctp.pdf"), "").lot is None


def test_classer_prend_la_premiere_mention_de_l_en_tete():
    """Le type est celui de la première mention de l'en-tête, pas celui de la
    première catégorie de la liste : un acte d'engagement qui cite le CCAP
    plus bas reste un AE."""
    texte_ae = (
        "ACTE D’ENGAGEMENT\n\n"
        "Identification du candidat : Entreprise Exemple.\n\n"
        "Le candidat reconnaît avoir pris connaissance du cahier des clauses "
        "administratives (CCAP) du marché."
    )
    resultat = classer(Path("piece4.txt"), texte_ae)
    assert resultat.type == "AE"
    assert resultat.indice == "contenu"
    # et l'inverse : un CCAP qui cite l'acte d'engagement plus bas reste un CCAP
    texte_ccap = (
        "CAHIER DES CLAUSES ADMINISTRATIVES\n\n"
        "Le titulaire signe un acte d’engagement au moment de la remise de l’offre."
    )
    assert classer(Path("piece5.txt"), texte_ccap).type == "CCAP"


def test_classer_cadre_de_memoire_technique_est_un_crt():
    """« Cadre de mémoire technique » est le même type que « Cadre de réponse
    technique » : un CRT, au nom comme à l'en-tête."""
    par_nom = classer(Path("cadre-de-memoire-technique.docx"), "")
    assert par_nom.type == "CRT"
    assert par_nom.indice == "nom"
    texte = (
        "CADRE DE MÉMOIRE TECHNIQUE\n\n"
        "Présentation de l'offre technique de l'Entreprise Exemple."
    )
    par_contenu = classer(Path("piece6.txt"), texte)
    assert par_contenu.type == "CRT"
    assert par_contenu.indice == "contenu"
    # non-régression : le cadre de réponse technique reste un CRT
    assert classer(Path("cadre-de-reponse-technique.docx"), "").type == "CRT"


def test_pieces_attendues_absentes():
    messages = pieces_attendues_absentes({"CCTP", "BPU"})
    assert any("règlement de consultation" in m for m in messages)
    assert any("cahier des réponses" in m for m in messages)
    messages = pieces_attendues_absentes({"RC"})
    assert not any("règlement de consultation" in m for m in messages)
    assert any("cahier des réponses" in m for m in messages)
    assert pieces_attendues_absentes({"RC", "CRT"}) == []
