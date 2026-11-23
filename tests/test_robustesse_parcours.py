"""Tests de robustesse du parcours par lot.

Chaque test reproduit le scénario qu'il doit empêcher
de revenir : le guide et le code restent d'accord (exemples JSON du guide
joués tels quels), les écritures survivent aux volumes sans liens physiques et
aux fichiers verrouillés, aux interruptions et aux nettoyages manqués ; les
droits restent ceux du système, les messages restent en français de dossier.
Les simulations (liens physiques indisponibles, fichier verrouillé, chemin
trop long, interruption, suppression impossible) remplacent une fonction du
système et le disent en commentaire ; rien d'autre n'est substitué.

Un refus vérifie toujours le code de sortie non nul ET des fichiers inchangés
(empreinte de chaque fichier du dossier, avant/après).
"""

from __future__ import annotations

import errno
import hashlib
import json
import os
import re
import shutil
import stat
import sys
import textwrap
import time
import unicodedata
from datetime import datetime, timezone
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


def _changer_denomination(dossier: Path, nom: str) -> None:
    """Change un champ du formulaire dans valeurs.json : le DC1 du prochain
    remplissage aura des octets différents de ceux déjà publiés."""
    chemin = dossier / "candidature" / "valeurs.json"
    valeurs = json.loads(chemin.read_text(encoding="utf-8"))
    valeurs["DC1"]["champs"]["denomination"]["valeur"] = nom
    chemin.write_text(
        json.dumps(valeurs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def _ecrire_plan(dossier: Path) -> None:
    """Un plan à deux sections : sans lui, l'export de la matrice est refusé
    (« Matrice vide »)."""
    (dossier / "04-plan.md").write_text(
        "# Plan du mémoire\n\n"
        "- [ ] 01 — Présentation de l'entreprise\n"
        "- [ ] 02 — Organisation et moyens humains\n",
        encoding="utf-8",
    )


def _analyse_remplie(dossier: Path, lot: str = "02",
                     identite: str | None = None) -> None:
    """Les neuf rubriques de l'analyse du lot, rédigées, marqueur en moins.

    `identite` remplace le contenu par défaut de la rubrique Identité (les
    tests de la date limite y écrivent leurs formes de ligne)."""
    corps = {
        "En bref": "Lot principal, à répondre avec les moyens internes (fictif).",
        "Identité": identite if identite is not None else
                   "- Acheteur : Ville d'Exemple\n- Objet : "
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


def _dossiers_directs(dossier: Path) -> set[str]:
    """Noms des sous-dossiers immédiats d'un dossier (ce qui y vit, pas les
    fichiers) : le dossier d'attente se voit par différence entre deux
    instants, sans présumer de son nom."""
    if not dossier.is_dir():
        return set()
    return {p.name for p in dossier.iterdir() if p.is_dir()}


def _nettoyage_en_echec(monkeypatch, dossier: Path, *, lever: bool) -> None:
    """Simulation de la suppression impossible du dossier d'attente : un
    antivirus ou un client de synchronisation tient un fichier dedans (Windows,
    cas connu de tout nettoyeur de fichiers temporaires).

    `lever=True` : shutil.rmtree lève PermissionError sur le dossier d'attente
    de la commande en cours (dossier nouveau de `.remporte/`), et laisse passer
    partout ailleurs. Sinon, la suppression ne fait rien (équivalent d'un
    processus tué avant d'avoir fini de nettoyer).
    """
    interne = (dossier / ".remporte").resolve()
    connus = {p.resolve() for p in interne.iterdir() if p.is_dir()}
    original = shutil.rmtree

    def supprimer(chemin, *args, **kwargs):
        chemin = Path(chemin)
        if chemin.parent == interne and chemin.resolve() not in connus:
            if lever:
                raise PermissionError(errno.EACCES, "Permission denied", str(chemin))
            return None  # la suppression « réussit » sans rien supprimer
        return original(chemin, *args, **kwargs)

    monkeypatch.setattr(shutil, "rmtree", supprimer)


def _observer_attente(monkeypatch, dossier: Path) -> list[dict]:
    """Photographie `.remporte/` et `memoire/` à chaque publication, à l'instant
    où un fichier est renommé vers sa cible : c'est là qu'un dossier d'attente
    vivant doit se voir (dans `.remporte/` uniquement), avec les droits de
    `.remporte/`."""
    photos: list[dict] = []
    zones = {".remporte": dossier / ".remporte", "memoire": dossier / "memoire"}
    original = Path.replace

    def remplacer(self, cible, *args, **kwargs):
        photo: dict = {}
        for nom, zone in zones.items():
            if zone.is_dir():
                photo[nom] = {p.name: _mode(p) for p in zone.iterdir() if p.is_dir()}
        photo["mode_.remporte"] = _mode(zones[".remporte"])
        photos.append(photo)
        return original(self, cible, *args, **kwargs)

    monkeypatch.setattr(Path, "replace", remplacer)
    return photos


def _interrompre_a(monkeypatch, rang: int) -> None:
    """Simulation d'un Ctrl-C au milieu d'une publication : Path.replace lève
    KeyboardInterrupt à son n-ième appel (après les publications précédentes,
    avant la suivante), puis laisse tout passer."""
    original = Path.replace
    compteur = {"n": 0}

    def remplacer(self, cible, *args, **kwargs):
        compteur["n"] += 1
        if compteur["n"] == rang:
            raise KeyboardInterrupt
        return original(self, cible, *args, **kwargs)

    monkeypatch.setattr(Path, "replace", remplacer)


def _deux_verrous(monkeypatch, premier: str, second: str) -> None:
    """Deux fichiers tenus par deux programmes successifs : la publication du
    premier échoue, puis la remise (retour arrière) du second échoue à son
    tour. On distingue publication et retour arrière d'un même fichier par le
    rang de l'appel (la publication vient toujours en premier)."""
    original = Path.replace
    compteur: dict[str, int] = {}

    def remplacer(self, cible, *args, **kwargs):
        nom = Path(cible).name
        rang = compteur.get(nom, 0) + 1
        compteur[nom] = rang
        if (nom == premier and rang == 1) or (nom == second and rang == 2):
            raise PermissionError(errno.EACCES, "Permission denied", str(cible))
        return original(self, cible, *args, **kwargs)

    monkeypatch.setattr(Path, "replace", remplacer)


def _permission_windows(monkeypatch, relatif: str, code: int) -> None:
    """Simulation d'un refus de partage Windows (fichier ouvert par un autre
    programme) : le système se déclare Windows (sys.platform patché), et
    Path.replace lève PermissionError avec le winerror donné pour la cible
    indiquée, sinon laisse passer. (os.name ne peut pas être patché ici : sur
    ce système, pathlib refuserait d'instancier WindowsPath.)"""
    monkeypatch.setattr(sys, "platform", "win32")
    original = Path.replace

    def remplacer(self, cible, *args, **kwargs):
        cible = Path(cible)
        if cible.as_posix().endswith(relatif):
            erreur = PermissionError(errno.EACCES,
                                     "Le processus ne peut pas accéder au fichier")
            erreur.winerror = code
            raise erreur
        return original(self, cible, *args, **kwargs)

    monkeypatch.setattr(Path, "replace", remplacer)


# ---------------------------------------------------------------------------
# le tri écrit comme le guide le demande passe tels quels
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
# la question à l'acheteur écrite comme le guide le demande est conforme
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
# aucun lien physique requis : volume qui refuse os.link
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
# un fichier verrouillé refuse la commande sans rien modifier
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
# marques d'ordre d'octets et encodages
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
# options obligatoires refusées par la commande, en français
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
# deux identifiants qui ne diffèrent que par la casse ou les accents
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
# aucun message ne montre une valeur non textuelle
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
# page du rapport : date en clair, accord au singulier
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
# droits des fichiers écrits (POSIX)
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
# intitulé de lot long : coupé dans le nom du dossier, diagnostic gardé
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


# ---------------------------------------------------------------------------
# le nettoyage du dossier d'attente ne fait jamais échouer une commande réussie
# ---------------------------------------------------------------------------

def test_le_nettoyage_en_echec_ne_fait_pas_echouer_une_commande_reussie(
        tmp_path, monkeypatch, capsys):
    """Toutes les publications ont réussi ; à la fin, la suppression du dossier
    d'attente échoue (simulation : shutil.rmtree lève PermissionError sur le
    dossier nouveau de `.remporte/`). La commande doit rester un succès : les
    formulaires sont écrits, le refus ne dit pas le contraire."""
    source = _dce_simple(tmp_path / "DCE")
    dossier = _initialiser(source, tmp_path, capsys)
    _enregistrer(dossier, capsys, _tri_simple())
    _choisir(dossier, capsys)
    _candidature_prete(dossier, capsys)

    _nettoyage_en_echec(monkeypatch, dossier, lever=True)
    assert main(["candidature", "remplir", "--dossier", str(dossier), "--json"]) == 0
    monkeypatch.undo()
    sortie = json.loads(capsys.readouterr().out)
    assert sortie["ok"] is True
    remise = dossier / "reponse" / "Lot 02 - Électricité courants forts"
    assert (remise / "DC1.docx").is_file()
    assert (remise / "DC2.docx").is_file()


def test_un_dossier_d_attente_oublie_est_retire_a_la_commande_suivante(
        tmp_path, monkeypatch, capsys):
    """Un processus tué laisse son dossier d'attente dans `.remporte/`
    (simulation : shutil.rmtree ne supprime rien pendant une première
    commande). La commande suivante doit le retirer à son tour, et laisser le
    dossier comme il était."""
    source = _dce_simple(tmp_path / "DCE")
    dossier = _initialiser(source, tmp_path, capsys)
    _enregistrer(dossier, capsys, _tri_simple())
    interne = dossier / ".remporte"
    connus = _dossiers_directs(interne)

    _nettoyage_en_echec(monkeypatch, dossier, lever=False)
    assert main(["lots", "rapport", "--dossier", str(dossier), "--json"]) == 0
    capsys.readouterr()
    monkeypatch.undo()
    restes = _dossiers_directs(interne) - connus
    assert restes, "la simulation n'a laissé aucun dossier d'attente"
    # un processus tué il y a un moment : le reste date d'avant la commande suivante
    vieux = time.time() - 3600
    for nom in restes:
        os.utime(interne / nom, (vieux, vieux))

    assert main(["lots", "rapport", "--dossier", str(dossier), "--json"]) == 0
    capsys.readouterr()
    assert _dossiers_directs(interne) == connus
    assert (dossier / ".remporte" / "etat.json").is_file()  # l'état est intact


# ---------------------------------------------------------------------------
# le dossier d'attente vit dans .remporte/, avec ses droits, un nom aléatoire
# ---------------------------------------------------------------------------

def test_le_dossier_d_attente_vit_dans_remporte_heurite_ses_droits_et_disparait(
        tmp_path, monkeypatch, capsys):
    """Pendant une publication, le dossier d'attente vivant est observé par
    différence (on ne présume pas de son nom). Il doit être un sous-dossier
    direct de `.remporte/` (pas des dossiers publiés), porter les droits de
    `.remporte/` (un dossier réservé au propriétaire serait hérité par les
    fichiers publiés, notamment sous Windows) et disparaître avec la commande."""
    source = _dce_simple(tmp_path / "DCE")
    dossier = _initialiser(source, tmp_path, capsys)
    _enregistrer(dossier, capsys, _tri_simple())
    interne = dossier / ".remporte"
    connus = _dossiers_directs(interne)
    memoire_avant = _dossiers_directs(dossier / "memoire")

    photos = _observer_attente(monkeypatch, dossier)
    assert main(["lots", "rapport", "--dossier", str(dossier), "--json"]) == 0
    capsys.readouterr()
    monkeypatch.undo()

    observes = set()
    modes = set()
    for photo in photos:
        observes |= set(photo.get(".remporte", {})) - connus
        if observes:
            derniers = set(photo.get(".remporte", {})) & observes
            modes |= {photo[".remporte"][nom] for nom in derniers}
        # aucun dossier d'attente côté des dossiers publiés (memoire/ ici)
        assert set(photo.get("memoire", {})) == memoire_avant
    assert observes, "aucun dossier d'attente observé pendant la publication"
    assert len(observes) == 1, observes
    # il hérite des droits de .remporte/ (pas de mode réservé au propriétaire)
    assert modes == {_mode(interne)}, (modes, _mode(interne))
    # et il est parti à la fin de la commande
    assert _dossiers_directs(interne) == connus


def test_le_dossier_d_attente_change_de_nom_a_chaque_commande(
        tmp_path, monkeypatch, capsys):
    """Deux commandes successives ne doivent pas réutiliser le même nom de
    dossier d'attente (sinon deux commandes en parallèle dans le même dossier
    de réponse écriraient dans le même endroit)."""
    source = _dce_simple(tmp_path / "DCE")
    dossier = _initialiser(source, tmp_path, capsys)
    _enregistrer(dossier, capsys, _tri_simple())
    connus = _dossiers_directs(dossier / ".remporte")

    def noms_observes(photos):
        observes = set()
        for photo in photos:
            observes |= set(photo.get(".remporte", {})) - connus
        return observes

    photos = _observer_attente(monkeypatch, dossier)
    assert main(["lots", "rapport", "--dossier", str(dossier), "--json"]) == 0
    capsys.readouterr()
    monkeypatch.undo()
    premiere = noms_observes(photos)
    assert premiere

    photos = _observer_attente(monkeypatch, dossier)
    assert main(["lots", "rapport", "--dossier", str(dossier), "--json"]) == 0
    capsys.readouterr()
    monkeypatch.undo()
    seconde = noms_observes(photos)
    assert seconde
    assert not (premiere & seconde), (premiere, seconde)


# ---------------------------------------------------------------------------
# « Fermez … » seulement pour un fichier tenu par un autre programme (Windows)
# ---------------------------------------------------------------------------

def test_un_refus_de_droits_parle_de_droits_et_pas_de_fichier_a_fermer(
        tmp_path, capsys):
    """Sous macOS et Linux, un fichier ouvert ne bloque jamais une écriture :
    un refus de droits (ici le dossier memoire/ mis en lecture seule, refus
    réel du système) doit dire de vérifier les droits, jamais de fermer un
    fichier."""
    source = _dce_simple(tmp_path / "DCE")
    dossier = _initialiser(source, tmp_path, capsys)
    _ecrire_tri(dossier, _tri_simple())
    empreintes = _empreintes(dossier)
    (dossier / "memoire").chmod(0o555)
    try:
        assert main(["lots", "enregistrer", "--dossier", str(dossier)]) != 0
        message = "".join(capsys.readouterr())
        assert ("Impossible d'écrire lots.json : vérifiez les droits du "
                "dossier.") in message, message
        assert "Fermez" not in message, message
        assert _empreintes(dossier) == empreintes  # inventaire remis, tri intact
    finally:
        (dossier / "memoire").chmod(0o755)


def test_un_fichier_tenu_par_un_autre_programme_sous_windows_parle_de_fermeture(
        tmp_path, monkeypatch, capsys):
    """Sous Windows, un fichier ouvert par un autre programme refuse le
    partage (winerror 32) : là seulement, le conseil de fermer le fichier est
    le bon. Simulation : os.name et sys.platform sont patchés tous les deux,
    et Path.replace lève PermissionError avec winerror 32 sur
    memoire/lots.json."""
    source = _dce_simple(tmp_path / "DCE")
    dossier = _initialiser(source, tmp_path, capsys)
    _ecrire_tri(dossier, _tri_simple())
    empreintes = _empreintes(dossier)

    _permission_windows(monkeypatch, "memoire/lots.json", 32)
    assert main(["lots", "enregistrer", "--dossier", str(dossier)]) != 0
    message = "".join(capsys.readouterr())
    assert "Fermez lots.json puis relancez." in message, message
    assert _empreintes(dossier) == empreintes


# ---------------------------------------------------------------------------
# une interruption annule ce que la commande a publié
# ---------------------------------------------------------------------------

def test_une_interruption_pendant_l_ecriture_annule_ce_qui_est_publie(
        tmp_path, monkeypatch, capsys):
    """Ctrl-C après le premier formulaire publié, avant le second
    (simulation : Path.replace lève KeyboardInterrupt au deuxième appel).
    L'interruption doit ressortir telle quelle, et tout doit être revenu à
    l'état d'avant, dossier d'attente compris."""
    source = _dce_simple(tmp_path / "DCE")
    dossier = _initialiser(source, tmp_path, capsys)
    _enregistrer(dossier, capsys, _tri_simple())
    _choisir(dossier, capsys)
    _candidature_prete(dossier, capsys)
    assert main(["candidature", "remplir", "--dossier", str(dossier)]) == 0
    capsys.readouterr()
    _changer_denomination(dossier, "Entreprise Exemple SAS et partenaires")
    empreintes = _empreintes(dossier)
    connus = _dossiers_directs(dossier / ".remporte")

    _interrompre_a(monkeypatch, 2)  # DC1 publié (nouvelle version), DC2 non
    with pytest.raises(KeyboardInterrupt):
        main(["candidature", "remplir", "--remplacer",
              "--dossier", str(dossier)])
    monkeypatch.undo()
    assert _empreintes(dossier) == empreintes  # DC1 remise, DC2 intact
    assert _dossiers_directs(dossier / ".remporte") == connus  # aucun reste


def test_une_interruption_pendant_le_choix_des_lots_se_repare_avec_lots_enregistrer(
        tmp_path, monkeypatch, capsys):
    """Ctrl-C pendant `lots choisir`, entre le relevé du choix et la fin des
    publications (simulation : KeyboardInterrupt au dernier appel de
    Path.replace). L'état qui reste doit se réparer par la commande prévue :
    `lots enregistrer` relance la validation et remet le choix, sans qu'on
    touche au tri à la main."""
    source = _dce_simple(tmp_path / "DCE")
    dossier = _initialiser(source, tmp_path, capsys)
    _enregistrer(dossier, capsys, _tri_simple())
    connus = _dossiers_directs(dossier / ".remporte")

    # publications de `lots choisir` : deux analyses, le tri, le relevé du choix
    _interrompre_a(monkeypatch, 4)
    with pytest.raises(KeyboardInterrupt):
        main(["lots", "choisir", "--lots", "02", "--par", "Camille Exemple",
              "--dossier", str(dossier)])
    monkeypatch.undo()
    assert _dossiers_directs(dossier / ".remporte") == connus  # aucun reste

    assert main(["lots", "enregistrer", "--dossier", str(dossier), "--json"]) == 0
    sortie = json.loads(capsys.readouterr().out)
    assert sortie["ok"] is True
    assert sortie["choix"]["retenus"] == ["02"]
    assert sortie["choix"]["par"] == "Camille Exemple"
    tri = json.loads((dossier / "memoire" / "lots.json").read_text("utf-8"))
    assert tri["choix"]["retenus"] == ["02"]


# ---------------------------------------------------------------------------
# un fichier enregistré pendant l'opération n'est pas écrasé par le retour arrière
# ---------------------------------------------------------------------------

def test_un_fichier_enregistre_pendant_l_operation_n_est_pas_ecrase(
        tmp_path, monkeypatch, capsys):
    """La matrice est publiée, puis la publication de la feuille échoue
    (simulation : PermissionError sur feuille-de-route.html) ; au même
    instant, un enregistrement d'utilisateur réécrit la matrice (octets
    différents). Le retour arrière doit laisser cette version et le dire, pas
    remettre l'ancienne par-dessus."""
    source = _dce_simple(tmp_path / "DCE")
    dossier = _initialiser(source, tmp_path, capsys)
    _enregistrer(dossier, capsys, _tri_simple())
    _choisir(dossier, capsys)
    _ecrire_plan(dossier)
    assert main(["exporter", "--formats", "matrice,feuille",
                 "--dossier", str(dossier)]) == 0
    capsys.readouterr()
    matrice = dossier / "export" / "matrice-conformite.xlsx"
    feuille = dossier / "export" / "feuille-de-route.html"
    enregistrement = b"enregistre entre-temps par l'utilisateur"
    connus = _dossiers_directs(dossier / ".remporte")
    empreintes_avant = {"matrice": matrice.read_bytes(), "feuille": feuille.read_bytes()}

    original = Path.replace

    def remplacer(self, cible, *args, **kwargs):
        cible = Path(cible)
        if cible.name == "feuille-de-route.html":
            # l'utilisateur enregistre la matrice pendant que la commande échoue
            matrice.write_bytes(enregistrement)
            raise PermissionError(errno.EACCES, "Permission denied", str(cible))
        return original(self, cible, *args, **kwargs)

    monkeypatch.setattr(Path, "replace", remplacer)
    assert main(["exporter", "--formats", "matrice,feuille",
                 "--dossier", str(dossier)]) != 0
    message = "".join(capsys.readouterr())
    monkeypatch.undo()
    assert ("matrice-conformite.xlsx a été modifié pendant l'opération : "
            "il est conservé.") in message, message
    assert matrice.read_bytes() == enregistrement  # la version récente est gardée
    # la feuille, jamais publiée au second tour, est revenue à la version d'avant
    assert feuille.read_bytes() == empreintes_avant["feuille"]
    assert _dossiers_directs(dossier / ".remporte") == connus  # aucun reste


# ---------------------------------------------------------------------------
# un retour arrière en échec continue pour les autres et nomme ce qui reste
# ---------------------------------------------------------------------------

def test_un_retour_arriere_en_echec_continue_et_nomme_ce_qui_n_est_pas_remis(
        tmp_path, monkeypatch, capsys):
    """La publication du DC4 échoue (fichier verrouillé), puis la remise du
    DC2 échoue aussi pendant le retour arrière (deux programmes distincts
    tiennent les deux fichiers, simulation : _deux_verrous). Le retour
    arrière doit remettre quand même le DC1, et le message doit nommer le
    DC2, laissé dans sa version publiée."""
    source = _dce_simple(tmp_path / "DCE")
    dossier = _initialiser(source, tmp_path, capsys)
    _enregistrer(dossier, capsys, _tri_simple())
    _choisir(dossier, capsys)
    _candidature_prete(dossier, capsys)
    chemin_valeurs = dossier / "candidature" / "valeurs.json"
    valeurs = json.loads(chemin_valeurs.read_text(encoding="utf-8"))
    valeurs["DC4"]["champs"]["sous_traitance"]["valeur"] = True
    chemin_valeurs.write_text(
        json.dumps(valeurs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    assert main(["candidature", "remplir", "--dossier", str(dossier)]) == 0
    capsys.readouterr()
    remise = dossier / "reponse" / "Lot 02 - Électricité courants forts"
    empreintes = _empreintes(dossier)
    _changer_denomination(dossier, "Entreprise Exemple SAS et partenaires")

    _deux_verrous(monkeypatch, "DC4.docx", "DC2.docx")
    assert main(["candidature", "remplir", "--remplacer",
                 "--dossier", str(dossier)]) != 0
    message = "".join(capsys.readouterr())
    monkeypatch.undo()
    empreintes_apres = _empreintes(dossier)
    # le DC1 a été remis malgré l'échec de la remise du DC2
    assert empreintes_apres[f"reponse/Lot 02 - Électricité courants forts/DC1.docx"] \
        == empreintes[f"reponse/Lot 02 - Électricité courants forts/DC1.docx"]
    # le DC2 est resté dans sa version publiée : le message doit le nommer
    assert empreintes_apres[f"reponse/Lot 02 - Électricité courants forts/DC2.docx"] \
        != empreintes[f"reponse/Lot 02 - Électricité courants forts/DC2.docx"]
    assert "DC2.docx" in message, message
    # le DC4, jamais publié, est resté tel quel
    assert empreintes_apres[f"reponse/Lot 02 - Électricité courants forts/DC4.docx"] \
        == empreintes[f"reponse/Lot 02 - Électricité courants forts/DC4.docx"]


# ---------------------------------------------------------------------------
# le tri modifié depuis son enregistrement renvoie à la commande de validation
# ---------------------------------------------------------------------------

COMMANDES_TRI_MODIFIE = [
    ("lots_choisir", ["lots", "choisir", "--lots", "02", "--par", "Camille"]),
    ("lots_rapport", ["lots", "rapport"]),
    ("livraison_dossier", ["livraison", "dossier"]),
]


@pytest.mark.parametrize("nom,commande", COMMANDES_TRI_MODIFIE,
                         ids=[c[0] for c in COMMANDES_TRI_MODIFIE])
def test_un_tri_modifie_depuis_son_enregistrement_renvoie_a_lots_enregistrer(
        tmp_path, capsys, nom, commande):
    """Le tri a été réécrit après `lots enregistrer` (l'agent l'a changé sans
    revalidation) : le refus nomme la commande qui le fait valider à nouveau."""
    source = _dce_simple(tmp_path / "DCE")
    dossier = _initialiser(source, tmp_path, capsys)
    _enregistrer(dossier, capsys, _tri_simple())
    tri = json.loads((dossier / "memoire" / "lots.json").read_text("utf-8"))
    tri["lots"][0]["intitule"] = "Électricité courants forts et faibles"
    (dossier / "memoire" / "lots.json").write_text(
        json.dumps(tri, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    empreintes = _empreintes(dossier)

    assert main([*commande, "--dossier", str(dossier)]) != 0
    message = "".join(capsys.readouterr())
    assert ("Le tri des lots a changé depuis son enregistrement : faites-le "
            "valider à nouveau (remporte lots enregistrer).") in message, message
    assert _empreintes(dossier) == empreintes
    assert not (dossier / "reponse").exists()  # livraison dossier n'a rien créé


# ---------------------------------------------------------------------------
# la date limite : réception, parenthèses, puces et sources en lien markdown
# ---------------------------------------------------------------------------

def test_la_date_limite_vaut_pour_la_reception_hors_parentheses_et_en_puce_etoile(
        tmp_path, capsys):
    """La date limite des offres s'écrit « réception des offres », en puce
    étoile, et une ligne de questions qui contient le mot « remise » entre
    parenthèses ne doit pas être prise pour elle."""
    source = _dce_simple(tmp_path / "DCE")
    dossier = _initialiser(source, tmp_path, capsys)
    _enregistrer(dossier, capsys, _tri_simple())
    _choisir(dossier, capsys)
    _analyse_remplie(dossier, identite=(
        "- Acheteur : Ville d'Exemple\n"
        "- Date limite des questions (au plus tard dix jours avant la remise) : "
        "1er juin 2026\n"
        "* Date limite de réception des offres : 12 juin 2026 à 17 h 00\n"))

    assert main(["exporter", "--formats", "feuille",
                 "--dossier", str(dossier)]) == 0
    capsys.readouterr()
    page = (dossier / "export" / "feuille-de-route.html").read_text("utf-8")
    assert "Date limite de remise" in page, page
    assert "12 juin 2026 à 17 h 00" in page, page
    assert "1er juin 2026" not in page, page  # les mots entre parenthèses ne comptent pas


def test_une_source_en_lien_markdown_est_retiree_de_la_date_limite(
        tmp_path, capsys):
    """Une source écrite en lien markdown est retirée comme une source entre
    crochets : le libellé du lien et sa cible ne doivent pas rester collés à
    la date."""
    source = _dce_simple(tmp_path / "DCE")
    dossier = _initialiser(source, tmp_path, capsys)
    _enregistrer(dossier, capsys, _tri_simple())
    _choisir(dossier, capsys)
    _analyse_remplie(dossier, identite=(
        "- Acheteur : Ville d'Exemple\n"
        "- Date limite de remise des offres : 12 juin 2026 à 17 h 00 "
        "[voir le règlement](dce/RC.pdf) art. 5\n"))

    assert main(["exporter", "--formats", "feuille",
                 "--dossier", str(dossier)]) == 0
    capsys.readouterr()
    page = (dossier / "export" / "feuille-de-route.html").read_text("utf-8")
    assert "Date limite de remise" in page, page
    assert "12 juin 2026 à 17 h 00 art. 5" in page, page
    assert "(dce/RC.pdf)" not in page, page
    assert "voir le règlement" not in page, page


def test_la_date_limite_se_lit_sur_une_ligne_sans_puce(tmp_path, capsys):
    """La rubrique Identité peut porter la date limite sur une ligne simple,
    sans puce ni tableau."""
    source = _dce_simple(tmp_path / "DCE")
    dossier = _initialiser(source, tmp_path, capsys)
    _enregistrer(dossier, capsys, _tri_simple())
    _choisir(dossier, capsys)
    _analyse_remplie(dossier, identite=(
        "- Acheteur : Ville d'Exemple\n"
        "Date limite de réception des offres : 12 juin 2026 à 17 h 00\n"))

    assert main(["exporter", "--formats", "feuille",
                 "--dossier", str(dossier)]) == 0
    capsys.readouterr()
    page = (dossier / "export" / "feuille-de-route.html").read_text("utf-8")
    assert "Date limite de remise" in page, page
    assert "12 juin 2026 à 17 h 00" in page, page


# ---------------------------------------------------------------------------
# la date du choix s'affiche dans le fuseau du poste
# ---------------------------------------------------------------------------

@pytest.mark.skipif(os.name == "nt", reason="fuseau forcé via TZ et time.tzset()")
def test_la_date_du_choix_s_affiche_dans_le_fuseau_du_poste(
        tmp_path, capsys, monkeypatch):
    """Un choix fait à une heure dont le jour diffère entre UTC et le poste
    (fuseau forcé choisi pour garantir l'écart) doit s'afficher à la date du
    poste, pas à la date UTC."""
    source = _dce_simple(tmp_path / "DCE")
    dossier = _initialiser(source, tmp_path, capsys)
    _enregistrer(dossier, capsys, _tri_simple())
    maintenant = datetime.now(timezone.utc)
    fuseau = "Etc/GMT+12" if maintenant.hour < 12 else "Pacific/Kiritimati"
    monkeypatch.setenv("TZ", fuseau)
    time.tzset()
    try:
        _choisir(dossier, capsys)
        date_choix = datetime.fromisoformat(json.loads(
            (dossier / "memoire" / "lots.json").read_text("utf-8")
        )["choix"]["date"])
        attendue = date_choix.astimezone().strftime("%d/%m/%Y")
        assert attendue != date_choix.strftime("%d/%m/%Y"), \
            "fuseau sans changement de jour : relancer le test"

        assert main(["lots", "rapport", "--dossier", str(dossier)]) == 0
        capsys.readouterr()
        page = (dossier / "memoire" / "rapport-lots.html").read_text("utf-8")
        assert f"choisi par Camille Exemple le {attendue}." in page, page
        assert f"le {date_choix.strftime('%d/%m/%Y')}." not in page, page
    finally:
        monkeypatch.undo()
        time.tzset()


# ---------------------------------------------------------------------------
# gardes : ce qui marche déjà doit continuer de marcher quand publier change
# ---------------------------------------------------------------------------

def test_une_feuille_verrouillee_annule_les_autres_exports(
        tmp_path, monkeypatch, capsys):
    """Garde du retour arrière d'`exporter` : la publication de la feuille
    échoue (fichier verrouillé), la matrice publiée juste avant doit revenir à
    la version d'avant la commande. Le plan change entre les deux exports pour
    que les exports du deuxième tour aient des octets différents des premiers."""
    source = _dce_simple(tmp_path / "DCE")
    dossier = _initialiser(source, tmp_path, capsys)
    _enregistrer(dossier, capsys, _tri_simple())
    _choisir(dossier, capsys)
    _ecrire_plan(dossier)
    assert main(["exporter", "--formats", "matrice,feuille",
                 "--dossier", str(dossier)]) == 0
    capsys.readouterr()
    # une section de plus : les exports du deuxième tour diffèrent des premiers
    plan = dossier / "04-plan.md"
    plan.write_text(plan.read_text(encoding="utf-8")
                    + "- [ ] 03 — Moyens matériels sur site\n", encoding="utf-8")
    empreintes = _empreintes(dossier)

    _verrouiller(monkeypatch, "feuille-de-route.html")
    assert main(["exporter", "--formats", "matrice,feuille",
                 "--dossier", str(dossier)]) != 0
    message = "".join(capsys.readouterr())
    monkeypatch.undo()
    assert message.strip(), "aucun message de refus"
    assert _empreintes(dossier) == empreintes  # la matrice est revenue d'avant

    assert main(["exporter", "--formats", "matrice,feuille",
                 "--dossier", str(dossier)]) == 0
    capsys.readouterr()


def test_l_inventaire_est_remis_quand_l_enregistrement_echoue_apres_lui(
        tmp_path, monkeypatch, capsys):
    """Garde du retour arrière sur l'inventaire : `01-pieces.md` est le
    premier fichier publié par `lots enregistrer` ; quand la publication du
    tri échoue juste après (simulation : verrou sur tout fichier nommé
    lots.json), l'inventaire déjà publié doit être remis à l'identique —
    avec sa colonne « Lot » d'origine, pas celle qui vient d'être remplie."""
    source = _dce_simple(tmp_path / "DCE")
    dossier = _initialiser(source, tmp_path, capsys)
    _ecrire_tri(dossier, _tri_simple())
    empreintes = _empreintes(dossier)
    assert "commun" not in (dossier / "01-pieces.md").read_text("utf-8")

    _verrouiller(monkeypatch, "lots.json")  # memoire/lots.json et .remporte/lots.json
    assert main(["lots", "enregistrer", "--dossier", str(dossier)]) != 0
    capsys.readouterr()
    monkeypatch.undo()
    assert _empreintes(dossier) == empreintes  # inventaire, tri et relevé intacts

    assert main(["lots", "enregistrer", "--dossier", str(dossier)]) == 0
    capsys.readouterr()
