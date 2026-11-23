"""Tests de remporte.espace : init, arborescence, 01-pieces.md, état."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from conftest import ecrire_pdf, fabriquer_docx, fabriquer_xlsx, fabriquer_zip

from remporte import espace, recherche
from remporte.cli import main
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
                   "AGENTS.md", "CLAUDE.md", "GEMINI.md", "03-go-no-go.md",
                   "04-plan.md", "05-relecture.md", "01-pieces.md",
                   ".remporte/etat.json", ".remporte/index.sqlite"):
        assert (dossier / chemin).exists(), chemin
    assert (dossier / "CLAUDE.md").read_text(encoding="utf-8").strip() == "@AGENTS.md"
    assert (dossier / "GEMINI.md").read_text(encoding="utf-8").strip() == "@./AGENTS.md"
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
    rempli = dossier / "03-go-no-go.md"
    rempli.write_text(
        rempli.read_text(encoding="utf-8").replace("<!-- à remplir -->", "Fait."),
        encoding="utf-8",
    )
    espace.initialiser(source_dce, dossier, forcer=True)
    assert "Fait." in rempli.read_text(encoding="utf-8")
    # un gabarit non rempli est réinitialisé : il contient encore son marqueur
    assert "à remplir" in (dossier / "04-plan.md").read_text(encoding="utf-8")


def test_initialiser_forcer_conserve_une_etape_entamee_avec_marqueur(
        tmp_path: Path, source_dce: Path):
    """`init --forcer` ne réécrit un fichier d'étape que s'il est identique au
    gabarit d'origine : un fichier entamé (paragraphe rédigé) qui garde un
    marqueur n'est pas réinitialisé — sinon la réindexation efface une
    rédaction en cours."""
    dossier = tmp_path / "reponse"
    espace.initialiser(source_dce, dossier)

    plan = dossier / "04-plan.md"
    plan_entame = (
        "# Plan du mémoire\n\n"
        "## Sections\n\n"
        "- [ ] 01 — Moyens\n"
        "- [ ] 02 — Prix\n\n"
        "## À rédiger\n\n"
        "Premier paragraphe rédigé par l'équipe, marqueur gardé pour la suite.\n"
        "<!-- à remplir -->\n"
    )
    plan.write_text(plan_entame, encoding="utf-8")
    decision = dossier / "03-go-no-go.md"
    decision_entame = decision.read_text(encoding="utf-8").replace(
        "## Décision\n\n<!-- à remplir -->",
        "## Décision\n\nGo. Le besoin correspond au métier (fictif).\n"
        "<!-- à remplir -->",
    )
    decision.write_text(decision_entame, encoding="utf-8")
    assert "<!-- à remplir -->" in plan_entame
    assert "<!-- à remplir -->" in decision_entame

    espace.initialiser(source_dce, dossier, forcer=True)

    # l'entame est conservée octet pour octet, marqueur compris
    assert plan.read_text(encoding="utf-8") == plan_entame
    assert decision.read_text(encoding="utf-8") == decision_entame


def test_01_pieces_contenu(tmp_path: Path, source_dce: Path):
    dossier = tmp_path / "reponse"
    espace.initialiser(source_dce, dossier)
    inventaire_md = (dossier / "01-pieces.md").read_text(encoding="utf-8")
    assert "| RC |" in inventaire_md
    assert "PDF probablement scanné" in inventaire_md
    assert "CRT (cahier des réponses) absent" in inventaire_md
    assert "à remplir dans le fichier de l'acheteur" in inventaire_md
    assert "`remporte guide chiffrage`" in inventaire_md or "`remporte guide excel`" in inventaire_md
    assert "remporte.fr" not in inventaire_md and "utm_" not in inventaire_md
    assert espace.MARQUEUR not in inventaire_md  # étape « pieces » sans marqueur


def test_etat_initial(tmp_path: Path, source_dce: Path):
    dossier = tmp_path / "reponse"
    espace.initialiser(source_dce, dossier)
    etat = espace.etat(dossier)
    assert etat["etapes"]["pieces"]["etat"] == "faite"
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


def test_initialiser_forcer_retire_les_pieces_disparues(tmp_path: Path):
    """Réinitialiser avec une nouvelle source retire les pièces de l'ancien
    DCE devenues absentes, les annonce, et garde les pièces déposées à la main."""
    source_1 = tmp_path / "DCE-ancien"
    source_1.mkdir()
    fabriquer_docx(source_1 / "1-RC.docx")
    (source_1 / "annexe-ancienne.txt").write_text(
        "Contraintes de normes ZXQWJ propres à l'ancien dossier.", encoding="utf-8"
    )
    dossier = tmp_path / "reponse"
    espace.initialiser(source_1, dossier)

    # une pièce déposée à la main dans dce/, jamais importée par init
    manuelle = dossier / "dce" / "note-manuelle.txt"
    manuelle.write_text("Précision ajoutée à la main pour l'offre.", encoding="utf-8")

    source_2 = tmp_path / "DCE-nouveau"
    source_2.mkdir()
    fabriquer_docx(source_2 / "1-RC.docx")
    donnees = espace.initialiser(source_2, dossier, forcer=True)

    # la pièce importée de l'ancienne source, absente de la nouvelle, est retirée
    assert not (dossier / "dce" / "annexe-ancienne.txt").exists()
    # … et son retrait est annoncé dans le retour de la commande
    assert donnees.get("retirees") == ["annexe-ancienne.txt"]
    # la pièce déposée à la main reste en place
    assert manuelle.exists()
    # le texte converti de la pièce retirée disparaît du cache comme de l'index :
    # la recherche ne la cite plus
    assert not (dossier / ".remporte" / "texte" / "annexe-ancienne.txt.md").exists()
    assert (dossier / ".remporte" / "texte" / "1-RC.docx.md").exists()
    assert "annexe-ancienne.txt" not in (dossier / "01-pieces.md").read_text(encoding="utf-8")
    assert recherche.chercher_dce(dossier, "zxqwj") == []


def test_initialiser_ecarte_les_parasites_de_l_inventaire(tmp_path: Path):
    """Les parasites d'un zip ne sont ni extraits dans dce/ ni comptés comme pièces."""
    zip_dce = fabriquer_zip(
        tmp_path / "DCE.zip",
        {
            "RC.txt": "Règlement de la consultation",
            "~$CCTP.docx": "verrou office",
            "~$DPGF.xlsx": "verrou office",
            "Thumbs.db": "vignettes windows",
            "desktop.ini": "[.ShellClassInfo]",
            "sous/._CCTP.pdf": "%PDF-faux",
            ".DS_Store": "bud1",
            "__MACOSX/._RC.txt": "appledouble",
        },
    )
    dossier = tmp_path / "reponse"
    donnees = espace.initialiser(zip_dce, dossier)
    assert {p["chemin"] for p in donnees["pieces"]} == {"RC.txt"}
    inventaire_md = (dossier / "01-pieces.md").read_text(encoding="utf-8")
    for parasite in ("~$CCTP.docx", "~$DPGF.xlsx", "Thumbs.db", "desktop.ini", "._CCTP.pdf"):
        assert parasite not in inventaire_md, parasite
    sur_disque = {p.relative_to(dossier / "dce").as_posix()
                  for p in (dossier / "dce").rglob("*") if p.is_file()}
    assert sur_disque == {"RC.txt"}


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


