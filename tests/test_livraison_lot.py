"""Tests du lot B — dossier de remise par lot : `remporte livraison dossier`
(§ 4.4), `remporte candidature remplir` dans le dossier de remise (§ 4.5),
`remporte exporter` lu depuis les analyses par lot (§ 4.8) et le guide de
style (§ 4.9).

Les dossiers allotis sont préparés en écrivant `memoire/lots.json` au format
de la spec § 2 avec `choix` rempli (le choix des lots est testé ailleurs).
Chaque refus vérifie un code de sortie non nul et des fichiers inchangés.
"""

from __future__ import annotations

import hashlib
import json
import re
import zipfile
from pathlib import Path

import pytest
from conftest import fabriquer_docx

from remporte.cli import main


# ---------------------------------------------------------------------------
# Aides : dossier de réponse, memoire/lots.json, analyses par lot
# ---------------------------------------------------------------------------

@pytest.fixture()
def dossier(tmp_path: Path) -> Path:
    """Dossier de réponse initialisé depuis un DCE minimal (un RC)."""
    source = tmp_path / "DCE"
    source.mkdir()
    fabriquer_docx(source / "1-RC.docx")
    dossier = tmp_path / "reponse"
    assert main(["init", str(source), "--dossier", str(dossier)]) == 0
    return dossier


