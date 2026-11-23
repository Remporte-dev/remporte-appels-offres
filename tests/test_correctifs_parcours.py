"""Tests des correctifs du parcours par lot, après relecture adverse.

Chaque test reproduit le scénario du rapport de relecture qu'il doit empêcher
de revenir : le guide et le code restent d'accord (exemples JSON du guide
joués tels quels), les écritures survivent aux volumes sans liens physiques et
aux fichiers verrouillés, les droits restent ceux du système, les messages
restent en français de dossier. Les simulations (liens physiques indisponibles,
fichier verrouillé, chemin trop long) remplacent une fonction du système et le
disent en commentaire ; rien d'autre n'est substitué.

Un refus vérifie toujours le code de sortie non nul ET des fichiers inchangés
(empreinte de chaque fichier du dossier, avant/après).
"""

from __future__ import annotations

import errno
import hashlib
import json
import os
import re
import stat
import textwrap
import unicodedata
from pathlib import Path

import pytest
from conftest import ecrire_pdf

from remporte.cli import main

RUBRIQUES_LOT = ["En bref", "Identité", "Ce que l'acheteur attend vraiment",
                 "Critères et pondérations", "Pièces à remettre et formes imposées",
                 "Incohérences entre pièces", "Pièces illisibles ou absentes",
                 "Documents de référence et versions", "Avis"]


# ---------------------------------------------------------------------------
# Aides : DCE de test, dossier de réponse, tri, candidature
# ---------------------------------------------------------------------------

def _dce_guide(source: Path) -> Path:
    """Les trois pièces exactes que cite l'exemple du guide d'analyse :
    RC.pdf, CCAP.pdf et LOT 02/CCTP lot 02.pdf, toutes lisibles."""
    (source / "LOT 02").mkdir(parents=True)
    ecrire_pdf(source / "RC.pdf", [
        "Reglement de la consultation du marche\n"
        "Le marche est alloti en un lot : numero 02.",
    ])
    ecrire_pdf(source / "CCAP.pdf", [
        "Cahier des clauses administratives particulieres\n"
        "Les penalites de retard suivent le reglement.",
    ])
    ecrire_pdf(source / "LOT 02/CCTP lot 02.pdf", [
        "Cahier des clauses techniques particulieres du lot 02\n"
        "Eclairage, courants forts, armoires electriques.",
    ])
    return source


def _dce_simple(source: Path) -> Path:
    """DCE de test : une pièce commune lisible, une pièce de lot lisible,
    une pièce scannée (inventoriée « vide », donc illisible pour le tri)."""
    (source / "LOT 02").mkdir(parents=True)
    ecrire_pdf(source / "RC.pdf", [
        "Reglement de la consultation du marche\n"
        "Acheteur : Ville d'Exemple. Remise des offres le 12 juin 2026.",
    ])
    ecrire_pdf(source / "LOT 02/CCTP lot 02.pdf", [
        "Cahier des clauses techniques particulieres du lot 02\n"
        "Eclairage, courants forts, armoires electriques.",
    ])
    ecrire_pdf(source / "notice scannee.pdf", ["", ""])
    return source


def _initialiser(source: Path, tmp_path: Path, capsys) -> Path:
    dossier = tmp_path / "reponse"
    assert main(["init", str(source), "--dossier", str(dossier)]) == 0
    capsys.readouterr()
    return dossier


def _tri_simple() -> dict:
    """Tri valide sur le DCE simple : lot 02, RC commune, notice illisible."""
    return {
        "schema_version": 1,
        "allotissement": "lots",
        "lots": [
            {"id": "02", "intitule": "Électricité courants forts",
             "pieces": ["dce/LOT 02/CCTP lot 02.pdf"], "parties_communes": [],
             "recommandation": {"avis": "repondre",
                                "raison": "Cœur du métier de l'entreprise."}},
        ],
        "pieces_communes": ["dce/RC.pdf"],
        "pieces_illisibles": ["dce/notice scannee.pdf"],
        "types_pieces": {"dce/RC.pdf": "RC",
                         "dce/LOT 02/CCTP lot 02.pdf": "CCTP"},
        "choix": None,
    }


def _ecrire_tri(dossier: Path, tri: dict) -> Path:
    chemin = dossier / "memoire" / "lots.json"
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text(json.dumps(tri, ensure_ascii=False), encoding="utf-8")
    return chemin