def test_initialiser_extrait_les_noms_accentues_d_un_zip(tmp_path: Path):
    """init sur un zip dont les noms sont en UTF-8 non déclaré : le fichier
    extrait porte son vrai nom accentué, dans dce/ comme dans l'inventaire."""
    import zipfile as _zipfile

    vrai = "DCE Tvx généraux/RC.txt".encode("utf-8")
    substitut = bytes(b if b < 0x80 else ord("x") for b in vrai)
    archive = tmp_path / "dce.zip"
    with _zipfile.ZipFile(archive, "w") as zf:
        zf.writestr(substitut.decode("ascii"), "Règlement de la consultation")
    archive.write_bytes(archive.read_bytes().replace(substitut, vrai))

    dossier = tmp_path / "reponse"
    donnees = espace.initialiser(archive, dossier)
    assert (dossier / "dce" / "DCE Tvx généraux" / "RC.txt").exists()
    chemins = {p["chemin"] for p in donnees["pieces"]}
    assert chemins == {"DCE Tvx généraux/RC.txt"}
    assert "DCE Tvx généraux/RC.txt" in (dossier / "01-pieces.md").read_text(encoding="utf-8")


def test_initialiser_forcer_ne_retire_rien_d_un_dossier_sans_provenance(tmp_path: Path):
    """Un dossier dont l'état ne distingue pas les pièces importées des pièces
    ajoutées à la main garde toutes ses pièces à la réinitialisation."""
    source_1 = tmp_path / "DCE-ancien"
    source_1.mkdir()
    fabriquer_docx(source_1 / "1-RC.docx")
    dossier = tmp_path / "reponse"
    espace.initialiser(source_1, dossier)
    manuelle = dossier / "dce" / "note-manuelle.txt"
    manuelle.write_text("Précision ajoutée à la main pour l'offre.", encoding="utf-8")
    chemin_etat = dossier / ".remporte" / "etat.json"
    etat = json.loads(chemin_etat.read_text(encoding="utf-8"))
    del etat["importees"]
    etat["pieces"].append({"chemin": "note-manuelle.txt"})
    chemin_etat.write_text(json.dumps(etat), encoding="utf-8")

    source_2 = tmp_path / "DCE-nouveau"
    source_2.mkdir()
    fabriquer_docx(source_2 / "2-CCTP.docx")
    donnees = espace.initialiser(source_2, dossier, forcer=True)

    assert manuelle.exists()
    assert (dossier / "dce" / "1-RC.docx").exists()
    assert donnees["retirees"] == []
    assert sorted(donnees["importees"]) == ["2-CCTP.docx"]


