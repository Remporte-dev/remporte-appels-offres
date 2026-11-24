"""Tests de la commande `remporte convertir` : conversion simplifiée (secours
Python), chemin LibreOffice (faux soffice), non-écrasement, destination par
défaut (dossier de réponse ou à côté de l'original), options, erreurs et JSON.

Chaque refus vérifie un code de sortie non nul et des fichiers inchangés
(octets avant/après), rien de créé.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

import pytest
from conftest import chemin_fixture, fabriquer_docx, fabriquer_xlsx

from remporte.cli import main


# ---------------------------------------------------------------------------
# Aides : empreintes, tri des lots (style test_livraison_lot), détection LibreOffice
# ---------------------------------------------------------------------------

def empreinte(chemin: Path) -> str:
    return hashlib.sha256(chemin.read_bytes()).hexdigest()


def empreintes_dossier(racine: Path) -> dict[str, str]:
    """Empreinte de chaque fichier du dossier : une commande refusée ne doit
    rien modifier, ni rien ajouter."""
    empreintes: dict[str, str] = {}
    for chemin in sorted(racine.rglob("*")):
        if chemin.is_file():
            empreintes[chemin.relative_to(racine).as_posix()] = empreinte(chemin)
    return empreintes


@pytest.fixture()
def sans_libreoffice(monkeypatch, tmp_path):
    """Aucun LibreOffice détectable : PATH vide, chemins codés en dur absents."""
    from remporte import conversion

    vide = tmp_path / "sans-bin"
    vide.mkdir()
    monkeypatch.setenv("PATH", str(vide))
    monkeypatch.setattr(conversion, "_CHEMINS_SOFFICE", ())


@pytest.fixture()
def faux_soffice(monkeypatch, tmp_path):
    """Faux `soffice` en tête du PATH : vérifie ses arguments et écrit le
    fichier attendu par LibreOffice (<nom>.<format> dans --outdir)."""
    if os.name == "nt":
        pytest.skip("le faux soffice est un script à shebang, que Windows n'exécute pas")
    binaires = tmp_path / "bin"
    binaires.mkdir()
    script = binaires / "soffice"
    script.write_text(
        f"#!{sys.executable}\n"
        "import sys, pathlib\n"
        "args = sys.argv[1:]\n"
        "assert '--headless' in args, args\n"
        "format_moderne = args[args.index('--convert-to') + 1]\n"
        "assert format_moderne in {'xlsx', 'docx'}, format_moderne\n"
        "sortie = pathlib.Path(args[args.index('--outdir') + 1])\n"
        "source = pathlib.Path(args[-1])\n"
        "assert source.suffix.lower() in {'.xls', '.doc'}, source\n"
        "assert str(source) in args\n"
        "(sortie / (source.stem + '.' + format_moderne)).write_bytes("
        "b'produit par LibreOffice\\n')\n",
        encoding="utf-8",
    )
    script.chmod(0o755)
    monkeypatch.setenv("PATH", str(binaires))
    from remporte import conversion

    monkeypatch.setattr(conversion, "_CHEMINS_SOFFICE", ())


def tri_alloti() -> dict:
    """Tri alloti valide, deux lots, RC et DPGF réparties dans le lot 02. Le
    choix des lots reste vide : seule la commande de choix l'écrit."""
    return {
        "schema_version": 1,
        "allotissement": "lots",
        "lots": [
            {"id": "02", "intitule": "Électricité courants forts",
             "pieces": ["dce/1-RC.docx", "dce/dpgf-exemple.xls"],
             "parties_communes": [],
             "recommandation": {"avis": "repondre",
                                "raison": "Cœur du métier de l'entreprise (fictif)."}},
            {"id": "05", "intitule": "Ventilation mécanique",
             "pieces": [], "parties_communes": [],
             "recommandation": {"avis": "a_discuter",
                                "raison": "Sous-traitance probable (fictif)."}},
        ],
        "pieces_communes": [],
        "pieces_illisibles": [],
        "types_pieces": {"dce/1-RC.docx": "RC", "dce/dpgf-exemple.xls": "DPGF"},
        "choix": None,
    }