def _enregistrer(dossier: Path, capsys, tri: dict | None = None) -> None:
    if tri is not None:
        _ecrire_tri(dossier, tri)
    assert main(["lots", "enregistrer", "--dossier", str(dossier)]) == 0
    capsys.readouterr()


def _choisir(dossier: Path, capsys, ids: str = "02",
             par: str = "Camille Exemple") -> None:
    assert main(["lots", "choisir", "--lots", ids, "--par", par,
                 "--dossier", str(dossier)]) == 0
    capsys.readouterr()


def _candidature_prete(dossier: Path, capsys) -> None:
    assert main(["candidature", "preparer", "--dossier", str(dossier)]) == 0
    capsys.readouterr()
    chemin = dossier / "candidature" / "valeurs.json"
    valeurs = json.loads(chemin.read_text(encoding="utf-8"))
    valeurs["DC1"]["champs"]["denomination"]["valeur"] = "Entreprise Exemple SAS"
    chemin.write_text(
        json.dumps(valeurs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def _analyse_remplie(dossier: Path, lot: str = "02") -> None:
    """Les neuf rubriques de l'analyse du lot, rédigées, marqueur en moins."""
    corps = {
        "En bref": "Lot principal, à répondre avec les moyens internes (fictif).",
        "Identité": "- Acheteur : Ville d'Exemple\n- Objet : "
                    "Réhabilitation des installations (fictif)",
        "Ce que l'acheteur attend vraiment":
            "Une équipe présente sur site pendant les travaux (fictif).",
        "Critères et pondérations":
            "| Critère | Pondération |\n|---|---|\n| Technique | 60 % |",
        "Pièces à remettre et formes imposées":
            "- DC1, DC2 et le mémoire technique.",
        "Incohérences entre pièces":
            "I-1 : le CCTP demande quarante prises au R+1, le bordereau en "
            "compte trente-deux.",
        "Pièces illisibles ou absentes": "Aucune.",
        "Documents de référence et versions":
            "Reglement version du 2 mars (fictif).",
        "Avis": "Répondre (fictif).",
    }
    lignes = [f"# Analyse du lot {lot}", ""]
    for rubrique in RUBRIQUES_LOT:
        lignes += [f"## {rubrique}", "", corps[rubrique], ""]
    (dossier / "analyse" / f"lot-{lot}.md").write_text(
        "\n".join(lignes), encoding="utf-8")


def _empreintes(dossier: Path) -> dict[str, str]:
    """Empreinte de chaque fichier du dossier : un refus ne doit rien
    modifier, ni rien ajouter (relevé, analyses, temporaire oublié)."""
    empreintes: dict[str, str] = {}
    for chemin in sorted(dossier.rglob("*")):
        if chemin.is_file():
            empreintes[chemin.relative_to(dossier).as_posix()] = \
                hashlib.sha256(chemin.read_bytes()).hexdigest()
    return empreintes


def _blocs_json_du_guide() -> list[str]:
    """Les deux exemples ```json du guide d'analyse, extraits du fichier du
    dépôt (pas de copie locale : si le guide change, le test le voit)."""
    source = (Path(__file__).resolve().parent.parent
              / "src" / "remporte" / "guides" / "analyse.md")
    blocs = re.findall(r"```json\n(.*?)```", source.read_text(encoding="utf-8"), re.S)
    assert len(blocs) >= 2, "le guide d'analyse doit porter deux exemples JSON"
    return [textwrap.dedent(bloc) for bloc in blocs[:2]]


def _mode(chemin: Path) -> int:
    return stat.S_IMODE(chemin.stat().st_mode)


# ---------------------------------------------------------------------------
# B1 — le tri écrit comme le guide le demande passe tels quels
# ---------------------------------------------------------------------------

def test_le_tri_ecrit_comme_le_guide_le_demande_est_accepte(tmp_path, capsys):
    bloc_tri = _blocs_json_du_guide()[0]
    tri = json.loads(bloc_tri)  # sanité : c'est bien un tri
    assert tri["schema_version"] == 1
    source = _dce_guide(tmp_path / "DCE")
    dossier = _initialiser(source, tmp_path, capsys)

    # l'agent recopie l'exemple du guide sans y toucher
    chemin_tri = dossier / "memoire" / "lots.json"
    chemin_tri.parent.mkdir(parents=True, exist_ok=True)
    chemin_tri.write_text(bloc_tri, encoding="utf-8")

    assert main(["lots", "enregistrer", "--dossier", str(dossier)]) == 0
    capsys.readouterr()

    assert main(["lots", "enregistrer", "--dossier", str(dossier),
                 "--json"]) == 0
    sortie = json.loads(capsys.readouterr().out)
    assert sortie["ok"] is True
    assert sortie["lots"] == ["02"]
    assert sortie["pieces_communes"] == 2
    assert sortie["choix"] is None


# ---------------------------------------------------------------------------
# B2 — la question à l'acheteur écrite comme le guide le demande est conforme
# ---------------------------------------------------------------------------

def test_la_question_ecrite_comme_le_guide_le_demande_passe_dans_le_rapport(
        tmp_path, capsys):
    bloc_tri, bloc_questions = _blocs_json_du_guide()
    assert "questions_acheteur" in bloc_questions  # sanité : c'est le JSON d'analyse
    source = _dce_guide(tmp_path / "DCE")
    dossier = _initialiser(source, tmp_path, capsys)
    (dossier / "memoire" / "lots.json").parent.mkdir(parents=True, exist_ok=True)
    (dossier / "memoire" / "lots.json").write_text(bloc_tri, encoding="utf-8")
    _enregistrer(dossier, capsys)
    _choisir(dossier, capsys)

    _analyse_remplie(dossier)  # neuf rubriques, incohérence I-1 décrite
    (dossier / "analyse" / "lot-02.json").write_text(bloc_questions, encoding="utf-8")

    assert main(["lots", "rapport", "--dossier", str(dossier), "--json"]) == 0
    sortie = json.loads(capsys.readouterr().out)
    assert sortie["ok"] is True
    assert sortie.get("problemes", {}).get("02") is None, sortie["problemes"]

    page = (dossier / "memoire" / "rapport-lots.html").read_text(encoding="utf-8")
    question = json.loads(bloc_questions)["questions_acheteur"][0]
    assert question["contexte"] in page
    assert question["question"] in page
    assert page.index(question["contexte"]) < page.index(question["question"])


# ---------------------------------------------------------------------------
# B3 — aucun lien physique requis : volume qui refuse os.link
# ---------------------------------------------------------------------------

def _sans_liens_physiques(monkeypatch) -> None:
    """Simulation d'un volume sans liens physiques (clé exFAT, partage SMB) :
    os.link et Path.hardlink_to répondent ENOTSUP."""
    def refuser(*args, **kwargs):
        raise OSError(errno.ENOTSUP, "Opération non prise en charge")
    monkeypatch.setattr(os, "link", refuser)
    monkeypatch.setattr(Path, "hardlink_to", refuser)


def test_le_choix_des_lots_reussit_sans_liens_physiques(tmp_path, monkeypatch, capsys):
    source = _dce_simple(tmp_path / "DCE")
    dossier = _initialiser(source, tmp_path, capsys)
    _enregistrer(dossier, capsys, _tri_simple())
    _sans_liens_physiques(monkeypatch)

    assert main(["lots", "choisir", "--lots", "02", "--par", "Camille",
                 "--dossier", str(dossier)]) == 0
    capsys.readouterr()

    assert (dossier / "analyse" / "lot-02.md").is_file()
    assert (dossier / "analyse" / "lot-02.json").is_file()
    tri = json.loads((dossier / "memoire" / "lots.json").read_text("utf-8"))
    assert tri["choix"]["retenus"] == ["02"]


def test_les_formulaires_se_crent_sans_liens_physiques_et_le_second_appel_refuse(
        tmp_path, monkeypatch, capsys):
    source = _dce_simple(tmp_path / "DCE")
    dossier = _initialiser(source, tmp_path, capsys)
    _enregistrer(dossier, capsys, _tri_simple())
    _choisir(dossier, capsys)
    _candidature_prete(dossier, capsys)
    _sans_liens_physiques(monkeypatch)

    assert main(["candidature", "remplir", "--dossier", str(dossier)]) == 0
    capsys.readouterr()
    remise = dossier / "reponse" / "Lot 02 - Électricité courants forts"
    assert (remise / "DC1.docx").is_file()
    assert (remise / "DC2.docx").is_file()

    empreintes = _empreintes(remise)
    assert main(["candidature", "remplir", "--dossier", str(dossier)]) != 0
    message = "".join(capsys.readouterr())
    assert "DC1.docx existe déjà" in message
    assert _empreintes(remise) == empreintes  # aucun formulaire retouché


# ---------------------------------------------------------------------------
# I1 — un fichier verrouillé refuse la commande sans rien modifier
# ---------------------------------------------------------------------------

def _verrouiller(monkeypatch, nom: str):
    """Simulation d'un fichier ouvert dans Word ou Excel : Path.replace lève
    PermissionError quand la cible porte ce nom, sinon laisse passer."""
    original = Path.replace

    def remplacer(self, cible):
        if Path(cible).name == nom:
            raise PermissionError(errno.EACCES, "Permission denied", str(cible))
        return original(self, cible)

    monkeypatch.setattr(Path, "replace", remplacer)


def test_un_formulaire_verrouille_refuse_sans_rien_modifier_puis_se_debloque(
        tmp_path, monkeypatch, capsys):
    source = _dce_simple(tmp_path / "DCE")
    dossier = _initialiser(source, tmp_path, capsys)
    _enregistrer(dossier, capsys, _tri_simple())
    _choisir(dossier, capsys)
    _candidature_prete(dossier, capsys)
    assert main(["candidature", "remplir", "--dossier", str(dossier)]) == 0
    capsys.readouterr()
    remise = dossier / "reponse" / "Lot 02 - Électricité courants forts"
    empreintes = _empreintes(dossier)

    _verrouiller(monkeypatch, "DC2.docx")  # DC2.docx ouvert dans Word
    assert main(["candidature", "remplir", "--remplacer",
                 "--dossier", str(dossier)]) != 0
    message = "".join(capsys.readouterr())
    assert "Fermez DC2.docx puis relancez" in message
    assert _empreintes(dossier) == empreintes  # DC1 repris, DC2 intact

    monkeypatch.undo()
    assert main(["candidature", "remplir", "--remplacer",
                 "--dossier", str(dossier)]) == 0
    capsys.readouterr()


def test_un_inventaire_verrouille_refuse_sans_rien_modifier(tmp_path, monkeypatch, capsys):
    source = _dce_simple(tmp_path / "DCE")
    dossier = _initialiser(source, tmp_path, capsys)
    _enregistrer(dossier, capsys, _tri_simple())
    _choisir(dossier, capsys)
    empreintes = _empreintes(dossier)

    _verrouiller(monkeypatch, "01-pieces.md")
    assert main(["lots", "enregistrer", "--dossier", str(dossier)]) != 0
    message = "".join(capsys.readouterr())
    assert "Fermez 01-pieces.md puis relancez" in message
    assert _empreintes(dossier) == empreintes  # tri, relevé et inventaire intacts


def test_un_tri_verrouille_refuse_sans_creer_d_analyse_puis_se_debloque(
        tmp_path, monkeypatch, capsys):
    source = _dce_simple(tmp_path / "DCE")
    dossier = _initialiser(source, tmp_path, capsys)
    _enregistrer(dossier, capsys, _tri_simple())
    empreintes = _empreintes(dossier)

    _verrouiller(monkeypatch, "lots.json")  # memoire/lots.json indisponible
    assert main(["lots", "choisir", "--lots", "02", "--par", "Camille",
                 "--dossier", str(dossier)]) != 0
    message = "".join(capsys.readouterr())
    assert "Fermez lots.json puis relancez" in message
    apres = _empreintes(dossier)
    assert apres == empreintes  # ni analyse créée, ni tri, ni relevé modifiés
    assert "analyse/lot-02.md" not in apres
    assert "analyse/lot-02.json" not in apres

    monkeypatch.undo()
    assert main(["lots", "choisir", "--lots", "02", "--par", "Camille",
                 "--dossier", str(dossier)]) == 0
    capsys.readouterr()
    assert (dossier / "analyse" / "lot-02.md").is_file()


# ---------------------------------------------------------------------------
# I8 — marques d'ordre d'octets et encodages
# ---------------------------------------------------------------------------

def test_le_tri_avec_marque_d_ordre_d_octets_utf8_est_accepte(tmp_path, capsys):
    source = _dce_simple(tmp_path / "DCE")
    dossier = _initialiser(source, tmp_path, capsys)
    chemin_tri = dossier / "memoire" / "lots.json"
    chemin_tri.parent.mkdir(parents=True, exist_ok=True)
    chemin_tri.write_bytes(
        json.dumps(_tri_simple(), ensure_ascii=False).encode("utf-8-sig"))

    assert main(["lots", "enregistrer", "--dossier", str(dossier)]) == 0
    capsys.readouterr()


def test_le_tri_en_utf16_est_refuse_avec_le_conseil_utf8(tmp_path, capsys):
    source = _dce_simple(tmp_path / "DCE")
    dossier = _initialiser(source, tmp_path, capsys)
    chemin_tri = dossier / "memoire" / "lots.json"
    chemin_tri.parent.mkdir(parents=True, exist_ok=True)
    chemin_tri.write_bytes(json.dumps(_tri_simple()).encode("utf-16"))
    empreintes = _empreintes(dossier)

    assert main(["lots", "enregistrer", "--dossier", str(dossier)]) != 0
    message = "".join(capsys.readouterr())
    assert "Enregistrez lots.json en UTF-8" in message
    assert _empreintes(dossier) == empreintes


def test_le_json_d_analyse_avec_marque_d_ordre_d_octets_est_accepte(tmp_path, capsys):
    source = _dce_simple(tmp_path / "DCE")
    dossier = _initialiser(source, tmp_path, capsys)
    _enregistrer(dossier, capsys, _tri_simple())
    _choisir(dossier, capsys)
    _analyse_remplie(dossier)
    chemin_questions = dossier / "analyse" / "lot-02.json"
    chemin_questions.write_bytes(
        json.dumps({"questions_acheteur": []}, ensure_ascii=False).encode("utf-8-sig"))

    assert main(["lots", "rapport", "--dossier", str(dossier), "--json"]) == 0
    sortie = json.loads(capsys.readouterr().out)
    assert sortie.get("problemes", {}).get("02") is None, sortie["problemes"]


# ---------------------------------------------------------------------------
# M1 — options obligatoires refusées par la commande, en français
# ---------------------------------------------------------------------------

CAS_OPTIONS_MANQUANTES = [
    ("sans_lots_ni_par", ["lots", "choisir"], ["lots"]),
    ("sans_par", ["lots", "choisir", "--lots", "02"], ["nom"]),
]


@pytest.mark.parametrize("nom,commande,fragments", CAS_OPTIONS_MANQUANTES,
                         ids=[c[0] for c in CAS_OPTIONS_MANQUANTES])
def test_les_options_obligatoires_manquantes_sont_refusees_en_francais(
        tmp_path, capsys, nom, commande, fragments):
    source = _dce_simple(tmp_path / "DCE")
    dossier = _initialiser(source, tmp_path, capsys)
    _enregistrer(dossier, capsys, _tri_simple())

    complet = [*commande, "--dossier", str(dossier), "--json"]
    try:
        code = main(complet)
    except SystemExit as sortie:
        # argparse quitte avant d'atteindre la commande : le refus doit venir
        # de la commande elle-même, jamais d'un message d'usage en anglais.
        code = sortie.code
        assert code == 1, (nom, "argparse a refusé avec son propre message")
    assert code == 1
    brut = capsys.readouterr()
    message = brut.out + brut.err
    assert "the following arguments are required" not in message
    donnees = json.loads(brut.out)
    assert donnees["ok"] is False
    for fragment in fragments:
        assert fragment in donnees["erreur"], (nom, donnees["erreur"])


# ---------------------------------------------------------------------------
# M3 — deux identifiants qui ne diffèrent que par la casse ou les accents
# ---------------------------------------------------------------------------

def test_deux_lots_dont_les_ids_ne_differrent_que_par_la_casse_sont_un_doublon(
        tmp_path, capsys):
    source = _dce_simple(tmp_path / "DCE")
    dossier = _initialiser(source, tmp_path, capsys)
    tri = _tri_simple()
    tri["lots"].append(dict(tri["lots"][0], id="2A"))
    tri["lots"][0]["id"] = "2a"
    _ecrire_tri(dossier, tri)
    empreintes = _empreintes(dossier)

    assert main(["lots", "enregistrer", "--dossier", str(dossier)]) != 0
    message = "".join(capsys.readouterr())
    assert "deux fois" in message
    assert _empreintes(dossier) == empreintes


def test_deux_lots_dont_les_ids_ne_differrent_que_par_les_accents_sont_un_doublon(
        tmp_path, capsys):
    """Deux identifiants égaux en NFC (l'un composé, l'autre décomposé) sont
    le même lot : le tri est refusé et rien n'est enregistré. Aujourd'hui le
    filtre d'identifiant refuse déjà la forme décomposée (« invalide ») ; si
    le filtre s'élargit, le refus doit venir de l'unicité en NFC (« deux
    fois ») : les deux messages remplissent la règle, aucun tri ne passe."""
    source = _dce_simple(tmp_path / "DCE")
    dossier = _initialiser(source, tmp_path, capsys)
    tri = _tri_simple()
    tri["lots"][0]["id"] = "câble"                    # forme composée (NFC)
    tri["lots"].append(
        dict(tri["lots"][0],
             id=unicodedata.normalize("NFD", "câble")))  # même id, NFD
    _ecrire_tri(dossier, tri)
    empreintes = _empreintes(dossier)

    assert main(["lots", "enregistrer", "--dossier", str(dossier)]) != 0
    message = "".join(capsys.readouterr())
    assert "deux fois" in message or "invalide" in message.lower(), message
    assert _empreintes(dossier) == empreintes


# ---------------------------------------------------------------------------
# M6 — aucun message ne montre une valeur non textuelle
# ---------------------------------------------------------------------------

def test_une_piece_de_mauvais_type_est_refusee_sans_valeur_python(tmp_path, capsys):
    source = _dce_simple(tmp_path / "DCE")
    dossier = _initialiser(source, tmp_path, capsys)
    tri = _tri_simple()
    tri["lots"][0]["pieces"] = [None]
    _ecrire_tri(dossier, tri)
    empreintes = _empreintes(dossier)

    assert main(["lots", "enregistrer", "--dossier", str(dossier)]) != 0
    message = "".join(capsys.readouterr())
    assert "None" not in message, message
    assert "un texte" in message
    assert _empreintes(dossier) == empreintes


def test_un_type_de_piece_de_mauvais_type_est_refuse_sans_valeur_python(
        tmp_path, capsys):
    source = _dce_simple(tmp_path / "DCE")
    dossier = _initialiser(source, tmp_path, capsys)
    tri = _tri_simple()
    tri["types_pieces"]["dce/RC.pdf"] = {"a": 1}
    _ecrire_tri(dossier, tri)
    empreintes = _empreintes(dossier)

    assert main(["lots", "enregistrer", "--dossier", str(dossier)]) != 0
    message = "".join(capsys.readouterr())
    assert "{" not in message, message
    assert "un texte" in message
    assert _empreintes(dossier) == empreintes


# ---------------------------------------------------------------------------
# M7 — page du rapport : date en clair, accord au singulier
# ---------------------------------------------------------------------------

def test_la_page_du_rapport_donne_la_date_en_clair_et_l_accord_au_singulier(
        tmp_path, capsys):
    source = _dce_simple(tmp_path / "DCE")
    dossier = _initialiser(source, tmp_path, capsys)
    _enregistrer(dossier, capsys, _tri_simple())
    _choisir(dossier, capsys, ids="02", par="Camille Exemple")

    assert main(["lots", "rapport", "--dossier", str(dossier)]) == 0
    capsys.readouterr()
    page = (dossier / "memoire" / "rapport-lots.html").read_text(encoding="utf-8")
    assert "Lot 02 choisi par Camille Exemple" in page
    assert "choisis par" not in page
    assert re.search(r"\d{2}/\d{2}/\d{4}", page), page  # date en clair
    assert not re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:", page), page  # pas d'ISO brute


# ---------------------------------------------------------------------------
# I6 — droits des fichiers écrits (POSIX)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(os.name == "nt", reason="droits POSIX")
def test_les_fichiers_ecrits_ont_les_droits_usuels(tmp_path, capsys):
    source = _dce_simple(tmp_path / "DCE")
    dossier = _initialiser(source, tmp_path, capsys)

    ancien_masque = os.umask(0o022)
    try:
        _ecrire_tri(dossier, _tri_simple())
        (dossier / "memoire" / "lots.json").chmod(0o640)
        (dossier / "01-pieces.md").chmod(0o640)

        _enregistrer(dossier, capsys)
        # un fichier remplacé garde ses droits, un fichier créé a les droits par défaut
        assert _mode(dossier / "memoire" / "lots.json") == 0o640
        assert _mode(dossier / "01-pieces.md") == 0o640
        assert _mode(dossier / ".remporte" / "lots.json") == 0o644

        _choisir(dossier, capsys)
        assert _mode(dossier / "memoire" / "lots.json") == 0o640
        assert _mode(dossier / "analyse" / "lot-02.md") == 0o644
        assert _mode(dossier / "analyse" / "lot-02.json") == 0o644

        _candidature_prete(dossier, capsys)
        assert main(["candidature", "remplir", "--dossier", str(dossier)]) == 0
        capsys.readouterr()
        remise = dossier / "reponse" / "Lot 02 - Électricité courants forts"
        assert _mode(remise / "DC1.docx") == 0o644
        assert _mode(remise / "DC2.docx") == 0o644

        (remise / "DC1.docx").chmod(0o640)
        assert main(["candidature", "remplir", "--remplacer",
                     "--dossier", str(dossier)]) == 0
        capsys.readouterr()
        assert _mode(remise / "DC1.docx") == 0o640  # droits du fichier remplacé
        assert _mode(remise / "DC2.docx") == 0o644

        _analyse_remplie(dossier)
        assert main(["lots", "rapport", "--dossier", str(dossier)]) == 0
        capsys.readouterr()
        assert _mode(dossier / "memoire" / "rapport-lots.html") == 0o644
        assert _mode(dossier / "memoire" / "lots-analyses.json") == 0o644

        assert main(["exporter", "--formats", "analyse",
                     "--dossier", str(dossier)]) == 0
        capsys.readouterr()
        assert _mode(dossier / "export" / "analyse.html") == 0o644
    finally:
        os.umask(ancien_masque)


# ---------------------------------------------------------------------------
# I7 — intitulé de lot long : coupé dans le nom du dossier, diagnostic gardé
# ---------------------------------------------------------------------------

INTITULE_LONG = ("Réfection complète des réseaux électriques courants forts "
                 "et courants faibles des bâtiments techniques du site")


def _nom_de_lot(id_: str, intitule: str) -> str:
    """Le nom attendu : intitulé coupé à 60 caractères au dernier espace
    avant la limite, caractères interdits remplacés, bords nettoyés."""
    coupe = intitule[:60]
    if " " in coupe:
        coupe = coupe[:coupe.rindex(" ")]
    coupe = re.sub(r'[<>:"/\\|?*\x00-\x1f\x7f-\x9f]', "-", coupe).strip(" .")
    return f"Lot {id_} - " + (coupe or "-")


def test_un_intitule_de_lot_long_est_coupe_dans_le_nom_du_dossier(tmp_path, capsys):
    source = _dce_simple(tmp_path / "DCE")
    dossier = _initialiser(source, tmp_path, capsys)
    tri = _tri_simple()
    tri["lots"][0]["intitule"] = INTITULE_LONG
    _enregistrer(dossier, capsys, tri)
    _choisir(dossier, capsys)

    assert main(["livraison", "dossier", "--dossier", str(dossier)]) == 0
    capsys.readouterr()
    attendu = _nom_de_lot("02", INTITULE_LONG)
    dossiers = [p.name for p in (dossier / "reponse").iterdir() if p.is_dir()]
    assert dossiers == [attendu], dossiers


def test_un_chemin_trop_long_garde_son_diagnostic(tmp_path, monkeypatch, capsys):
    """Simulation d'un chemin trop long pour le système : le dossier de
    remise ne peut pas être créé. Le diagnostic du système doit passer."""
    source = _dce_simple(tmp_path / "DCE")
    dossier = _initialiser(source, tmp_path, capsys)
    _enregistrer(dossier, capsys, _tri_simple())
    _choisir(dossier, capsys)

    original = Path.mkdir

    def mkdir_trop_long(self, *args, **kwargs):
        if self.name.startswith("Lot "):
            raise OSError(errno.ENAMETOOLONG, "File name too long", str(self))
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", mkdir_trop_long)

    assert main(["livraison", "dossier", "--dossier", str(dossier)]) != 0
    message = "".join(capsys.readouterr())
    assert "Chemin trop long pour le système" in message, message
    assert "Le dossier de remise est inaccessible" not in message