# ---------------------------------------------------------------------------
# Colonne « Lot » de l'inventaire : une seule source, le tri enregistré
# ---------------------------------------------------------------------------

def _tri_dce_exemple() -> dict:
    """Tri du DCE d'essai (source_dce) : RC et notes dans le lot 02, BPU
    commun, CCTP scanné illisible. Le choix reste vide."""
    return {
        "schema_version": 1,
        "allotissement": "lots",
        "lots": [
            {"id": "02", "intitule": "Génie électrique et courants forts",
             "pieces": ["dce/1-RC.docx", "dce/notes.txt"], "parties_communes": [],
             "recommandation": {"avis": "repondre",
                                "raison": "Dans le métier de l'entreprise (fictif)."}},
        ],
        "pieces_communes": ["dce/2-BPU.xlsx"],
        "pieces_illisibles": ["dce/3-CCTP-scan.pdf"],
        "types_pieces": {"dce/1-RC.docx": "RC", "dce/2-BPU.xlsx": "BPU",
                         "dce/notes.txt": "autre"},
        "choix": None,
    }


def _enregistrer_tri(dossier: Path) -> None:
    chemin_tri = dossier / "memoire" / "lots.json"
    chemin_tri.parent.mkdir(parents=True, exist_ok=True)
    chemin_tri.write_text(
        json.dumps(_tri_dce_exemple(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    assert main(["lots", "enregistrer", "--dossier", str(dossier)]) == 0


def test_pieces_affiche_le_lot_du_tri_enregistre(
        tmp_path: Path, source_dce: Path, capsys):
    """Après `lots enregistrer`, `remporte pieces` montre la même répartition
    que 01-pieces.md : id du lot, « commun », ou un tiret."""
    dossier = tmp_path / "reponse"
    espace.initialiser(source_dce, dossier)
    _enregistrer_tri(dossier)

    assert main(["pieces", "--dossier", str(dossier)]) == 0
    sortie = capsys.readouterr().out
    colonnes = {}
    for ligne in sortie.splitlines():
        cellules = [c.strip() for c in re.split(r"  +", ligne) if c.strip()]
        if len(cellules) < 6:  # hors tableau : notes sous l'inventaire
            continue
        colonnes[cellules[-1]] = cellules[1]
    assert colonnes["dce/1-RC.docx"] == "02"
    assert colonnes["dce/notes.txt"] == "02"
    assert colonnes["dce/2-BPU.xlsx"] == "commun"
    assert colonnes["dce/3-CCTP-scan.pdf"] == "—"


def test_init_forcer_conserve_la_colonne_lot_d_un_tri_enregistre(
        tmp_path: Path, source_dce: Path, capsys):
    dossier = tmp_path / "reponse"
    espace.initialiser(source_dce, dossier)
    _enregistrer_tri(dossier)
    assert "| 02 | `dce/1-RC.docx`" in \
        (dossier / "01-pieces.md").read_text(encoding="utf-8")

    assert main(["init", str(source_dce), "--dossier", str(dossier),
                 "--forcer"]) == 0
    capsys.readouterr()
    inventaire = (dossier / "01-pieces.md").read_text(encoding="utf-8")
    assert "| 02 | `dce/1-RC.docx`" in inventaire
    assert "| commun | `dce/2-BPU.xlsx`" in inventaire


def test_init_forcer_efface_la_colonne_lot_si_le_tri_n_est_plus_valide(
        tmp_path: Path, source_dce: Path, capsys):
    dossier = tmp_path / "reponse"
    espace.initialiser(source_dce, dossier)
    _enregistrer_tri(dossier)

    # sans le relevé du choix, le tri n'est plus enregistré : rien ne prouve
    # que la répartition a été validée pour cet inventaire
    (dossier / ".remporte" / "lots.json").unlink()
    assert main(["init", str(source_dce), "--dossier", str(dossier),
                 "--forcer"]) == 0
    capsys.readouterr()
    inventaire = (dossier / "01-pieces.md").read_text(encoding="utf-8")
    assert "| — | `dce/1-RC.docx`" in inventaire
    assert "| 02 |" not in inventaire

    assert main(["etat", "--dossier", str(dossier)]) == 0
    sortie = capsys.readouterr().out
    assert "répartition" in sortie, sortie