def enregistrer_tri(dossier: Path, tri: dict) -> None:
    """Écrit le tri (sans choix) et le fait valider par `lots enregistrer`."""
    chemin = dossier / "memoire" / "lots.json"
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text(
        json.dumps(tri, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    assert main(["lots", "enregistrer", "--dossier", str(dossier)]) == 0


def choisir_lots(dossier: Path, ids: str, par: str = "Camille Exemple") -> None:
    """Fait choisir les lots retenus par la commande — jamais à la main."""
    assert main(["lots", "choisir", "--lots", ids, "--par", par,
                 "--dossier", str(dossier)]) == 0


def dossier_de_reponse(tmp_path: Path, avec_xls: bool = True) -> tuple[Path, Path | None]:
    """Dossier de réponse initialisé depuis un DCE minimal, avec en plus la
    DPGF d'exemple en .xls. Rend le dossier et le chemin du .xls dans dce/."""
    source = tmp_path / "DCE"
    source.mkdir()
    fabriquer_docx(source / "1-RC.docx")
    if avec_xls:
        shutil.copy(chemin_fixture("dpgf-exemple.xls"), source / "dpgf-exemple.xls")
    dossier = tmp_path / "reponse"
    assert main(["init", str(source), "--dossier", str(dossier)]) == 0
    return dossier, (dossier / "dce" / "dpgf-exemple.xls" if avec_xls else None)


# ---------------------------------------------------------------------------
# Point 9 : conversion simplifiée d'un .xls (sans LibreOffice)
# ---------------------------------------------------------------------------

def test_convertir_xls_secours_et_copie_relise(tmp_path: Path, sans_libreoffice,
                                               capsys):
    source = chemin_fixture("dpgf-exemple.xls")
    sortie = tmp_path / "dpgf.xlsx"
    assert main(["convertir", str(source), "--sortie", str(sortie)]) == 0
    texte = capsys.readouterr().out
    assert str(sortie) in texte
    assert "conversion simplifiée" in texte
    assert "Perdu" in texte
    assert "formules" in texte
    assert "Pour une conversion fidèle, installez LibreOffice" in texte

    from openpyxl import load_workbook

    classeur = load_workbook(sortie)
    assert classeur.sheetnames == ["DPGF Lot 02", "PSE éclairage"]
    feuille = classeur["DPGF Lot 02"]
    assert feuille["A1"].value == "RÉNOVATION DE L'ÉCOLE DES TILLEULS - LOT 02 ÉLECTRICITÉ"
    assert feuille["A1"].font.bold
    assert "A1:F1" in [str(plage) for plage in feuille.merged_cells.ranges]
    assert feuille.column_dimensions["B"].width >= 55
    assert feuille["E4"].value == 1850
    assert feuille["E4"].number_format == "#,##0.00"
    date_remise = feuille["C10"].value
    assert hasattr(date_remise, "year")
    assert (date_remise.year, date_remise.month, date_remise.day) == (2026, 12, 15)
    assert feuille["C11"].value is False
    assert feuille["B5"].value == "Prise de courant 16 A"


# ---------------------------------------------------------------------------
# Point 10 : conversion simplifiée d'un .doc
# ---------------------------------------------------------------------------

def test_convertir_doc_secours_et_copie_relise(tmp_path: Path, sans_libreoffice,
                                               capsys):
    source = chemin_fixture("dc1-exemple.doc")
    sortie = tmp_path / "dc1.docx"
    assert main(["convertir", str(source), "--sortie", str(sortie)]) == 0
    texte = capsys.readouterr().out
    assert "conversion simplifiée" in texte
    assert "mise en page" in texte
    assert "tableaux" in texte
    assert "cases à cocher" in texte

    from docx import Document

    document = Document(sortie)
    paragraphes = [p.text for p in document.paragraphs if p.text.strip()]
    assert paragraphes[0] == "Lettre de candidature (DC1)"
    for phrase in ("Identification de l’acheteur : Communauté de communes "
                   "du Val Fictif",
                   "Nom commercial", "Dénomination sociale",
                   "Entreprise Exemple", "Exemple SAS",
                   "Date de la dernière mise à jour : 01/04/2019"):
        assert phrase in paragraphes, phrase


# ---------------------------------------------------------------------------
# Point 11 : chemin LibreOffice (faux soffice) et repli sur le secours
# ---------------------------------------------------------------------------

def test_convertir_avec_libreoffice(tmp_path: Path, faux_soffice, capsys):
    source = chemin_fixture("dpgf-exemple.xls")
    sortie = tmp_path / "dpgf.xlsx"
    assert main(["convertir", str(source), "--sortie", str(sortie)]) == 0
    texte = capsys.readouterr().out
    assert "Méthode : LibreOffice" in texte
    assert "Perdu" not in texte
    assert "Pour une conversion fidèle" not in texte
    assert sortie.read_bytes() == b"produit par LibreOffice\n"


def test_convertir_libreoffice_echoue_repli_secours(monkeypatch, tmp_path,
                                                    capsys):
    """LibreOffice présent mais muet : le secours prend le relais."""
    from remporte import conversion

    binaires = tmp_path / "bin"
    binaires.mkdir()
    script = binaires / "soffice"
    script.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
    script.chmod(0o755)
    monkeypatch.setenv("PATH", str(binaires))
    monkeypatch.setattr(conversion, "_CHEMINS_SOFFICE", ())
    source = chemin_fixture("dc1-exemple.doc")
    sortie = tmp_path / "dc1.docx"
    assert main(["convertir", str(source), "--sortie", str(sortie)]) == 0
    assert "conversion simplifiée" in capsys.readouterr().out
    assert sortie.is_file()


# ---------------------------------------------------------------------------
# Point 12 : jamais d'écrasement
# ---------------------------------------------------------------------------

def test_convertir_n_ecrase_jamais(tmp_path: Path, sans_libreoffice, capsys):
    source = tmp_path / "DPGF.xls"
    shutil.copy(chemin_fixture("dpgf-exemple.xls"), source)
    original = empreinte(source)

    assert main(["convertir", str(source)]) == 0
    capsys.readouterr()
    premiere = tmp_path / "DPGF.xlsx"
    assert premiere.is_file()
    contenu_premiere = empreinte(premiere)
    assert empreinte(source) == original  # l'original n'est pas modifié

    assert main(["convertir", str(source)]) == 0
    capsys.readouterr()
    assert empreinte(premiere) == contenu_premiere  # pas écrasée
    assert (tmp_path / "DPGF (2).xlsx").is_file()
    assert main(["convertir", str(source)]) == 0
    capsys.readouterr()
    assert (tmp_path / "DPGF (3).xlsx").is_file()


def test_convertir_sortie_existante_decale_a_cote(tmp_path: Path,
                                                  sans_libreoffice, capsys):
    source = chemin_fixture("dpgf-exemple.xls")
    sortie = tmp_path / "dpgf.xlsx"
    deja_la = "copie déjà là, jamais remplacée".encode("utf-8")
    sortie.write_bytes(deja_la)
    assert main(["convertir", str(source), "--sortie", str(sortie)]) == 0
    decallee = tmp_path / "dpgf (2).xlsx"
    assert decallee.is_file()
    assert sortie.read_bytes() == deja_la


# ---------------------------------------------------------------------------
# Point 13 : destination par défaut dans un dossier de réponse
# ---------------------------------------------------------------------------

def test_convertir_dans_dossier_de_reponse_sans_tri(tmp_path: Path,
                                                    sans_libreoffice, capsys):
    dossier, xls = dossier_de_reponse(tmp_path)
    assert main(["convertir", str(xls)]) == 0
    produite = dossier / "reponse" / "dpgf-exemple.xlsx"
    assert produite.is_file()


def test_convertir_dans_le_dossier_du_lot_retenu_seul(tmp_path: Path,
                                                      sans_libreoffice, capsys):
    dossier, xls = dossier_de_reponse(tmp_path)
    enregistrer_tri(dossier, tri_alloti())
    choisir_lots(dossier, "02")
    capsys.readouterr()
    assert main(["convertir", str(xls)]) == 0
    produite = dossier / "reponse" / "Lot 02 - Électricité courants forts" / \
        "dpgf-exemple.xlsx"
    assert produite.is_file()


def test_convertir_exige_le_lot_quand_plusieurs_sont_retenus(
        tmp_path: Path, sans_libreoffice, capsys):
    dossier, xls = dossier_de_reponse(tmp_path)
    enregistrer_tri(dossier, tri_alloti())
    choisir_lots(dossier, "02,05")
    capsys.readouterr()
    avant = empreintes_dossier(dossier)
    assert main(["convertir", str(xls)]) != 0
    message = "".join(capsys.readouterr())
    # même refus et même message que `livraison dossier`
    assert "Choisissez le lot avec --lot parmi : 02, 05." in message
    assert empreintes_dossier(dossier) == avant
    assert not (dossier / "reponse").exists()


def test_convertir_avec_lot_rend_dans_le_dossier_du_lot_demande(
        tmp_path: Path, sans_libreoffice, capsys):
    dossier, xls = dossier_de_reponse(tmp_path)
    enregistrer_tri(dossier, tri_alloti())
    choisir_lots(dossier, "02,05")
    capsys.readouterr()
    assert main(["convertir", str(xls), "--lot", "02"]) == 0
    produite = dossier / "reponse" / "Lot 02 - Électricité courants forts" / \
        "dpgf-exemple.xlsx"
    assert produite.is_file()


def test_convertir_refuse_un_lot_non_retenu(tmp_path: Path, sans_libreoffice,
                                            capsys):
    dossier, xls = dossier_de_reponse(tmp_path)
    enregistrer_tri(dossier, tri_alloti())
    choisir_lots(dossier, "02")
    capsys.readouterr()
    avant = empreintes_dossier(dossier)
    assert main(["convertir", str(xls), "--lot", "07"]) != 0
    message = "".join(capsys.readouterr())
    assert "07" in message
    assert empreintes_dossier(dossier) == avant
    assert not (dossier / "reponse").exists()


# ---------------------------------------------------------------------------
# Point 14 : hors dossier de réponse
# ---------------------------------------------------------------------------

def test_convertir_hors_dossier_de_reponse_a_cote_de_l_original(
        tmp_path: Path, sans_libreoffice, capsys):
    source = tmp_path / "attestation.doc"
    shutil.copy(chemin_fixture("attestation-visite-exemple.doc"), source)
    assert main(["convertir", str(source)]) == 0
    produite = tmp_path / "attestation.docx"
    assert produite.is_file()
    assert not list(tmp_path.rglob("reponse"))


def test_convertir_refuse_lot_hors_dossier_de_reponse(tmp_path: Path,
                                                      sans_libreoffice, capsys):
    source = tmp_path / "attestation.doc"
    shutil.copy(chemin_fixture("attestation-visite-exemple.doc"), source)
    avant = empreintes_dossier(tmp_path)
    assert main(["convertir", str(source), "--lot", "02"]) != 0
    message = "".join(capsys.readouterr())
    # phrase imposée par la spécification
    assert "--lot ne s'utilise que dans un dossier de réponse." in message
    assert empreintes_dossier(tmp_path) == avant


# ---------------------------------------------------------------------------
# Point 15 : --lot et --sortie, extensions
# ---------------------------------------------------------------------------

def test_convertir_refuse_lot_avec_sortie(tmp_path: Path, sans_libreoffice,
                                          capsys):
    source = tmp_path / "attestation.doc"
    shutil.copy(chemin_fixture("attestation-visite-exemple.doc"), source)
    sortie = tmp_path / "autre.docx"
    avant = empreintes_dossier(tmp_path)
    assert main(["convertir", str(source), "--lot", "02",
                 "--sortie", str(sortie)]) != 0
    message = "".join(capsys.readouterr())
    # phrase imposée par la spécification
    assert "--lot et --sortie ne se combinent pas." in message
    assert empreintes_dossier(tmp_path) == avant
    assert not sortie.exists()


def test_convertir_refuse_mauvaise_extension_de_sortie(tmp_path: Path,
                                                       sans_libreoffice,
                                                       capsys):
    source = chemin_fixture("dpgf-exemple.xls")
    assert main(["convertir", str(source), "--sortie",
                 str(tmp_path / "dpgf.docx")]) != 0
    message = "".join(capsys.readouterr())
    # phrases imposées par la spécification
    assert "La copie d'un .xls se termine par .xlsx." in message
    assert not (tmp_path / "dpgf.docx").exists()

    source = chemin_fixture("dc1-exemple.doc")
    assert main(["convertir", str(source), "--sortie",
                 str(tmp_path / "dc1.xlsx")]) != 0
    message = "".join(capsys.readouterr())
    assert "La copie d'un .doc se termine par .docx." in message
    assert not (tmp_path / "dc1.xlsx").exists()


def test_convertir_extension_de_sortie_en_majuscules_acceptee(
        tmp_path: Path, sans_libreoffice, capsys):
    source = chemin_fixture("dpgf-exemple.xls")
    sortie = tmp_path / "X.XLSX"
    assert main(["convertir", str(source), "--sortie", str(sortie)]) == 0
    assert sortie.is_file()


# ---------------------------------------------------------------------------
# Point 16 : erreurs, en texte puis en JSON
# ---------------------------------------------------------------------------

def test_convertir_fichier_absent(tmp_path: Path, capsys):
    absent = tmp_path / "nul.part"
    assert main(["convertir", str(absent)]) == 1
    message = capsys.readouterr().err
    # phrase imposée par la spécification
    assert f"Fichier introuvable : {absent}." in message


def test_convertir_format_non_convertible(tmp_path: Path, capsys):
    source = fabriquer_xlsx(tmp_path / "deja-moderne.xlsx")
    avant = empreintes_dossier(tmp_path)
    assert main(["convertir", str(source)]) == 1
    message = capsys.readouterr().err
    assert "La conversion concerne les anciens formats .doc et .xls" in message
    assert "reçu : .xlsx" in message
    assert empreintes_dossier(tmp_path) == avant


def test_convertir_doc_illisible_sans_libreoffice(tmp_path: Path,
                                                  sans_libreoffice, capsys):
    source = tmp_path / "casse.doc"
    source.write_bytes(chemin_fixture("dc1-exemple.doc").read_bytes()[:600])
    assert main(["convertir", str(source)]) == 1
    message = capsys.readouterr().err
    assert "ne peut pas être lu" in message
    assert "conversion impossible sans LibreOffice" in message
    assert not (tmp_path / "casse.docx").exists()
    assert not list(tmp_path.glob("* (2)*"))


def test_convertir_fichier_sans_extension(tmp_path: Path, capsys):
    source = tmp_path / "sans-extension"
    source.write_bytes(b"n'importe quoi")
    assert main(["convertir", str(source)]) == 1
    assert "sans extension" in capsys.readouterr().err


@pytest.mark.parametrize("cas", ["absent", "xlsx", "doc-illisible"])
def test_convertir_erreurs_en_json(tmp_path: Path, sans_libreoffice, capsys,
                                   cas):
    if cas == "absent":
        cible = str(tmp_path / "nul.part")
        commande = ["convertir", cible]
    elif cas == "xlsx":
        cible = str(fabriquer_xlsx(tmp_path / "deja-moderne.xlsx"))
        commande = ["convertir", cible]
    else:
        casse = tmp_path / "casse.doc"
        casse.write_bytes(chemin_fixture("dc1-exemple.doc").read_bytes()[:600])
        cible = str(casse)
        commande = ["convertir", cible]
    assert main([*commande, "--json"]) == 1
    cap = capsys.readouterr()
    donnees = json.loads(cap.out)
    assert donnees["ok"] is False
    assert donnees["erreur"]  # un message d'erreur, sur stdout en JSON
    assert cap.err == ""


# ---------------------------------------------------------------------------
# Point 17 : --json en réussite
# ---------------------------------------------------------------------------

def test_convertir_json_en_reussite(tmp_path: Path, sans_libreoffice, capsys):
    source = chemin_fixture("dc1-exemple.doc")
    sortie = tmp_path / "dc1.docx"
    assert main(["convertir", str(source), "--sortie", str(sortie),
                 "--json"]) == 0
    donnees = json.loads(capsys.readouterr().out)
    assert donnees["ok"] is True
    assert donnees["fichier"] == str(sortie)
    assert donnees["methode"] == "conversion simplifiée"
    assert donnees["pertes"]
    assert donnees["conseil"]


# ---------------------------------------------------------------------------
# Point 18 : aucun fichier temporaire laissé
# ---------------------------------------------------------------------------

def test_convertir_sans_fichier_temporaire(tmp_path: Path, sans_libreoffice,
                                           capsys):
    dossier, xls = dossier_de_reponse(tmp_path)
    avant = empreintes_dossier(dossier)
    assert main(["convertir", str(xls)]) == 0
    apres = empreintes_dossier(dossier)
    nouveaux = sorted(chemin for chemin in apres if chemin not in avant)
    # le dossier de remise ne contient que la copie, rien d'autre n'a bougé
    assert nouveaux == ["reponse/dpgf-exemple.xlsx"]
    assert [p.name for p in (dossier / "reponse").iterdir()] == \
        ["dpgf-exemple.xlsx"]
    # le dossier de l'original n'a gagné aucun fichier
    assert [c for c in apres if c.startswith("dce/")] == \
        [c for c in avant if c.startswith("dce/")]