def ecrire_lots(dossier: Path, contenu: dict) -> Path:
    chemin = dossier / "memoire" / "lots.json"
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text(
        json.dumps(contenu, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return chemin


def lots_alloti(retenus: list[str], lots: list[dict] | None = None,
                choix: dict | None = None) -> dict:
    """Tri alloti valide (spec § 2), deux lots, RC répartie dans le lot 02."""
    if lots is None:
        lots = [
            {"id": "02", "intitule": "Électricité courants forts",
             "pieces": ["dce/1-RC.docx"], "parties_communes": [],
             "recommandation": {"avis": "repondre",
                                "raison": "Cœur du métier de l'entreprise (fictif)."}},
            {"id": "05", "intitule": "Ventilation mécanique",
             "pieces": [], "parties_communes": [],
             "recommandation": {"avis": "a_discuter",
                                "raison": "Sous-traitance probable (fictif)."}},
        ]
    if choix is None:
        choix = {"retenus": retenus, "par": "Camille Exemple",
                 "date": "2026-11-23T09:00:00+00:00"}
    return {
        "schema_version": 1,
        "allotissement": "lots",
        "lots": lots,
        "pieces_communes": [],
        "pieces_illisibles": [],
        "types_pieces": {"dce/1-RC.docx": "RC"},
        "choix": choix,
    }


def lots_unique() -> dict:
    """Tri d'un marché non alloti : un seul lot, id « unique », choix fait."""
    return {
        "schema_version": 1,
        "allotissement": "unique",
        "lots": [
            {"id": "unique", "intitule": "Prestation unique",
             "pieces": ["dce/1-RC.docx"], "parties_communes": [],
             "recommandation": {"avis": "repondre",
                                "raison": "Marché en une seule part (fictif)."}},
        ],
        "pieces_communes": [],
        "pieces_illisibles": [],
        "types_pieces": {"dce/1-RC.docx": "RC"},
        "choix": {"retenus": ["unique"], "par": "Camille Exemple",
                  "date": "2026-11-23T09:00:00+00:00"},
    }


def lot_intitule(id_: str, intitule: str) -> dict:
    return {"id": id_, "intitule": intitule, "pieces": ["dce/1-RC.docx"],
            "parties_communes": [],
            "recommandation": {"avis": "repondre", "raison": "Lot fictif d'essai."}}


RUBRIQUES_LOT = ["En bref", "Identité", "Ce que l'acheteur attend vraiment",
                 "Critères et pondérations", "Pièces à remettre et formes imposées",
                 "Incohérences entre pièces", "Pièces illisibles ou absentes",
                 "Documents de référence et versions", "Avis"]


def ecrire_analyse_lot(dossier: Path, id_: str, *, date_limite: str | None,
                       en_bref: str) -> Path:
    """`analyse/lot-<id>.md` rempli : les neuf rubriques, aucun marqueur."""
    identite = "| | |\n|---|---|\n| Acheteur | Ville d'Exemple |\n" \
               "| Objet | Réhabilitation des installations (fictif) |\n"
    if date_limite:
        identite += f"| Date limite de remise | {date_limite} |\n"
    corps = {
        "En bref": en_bref,
        "Identité": identite,
        "Ce que l'acheteur attend vraiment": "Une équipe présente sur site (fictif).",
        "Critères et pondérations":
            "| Critère | Pondération |\n|---|---|\n| Technique | 60 % |",
        "Pièces à remettre et formes imposées":
            "- DC1, DC2 et le mémoire technique.",
        "Incohérences entre pièces": "Aucune incohérence relevée (fictif).",
        "Pièces illisibles ou absentes": "Aucune.",
        "Documents de référence et versions": "RC version du 2 mars (fictif).",
        "Avis": "Répondre (fictif).",
    }
    lignes = [f"# Analyse du lot {id_}", ""]
    for rubrique in RUBRIQUES_LOT:
        lignes += [f"## {rubrique}", "", corps[rubrique], ""]
    chemin = dossier / "analyse" / f"lot-{id_}.md"
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text("\n".join(lignes), encoding="utf-8")
    return chemin


def empreinte(chemin: Path) -> str:
    return hashlib.sha256(chemin.read_bytes()).hexdigest()


def texte_docx(chemin: Path) -> str:
    with zipfile.ZipFile(chemin) as archive:
        xml = archive.read("word/document.xml").decode("utf-8")
    return re.sub(r"<[^>]+>", "", xml)


# ---------------------------------------------------------------------------
# § 4.4 — livraison dossier
# ---------------------------------------------------------------------------

def test_livraison_marche_non_alloti_rend_reponse(dossier: Path, capsys):
    ecrire_lots(dossier, lots_unique())
    assert main(["livraison", "dossier", "--dossier", str(dossier)]) == 0
    sortie = capsys.readouterr().out
    cible = dossier / "reponse"
    assert cible.is_dir()
    assert str(cible.resolve()) in sortie  # chemin absolu en sortie


def test_livraison_tri_absent_rend_reponse(dossier: Path, capsys):
    # pas de memoire/lots.json : le marché n'est pas alloti (ou pas encore trié)
    assert main(["livraison", "dossier", "--dossier", str(dossier)]) == 0
    assert (dossier / "reponse").is_dir()


def test_livraison_alloti_un_seul_lot_retenu_sans_option(dossier: Path, capsys):
    ecrire_lots(dossier, lots_alloti(["02"]))
    assert main(["livraison", "dossier", "--dossier", str(dossier)]) == 0
    sortie = capsys.readouterr().out
    cible = dossier / "reponse" / "Lot 02 - Électricité courants forts"
    assert cible.is_dir()
    assert str(cible.resolve()) in sortie
    dossiers = sorted(p.name for p in (dossier / "reponse").iterdir() if p.is_dir())
    assert dossiers == ["Lot 02 - Électricité courants forts"]


def test_livraison_remplace_les_caracteres_interdits_de_l_intitule(
        dossier: Path, capsys):
    ecrire_lots(dossier, lots_alloti(
        ["03"], lots=[lot_intitule("03", "Réseau : fibre/sécurité ?")]))
    assert main(["livraison", "dossier", "--dossier", str(dossier)]) == 0
    assert (dossier / "reponse" / "Lot 03 - Réseau - fibre-sécurité -").is_dir()


def test_livraison_retire_point_et_espace_de_fin_de_l_intitule(dossier: Path, capsys):
    ecrire_lots(dossier, lots_alloti(
        ["06", "07"],
        lots=[lot_intitule("06", "Voirie et réseaux divers."),
              lot_intitule("07", "Éclairage public ")]))
    assert main(["livraison", "dossier", "--lot", "06",
                 "--dossier", str(dossier)]) == 0
    assert (dossier / "reponse" / "Lot 06 - Voirie et réseaux divers").is_dir()
    assert not (dossier / "reponse" / "Lot 06 - Voirie et réseaux divers.").exists()
    assert main(["livraison", "dossier", "--lot", "07",
                 "--dossier", str(dossier)]) == 0
    assert (dossier / "reponse" / "Lot 07 - Éclairage public").is_dir()


def test_livraison_reprend_le_dossier_de_lot_existant(dossier: Path, capsys):
    ecrire_lots(dossier, lots_alloti(["02"]))
    ancien = dossier / "reponse" / "Lot 02 - Ancien intitulé"
    ancien.mkdir(parents=True)
    (ancien / "DC1.docx").write_bytes(b"contenu fictif")
    assert main(["livraison", "dossier", "--dossier", str(dossier)]) == 0
    sortie = capsys.readouterr().out
    assert str(ancien.resolve()) in sortie  # l'ancien dossier est rendu tel quel
    assert (ancien / "DC1.docx").read_bytes() == b"contenu fictif"
    dossiers = sorted(p.name for p in (dossier / "reponse").iterdir() if p.is_dir())
    # pas de second dossier malgré l'intitulé changé dans lots.json
    assert dossiers == ["Lot 02 - Ancien intitulé"]


def test_livraison_refuse_deux_dossiers_pour_le_meme_lot(dossier: Path, capsys):
    ecrire_lots(dossier, lots_alloti(["02"]))
    un = dossier / "reponse" / "Lot 02 - Premier intitulé"
    deux = dossier / "reponse" / "Lot 02 - Second intitulé"
    un.mkdir(parents=True)
    deux.mkdir(parents=True)
    (un / "note.txt").write_text("un", encoding="utf-8")
    (deux / "note.txt").write_text("deux", encoding="utf-8")
    assert main(["livraison", "dossier", "--dossier", str(dossier)]) != 0
    cap = capsys.readouterr()
    assert "Lot 02" in cap.out + cap.err
    # fichiers inchangés
    assert (un / "note.txt").read_text(encoding="utf-8") == "un"
    assert (deux / "note.txt").read_text(encoding="utf-8") == "deux"
    dossiers = sorted(p.name for p in (dossier / "reponse").iterdir() if p.is_dir())
    assert dossiers == ["Lot 02 - Premier intitulé", "Lot 02 - Second intitulé"]


def test_livraison_exige_le_lot_quand_plusieurs_sont_retenus(
        dossier: Path, capsys):
    ecrire_lots(dossier, lots_alloti(["02", "05"]))
    avant = empreinte(dossier / "memoire" / "lots.json")
    assert main(["livraison", "dossier", "--dossier", str(dossier)]) != 0
    message = "".join(capsys.readouterr())
    # la spec donne la phrase entre guillemets
    assert "Choisissez le lot avec --lot parmi : 02, 05." in message
    assert not (dossier / "reponse").exists()  # aucun fichier créé
    assert empreinte(dossier / "memoire" / "lots.json") == avant


def test_livraison_refuse_un_lot_non_retenu(dossier: Path, capsys):
    ecrire_lots(dossier, lots_alloti(["02"]))
    avant = empreinte(dossier / "memoire" / "lots.json")
    assert main(["livraison", "dossier", "--lot", "07",
                 "--dossier", str(dossier)]) != 0
    message = "".join(capsys.readouterr())
    assert "07" in message  # l'id fautif est nommé
    assert not (dossier / "reponse").exists()
    assert empreinte(dossier / "memoire" / "lots.json") == avant


def test_livraison_avec_lot_rend_le_dossier_du_lot_demande(dossier: Path, capsys):
    ecrire_lots(dossier, lots_alloti(["02", "05"]))
    assert main(["livraison", "dossier", "--lot", "05",
                 "--dossier", str(dossier)]) == 0
    sortie = capsys.readouterr().out
    cible = dossier / "reponse" / "Lot 05 - Ventilation mécanique"
    assert cible.is_dir()
    assert str(cible.resolve()) in sortie


def test_livraison_json_rend_un_seul_objet_avec_ok(dossier: Path, capsys):
    assert main(["livraison", "dossier", "--dossier", str(dossier), "--json"]) == 0
    brut = capsys.readouterr()
    assert json.loads(brut.out)["ok"] is True
    assert brut.err == ""


def test_livraison_json_en_erreur_rend_ok_false(dossier: Path, capsys):
    ecrire_lots(dossier, lots_alloti(["02"]))
    assert main(["livraison", "dossier", "--lot", "07",
                 "--dossier", str(dossier), "--json"]) != 0
    brut = capsys.readouterr()
    assert json.loads(brut.out)["ok"] is False


# ---------------------------------------------------------------------------
# § 4.5 — candidature remplir dans le dossier de remise
# ---------------------------------------------------------------------------

def preparer_candidature(dossier: Path) -> None:
    assert main(["candidature", "preparer", "--dossier", str(dossier)]) == 0
    chemin = dossier / "candidature" / "valeurs.json"
    valeurs = json.loads(chemin.read_text(encoding="utf-8"))
    valeurs["DC1"]["champs"]["denomination"]["valeur"] = "Entreprise Exemple SAS"
    chemin.write_text(
        json.dumps(valeurs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def test_candidature_remplir_ecrit_les_formulaires_dans_reponse(
        dossier: Path, capsys):
    preparer_candidature(dossier)
    valeurs_avant = empreinte(dossier / "candidature" / "valeurs.json")
    assert main(["candidature", "remplir", "--dossier", str(dossier)]) == 0
    for nom in ("DC1.docx", "DC2.docx"):
        assert (dossier / "reponse" / nom).is_file()
        assert not (dossier / "candidature" / nom).exists()
    assert not (dossier / "candidature" / "DC4.docx").exists()
    # valeurs.json reste à sa place et ne bouge pas
    assert empreinte(dossier / "candidature" / "valeurs.json") == valeurs_avant


def test_candidature_remplir_ecrit_dans_le_dossier_du_lot_alloti(
        dossier: Path, capsys):
    ecrire_lots(dossier, lots_alloti(["02"]))
    preparer_candidature(dossier)
    assert main(["candidature", "remplir", "--dossier", str(dossier)]) == 0
    cible = dossier / "reponse" / "Lot 02 - Électricité courants forts"
    assert (cible / "DC1.docx").is_file()
    assert (cible / "DC2.docx").is_file()
    assert not (dossier / "candidature" / "DC1.docx").exists()
    assert not (dossier / "candidature" / "DC2.docx").exists()


def test_candidature_remplir_refuse_le_second_appel_sans_remplacer(
        dossier: Path, capsys):
    preparer_candidature(dossier)
    assert main(["candidature", "remplir", "--dossier", str(dossier)]) == 0
    empreintes = {}
    for nom in ("DC1.docx", "DC2.docx"):
        chemin = dossier / "reponse" / nom
        empreintes[nom] = empreinte(chemin) if chemin.is_file() else None
    assert main(["candidature", "remplir", "--dossier", str(dossier)]) != 0
    message = "".join(capsys.readouterr())
    # la spec donne la phrase entre guillemets
    assert "DC1.docx existe déjà dans le dossier de remise" in message
    assert "retouché" in message
    assert "Confirmez" in message
    # aucun formulaire modifié, y compris DC2
    for nom, avant in empreintes.items():
        if avant is not None:
            assert empreinte(dossier / "reponse" / nom) == avant, nom


def test_candidature_remplir_reecrit_les_formulaires_avec_remplacer(
        dossier: Path, capsys):
    preparer_candidature(dossier)
    assert main(["candidature", "remplir", "--dossier", str(dossier)]) == 0
    chemin = dossier / "candidature" / "valeurs.json"
    valeurs = json.loads(chemin.read_text(encoding="utf-8"))
    valeurs["DC1"]["champs"]["denomination"]["valeur"] = "Entreprise Bis Exemple SARL"
    chemin.write_text(
        json.dumps(valeurs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    assert main(["candidature", "remplir", "--remplacer",
                 "--dossier", str(dossier)]) == 0
    assert "Entreprise Bis Exemple SARL" in texte_docx(dossier / "reponse" / "DC1.docx")
    assert "Entreprise Bis Exemple SARL" not in texte_docx(
        dossier / "reponse" / "DC2.docx")


# ---------------------------------------------------------------------------
# § 4.8 — exporter lit les analyses par lot
# ---------------------------------------------------------------------------

def test_exporter_construit_l_analyse_depuis_les_lots_retenus(
        dossier: Path, capsys):
    ecrire_lots(dossier, lots_alloti(["02", "05"]))
    ecrire_analyse_lot(dossier, "02", date_limite="12 juin 2026 à 17 h 00",
                       en_bref="Lot principal, à répondre avec les moyens internes (fictif).")
    ecrire_analyse_lot(dossier, "05", date_limite=None,
                       en_bref="Lot à confier à un installateur spécialisé (fictif).")
    assert main(["exporter", "--dossier", str(dossier),
                 "--formats", "analyse,feuille"]) == 0
    page_analyse = (dossier / "export" / "analyse.html").read_text(encoding="utf-8")
    page_feuille = (dossier / "export" / "feuille-de-route.html").read_text(encoding="utf-8")
    # une partie par lot retenu
    assert "Électricité courants forts" in page_analyse
    assert "Ventilation mécanique" in page_analyse
    assert "Lot principal, à répondre avec les moyens internes (fictif)." in page_analyse
    assert "Lot à confier à un installateur spécialisé (fictif)." in page_analyse
    # la date limite vient de la rubrique « Identité » du premier lot retenu
    assert "12 juin 2026 à 17 h 00" in page_analyse + page_feuille
    # les pièces de « Pièces à remettre et formes imposées » apparaissent
    assert "DC1, DC2 et le mémoire technique." in page_analyse + page_feuille


def test_exporter_ne_lit_plus_02_analyse(dossier: Path, capsys):
    ecrire_lots(dossier, lots_alloti(["02"]))
    ecrire_analyse_lot(dossier, "02", date_limite="12 juin 2026 à 17 h 00",
                       en_bref="Lot principal (fictif).")
    ancienne = dossier / "02-analyse.md"
    ancienne.write_text(
        "# Analyse du DCE\n\n## Identité de la consultation\n\n| | |\n|---|---|\n"
        "| Acheteur | Ville d'Exemple |\n"
        "| Date limite de remise | 31 décembre 2031 à 09 h 00 |\n",
        encoding="utf-8",
    )
    assert main(["exporter", "--dossier", str(dossier),
                 "--formats", "analyse,feuille"]) == 0
    page_analyse = (dossier / "export" / "analyse.html").read_text(encoding="utf-8")
    page_feuille = (dossier / "export" / "feuille-de-route.html").read_text(encoding="utf-8")
    assert "31 décembre 2031" not in page_analyse
    assert "31 décembre 2031" not in page_feuille
    assert "12 juin 2026 à 17 h 00" in page_analyse + page_feuille


def test_exporter_sans_choix_le_dit_et_sort_proprement(dossier: Path, capsys):
    tri = lots_alloti(["02"])
    tri["choix"] = None  # tri enregistré, lots pas encore choisis
    ecrire_lots(dossier, tri)
    ecrire_analyse_lot(dossier, "02", date_limite="12 juin 2026 à 17 h 00",
                       en_bref="Lot principal (fictif).")
    assert main(["exporter", "--dossier", str(dossier),
                 "--formats", "analyse"]) == 0
    message = "".join(capsys.readouterr())
    assert "chois" in message.casefold()  # le choix des lots lui est demandé


def test_exporter_sans_tri_le_dit_aussi_et_sort_proprement(dossier: Path, capsys):
    # aucun memoire/lots.json
    assert main(["exporter", "--dossier", str(dossier),
                 "--formats", "analyse"]) == 0
    message = "".join(capsys.readouterr())
    assert "chois" in message.casefold()


# ---------------------------------------------------------------------------
# § 4.9 — guide de style
# ---------------------------------------------------------------------------

def test_guide_liste_mentionne_style(capsys):
    assert main(["guide"]) == 0
    assert "style" in capsys.readouterr().out


def test_guide_style_rend_le_contenu_du_fichier(capsys):
    assert main(["guide", "style"]) == 0
    sortie = capsys.readouterr().out
    source = (Path(__file__).resolve().parent.parent
              / "src" / "remporte" / "guides" / "style.md")
    titre = source.read_text(encoding="utf-8").splitlines()[0].lstrip("#").strip()
    assert titre in sortie  # une phrase du fichier ressort dans la sortie
