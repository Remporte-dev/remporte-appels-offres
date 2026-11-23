"""Tests du parcours par lot : tri (memoire/lots.json), choix, rapport, état, init.

Le tri des pièces par lot est écrit par l'agent dans memoire/lots.json, validé
et réécrit par `remporte lots enregistrer`, puis l'utilisateur choisit les lots
retenus (`lots choisir`), un rapport HTML les présente (`lots rapport`) et
`etat` décrit l'étape analyse en libellés de métier. `init` ne déduit plus le
lot du nom de fichier et ne crée plus l'ancienne analyse unique.

Chaque refus vérifie le code de sortie non nul ET l'absence de modification
des fichiers (relus avant/après). Aucun mock du code testé ; seul
`webbrowser.open` est remplacé, conformément à la commande `--ouvrir`.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import unicodedata
import webbrowser
from pathlib import Path

import pytest
from conftest import ecrire_pdf, fabriquer_docx, fabriquer_xlsx

from remporte.cli import main

# Les neuf rubriques d'une analyse de lot, dans l'ordre imposé. La comparaison des titres est
# insensible à la casse, aux apostrophes typographiques et au « : » final :
# on normalise des deux côtés au lieu de figer l'orthographe exacte.
RUBRIQUES = [
    "En bref",
    "Identité",
    "Ce que l'acheteur attend vraiment",
    "Critères et pondérations",
    "Pièces à remettre et formes imposées",
    "Incohérences entre pièces",
    "Pièces illisibles ou absentes",
    "Documents de référence et versions",
    "Avis",
]

MARQUEUR = "<!-- à remplir -->"


# ---------------------------------------------------------------------------
# Aides : DCE alloti, dossier de réponse, tri valide
# ---------------------------------------------------------------------------

def _fabriquer_dce_alloti(source: Path) -> Path:
    """RC et CCAP communs ; CCTP lot 02, DPGF lot 05 ; un plan partagé ;
    une pièce scannée (statut « vide » donc non lisible pour le tri)."""
    (source / "LOT 02").mkdir(parents=True)
    (source / "LOT 05").mkdir(parents=True)
    # Une page par pièce, assez de texte pour que l'inventaire la dise lisible.
    ecrire_pdf(source / "RC.pdf", [
        "Reglement de la consultation du marche\n"
        "Le marche est alloti en deux lots :\n"
        "Lot 02 : electricite courants forts.\n"
        "Lot 05 : courants faibles et resolution.",
    ])
    ecrire_pdf(source / "CCAP.pdf", [
        "Cahier des clauses administratives particulieres\n"
        "Les penalites de retard sont fixees au RC.",
    ])
    ecrire_pdf(source / "LOT 02/CCTP lot 02.pdf", [
        "Cahier des clauses techniques particulieres du lot 02\n"
        "Tableau electrique de division, protection differentielle, "
        "colonnes de mesure.",
    ])
    fabriquer_xlsx(source / "LOT 05/DPGF lot 05.xlsx")
    ecrire_pdf(source / "Plan L2 étage.pdf", [
        "Plan d execution de l etage 2 du batiment A, niveaux et cotes.",
    ])
    ecrire_pdf(source / "notice scannee.pdf", ["", ""])  # PDF scanné → « vide »
    return source


def _dossier_alorti(tmp_path: Path, capsys=None) -> Path:
    """Dossier de réponse initialisé par `remporte init` sur le DCE alloti."""
    source = _fabriquer_dce_alloti(tmp_path / "DCE")
    dossier = tmp_path / "reponse"
    assert main(["init", str(source), "--dossier", str(dossier)]) == 0
    if capsys:
        capsys.readouterr()
    return dossier


def _tri_valide() -> dict:
    """Un tri complet : deux lots, une pièce dans les deux, deux communes,
    une illisible, une clé supplémentaire (admise et conservée)."""
    return {
        "schema_version": 1,
        "allotissement": "lots",
        "lots": [
            {
                "id": "02",
                "intitule": "Électricité courants forts",
                "pieces": ["dce/LOT 02/CCTP lot 02.pdf", "dce/Plan L2 étage.pdf"],
                "parties_communes": [],
                "recommandation": {
                    "avis": "repondre",
                    "raison": "Cœur du métier de l'entreprise.",
                },
            },
            {
                "id": "05",
                "intitule": "Courants faibles",
                "pieces": ["dce/LOT 05/DPGF lot 05.xlsx", "dce/Plan L2 étage.pdf"],
                "parties_communes": [],
                "recommandation": {
                    "avis": "a_discuter",
                    "raison": "Dérive possible du périmètre.",
                },
            },
        ],
        "pieces_communes": ["dce/RC.pdf", "dce/CCAP.pdf"],
        "pieces_illisibles": ["dce/notice scannee.pdf"],
        "types_pieces": {
            "dce/RC.pdf": "RC",
            "dce/CCAP.pdf": "CCAP",
            "dce/LOT 02/CCTP lot 02.pdf": "CCTP",
            "dce/LOT 05/DPGF lot 05.xlsx": "DPGF",
            "dce/Plan L2 étage.pdf": "plan",
        },
        "choix": None,
        "remise_le": "2026-12-01",
    }


def _ecrire_tri(dossier: Path, donnees: dict | None = None,
                brut: str | None = None) -> Path:
    """Écrit memoire/lots.json compact (sans indentation) : la réécriture
    normalisée de `enregistrer` doit ensuite indenter le fichier."""
    chemin = dossier / "memoire" / "lots.json"
    chemin.parent.mkdir(parents=True, exist_ok=True)
    if brut is not None:
        chemin.write_text(brut, encoding="utf-8")
    else:
        chemin.write_text(
            json.dumps(donnees if donnees is not None else _tri_valide(),
                       ensure_ascii=False),
            encoding="utf-8",
        )
    return chemin


def _contenus(dossier: Path) -> dict[str, str]:
    """Empreinte de chaque fichier du dossier : un refus ne doit rien modifier,
    ni rien ajouter (relevé du choix, analyses de lot, temporaire oublié)."""
    empreintes: dict[str, str] = {}
    for chemin in sorted(dossier.rglob("*")):
        if chemin.is_file():
            empreintes[chemin.relative_to(dossier).as_posix()] = \
                hashlib.sha256(chemin.read_bytes()).hexdigest()
    return empreintes


def _dossier_tri_enregistre(tmp_path: Path, capsys) -> Path:
    dossier = _dossier_alorti(tmp_path, capsys)
    _ecrire_tri(dossier)
    assert main(["lots", "enregistrer", "--dossier", str(dossier)]) == 0
    capsys.readouterr()
    return dossier


def _dossier_choix_fait(tmp_path: Path, capsys, ids: str = "02,05") -> Path:
    dossier = _dossier_tri_enregistre(tmp_path, capsys)
    assert main(["lots", "choisir", "--lots", ids, "--par", "Camille",
                 "--dossier", str(dossier)]) == 0
    capsys.readouterr()
    return dossier


def _lecture_du_tri(dossier: Path) -> dict:
    return json.loads((dossier / "memoire" / "lots.json").read_text("utf-8"))


# ---------------------------------------------------------------------------
# Analyse de lot : rubriques, marqueur, questions conformes
# ---------------------------------------------------------------------------

def _rubrique_normalisee(titre: str) -> str:
    titre = titre.replace("\u2019", "'").strip().rstrip(":").strip()
    return " ".join(titre.lower().split())


def _rubriques(texte: str) -> list[str]:
    return [_rubrique_normalisee(ligne[3:])
            for ligne in texte.splitlines() if ligne.startswith("## ")]


def _analyse_texte(lot: str = "02") -> str:
    """Une analyse faite : les neuf rubriques dans l'ordre, aucun marqueur."""
    return "\n\n".join(
        f"## {titre}\n\nRédigé pour le lot {lot}." for titre in RUBRIQUES
    ) + "\n"


def _questions_conformes(nb: int = 3) -> list[dict]:
    questions = []
    for rang in range(1, nb + 1):
        questions.append({
            "id": f"I-{rang}",
            "contexte": f"Deux pièces du lot donnent des valeurs différentes "
                        f"au point {rang}.",
            "question": f"Quelle valeur retenir au point {rang} ?",
            "sources": [f"Article {rang}.2 du CCTP",
                        f"Ligne {rang} du cadre de chiffrage"],
            "impact_prix": f"Écart de prix au point {rang}.",
        })
    return questions


def _question(**surcharge) -> list[dict]:
    """Une question conforme, surchargée pour fabriquer un cas non conforme."""
    question = {
        "id": "I-1",
        "contexte": "Le CCTP demande quarante prises et le chiffrage en "
                    "compte trente-deux.",
        "question": "Pouvez-vous confirmer le nombre de prises attendu ?",
        "sources": ["CCTP article 4.2", "DPGF ligne 3.1"],
        "impact_prix": "Huit prises de plus ou de moins.",
    }
    question.update(surcharge)
    return [question]


def _analyse_faite(dossier: Path, lot: str, questions: list[dict] | None = None) -> None:
    (dossier / "analyse" / f"lot-{lot}.md").write_text(
        _analyse_texte(lot), encoding="utf-8")
    (dossier / "analyse" / f"lot-{lot}.json").write_text(
        json.dumps({"questions_acheteur": questions or []},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# 1. `lots enregistrer` — cas nominal
# ---------------------------------------------------------------------------

def test_enregistrer_tri_valide_reecrit_le_tri_et_la_colonne_lot(tmp_path, capsys):
    dossier = _dossier_alorti(tmp_path, capsys)
    chemin_tri = _ecrire_tri(dossier)
    brut_avant = chemin_tri.read_text(encoding="utf-8")
    assert "\n  \"" not in brut_avant  # écrit compact : pas encore normalisé

    assert main(["lots", "enregistrer", "--dossier", str(dossier)]) == 0
    capsys.readouterr()

    brut_apres = chemin_tri.read_text(encoding="utf-8")
    assert "\n  \"" in brut_apres        # réécrit en JSON indenté
    assert "Électricité" in brut_apres   # UTF-8 direct, pas d'échappement \u00c9
    tri = json.loads(brut_apres)
    assert tri["schema_version"] == 1
    assert [lot["id"] for lot in tri["lots"]] == ["02", "05"]
    assert tri["choix"] is None
    assert tri["remise_le"] == "2026-12-01"  # clé supplémentaire conservée

    assert main(["lots", "enregistrer", "--dossier", str(dossier),
                 "--json"]) == 0
    sortie = json.loads(capsys.readouterr().out)
    assert sortie["ok"] is True
    assert sortie["lots"] == ["02", "05"]
    assert sortie["pieces_communes"] == 2
    assert sortie["choix"] is None

    inventaire = (dossier / "01-pieces.md").read_text(encoding="utf-8")
    assert "| 02 | `dce/LOT 02/CCTP lot 02.pdf`" in inventaire
    assert "| 05 | `dce/LOT 05/DPGF lot 05.xlsx`" in inventaire
    assert "| commun | `dce/RC.pdf`" in inventaire
    assert "| commun | `dce/CCAP.pdf`" in inventaire
    # une pièce rangée dans les deux lots porte les deux ids
    assert "| 02, 05 | `dce/Plan L2 étage.pdf`" in inventaire
    # une pièce illisible n'appartient à aucun lot
    assert "| — | `dce/notice scannee.pdf`" in inventaire


# ---------------------------------------------------------------------------
# 2. `lots enregistrer` — refus, un par cas : code ≠ 0, fichiers inchangés,
#    message qui nomme l'objet fautif
# ---------------------------------------------------------------------------

def _cas_fichier_absent(dossier: Path) -> None:
    pass  # pas de memoire/lots.json du tout


def _cas_json_illisible(dossier: Path) -> None:
    _ecrire_tri(dossier, brut="{oops pas du json")


def _cas_schema_version_inconnue(dossier: Path) -> None:
    tri = _tri_valide()
    tri["schema_version"] = 2
    _ecrire_tri(dossier, tri)


def _cas_id_vide(dossier: Path) -> None:
    tri = _tri_valide()
    tri["lots"][0]["id"] = ""
    _ecrire_tri(dossier, tri)


def _cas_id_en_double(dossier: Path) -> None:
    tri = _tri_valide()
    tri["lots"][1]["id"] = "02"
    _ecrire_tri(dossier, tri)


def _cas_id_avec_barre_oblique(dossier: Path) -> None:
    tri = _tri_valide()
    tri["lots"][0]["id"] = "02/bis"
    _ecrire_tri(dossier, tri)


def _cas_unique_melee_a_d_autres_lots(dossier: Path) -> None:
    tri = _tri_valide()
    tri["lots"][0]["id"] = "unique"
    _ecrire_tri(dossier, tri)


def _cas_allotissement_unique_mal_employe(dossier: Path) -> None:
    tri = _tri_valide()
    tri["allotissement"] = "unique"
    # toutes les pièces restent réparties : la seule erreur est l'identifiant
    tri["lots"] = [tri["lots"][0]]
    tri["lots"][0]["id"] = "03"
    tri["lots"][0]["pieces"].append("dce/LOT 05/DPGF lot 05.xlsx")
    _ecrire_tri(dossier, tri)


def _cas_intitule_vide(dossier: Path) -> None:
    tri = _tri_valide()
    tri["lots"][0]["intitule"] = ""
    _ecrire_tri(dossier, tri)


def _cas_avis_hors_liste(dossier: Path) -> None:
    tri = _tri_valide()
    tri["lots"][0]["recommandation"]["avis"] = "peut_etre"
    _ecrire_tri(dossier, tri)


def _cas_raison_vide(dossier: Path) -> None:
    tri = _tri_valide()
    tri["lots"][0]["recommandation"]["raison"] = ""
    _ecrire_tri(dossier, tri)


def _cas_partie_commune_inconnue(dossier: Path) -> None:
    tri = _tri_valide()
    tri["lots"][0]["parties_communes"] = ["09"]
    _ecrire_tri(dossier, tri)


def _cas_piece_inconnue_chemin_proche(dossier: Path) -> None:
    tri = _tri_valide()
    tri["pieces_communes"].append("dce/RC v2.pdf")
    _ecrire_tri(dossier, tri)


def _cas_deux_pieces_non_reparties(dossier: Path) -> None:
    # le lot 02 ne garde que le CCTP, le lot 05 disparaît : DPGF et Plan
    # ne sont plus réparties nulle part, les deux doivent être citées
    tri = _tri_valide()
    tri["lots"][0]["pieces"] = ["dce/LOT 02/CCTP lot 02.pdf"]
    tri["lots"] = [tri["lots"][0]]
    _ecrire_tri(dossier, tri)


def _cas_piece_lisible_declaree_illisible(dossier: Path) -> None:
    tri = _tri_valide()
    tri["pieces_illisibles"] = ["dce/RC.pdf", "dce/notice scannee.pdf"]
    _ecrire_tri(dossier, tri)


def _cas_type_manquant(dossier: Path) -> None:
    tri = _tri_valide()
    del tri["types_pieces"]["dce/CCAP.pdf"]
    _ecrire_tri(dossier, tri)


def _cas_type_hors_liste(dossier: Path) -> None:
    tri = _tri_valide()
    tri["types_pieces"]["dce/RC.pdf"] = "RCAP"
    _ecrire_tri(dossier, tri)


def _cas_type_en_double_apres_normalisation(dossier: Path) -> None:
    # même type, même pièce désignée (double espace au lieu d'un seul) : la
    # deuxième entrée est refusée, même quand le type est identique
    tri = _tri_valide()
    tri["types_pieces"]["dce/LOT  02/CCTP lot 02.pdf"] = "CCTP"
    _ecrire_tri(dossier, tri)


def _cas_choix_ecrit_par_l_agent(dossier: Path) -> None:
    tri = _tri_valide()
    tri["choix"] = {"retenus": ["02"], "par": "Agent",
                    "date": "2026-11-23T10:00:00+00:00"}
    _ecrire_tri(dossier, tri)


# Fragments attendus dans le message : chaque groupe est une liste
# d'alternatives acceptables (mots qui portent le sens, pas la phrase entière).
FRAGMENTS_REFUS = {
    "fichier_absent": [["lots.json"]],
    "json_illisible": [["lots.json"]],
    "schema_version_inconnue": [["version"]],
    "id_vide": [["id"]],
    "id_en_double": [["02"]],
    "id_avec_barre_oblique": [["02/bis"]],
    "unique_melee_a_d_autres_lots": [["unique"]],
    "allotissement_unique_mal_employe": [["03", "unique"]],
    "intitule_vide": [["intitul"]],
    "avis_hors_liste": [["avis"]],
    "raison_vide": [["raison"]],
    "partie_commune_inconnue": [["09"]],
    "piece_inconnue_chemin_proche": [["RC v2.pdf"], ["dce/RC.pdf"]],
    "deux_pieces_non_reparties": [["DPGF lot 05"], ["Plan L2 étage"]],
    "piece_lisible_declaree_illisible": [["RC.pdf"]],
    "type_manquant": [["CCAP"]],
    "type_hors_liste": [["RCAP", "dce/RC.pdf"]],
    "type_en_double_apres_normalisation": [["CCTP lot 02.pdf"]],
    # phrase imposée pour ce refus : l'agent ne choisit pas les lots
    "choix_ecrit_par_l_agent": [["Laisser le choix des lots vide"]],
}

CAS_REFUS = [
    ("fichier_absent", _cas_fichier_absent),
    ("json_illisible", _cas_json_illisible),
    ("schema_version_inconnue", _cas_schema_version_inconnue),
    ("id_vide", _cas_id_vide),
    ("id_en_double", _cas_id_en_double),
    ("id_avec_barre_oblique", _cas_id_avec_barre_oblique),
    ("unique_melee_a_d_autres_lots", _cas_unique_melee_a_d_autres_lots),
    ("allotissement_unique_mal_employe", _cas_allotissement_unique_mal_employe),
    ("intitule_vide", _cas_intitule_vide),
    ("avis_hors_liste", _cas_avis_hors_liste),
    ("raison_vide", _cas_raison_vide),
    ("partie_commune_inconnue", _cas_partie_commune_inconnue),
    ("piece_inconnue_chemin_proche", _cas_piece_inconnue_chemin_proche),
    ("deux_pieces_non_reparties", _cas_deux_pieces_non_reparties),
    ("piece_lisible_declaree_illisible", _cas_piece_lisible_declaree_illisible),
    ("type_manquant", _cas_type_manquant),
    ("type_hors_liste", _cas_type_hors_liste),
    ("type_en_double_apres_normalisation", _cas_type_en_double_apres_normalisation),
    ("choix_ecrit_par_l_agent", _cas_choix_ecrit_par_l_agent),
]


@pytest.mark.parametrize("nom,preparer", CAS_REFUS, ids=[c[0] for c in CAS_REFUS])
def test_enregistrer_refuse_et_ne_modifie_rien(tmp_path, capsys, nom, preparer):
    dossier = _dossier_alorti(tmp_path, capsys)
    preparer(dossier)
    avant = _contenus(dossier)
    capsys.readouterr()

    code = main(["lots", "enregistrer", "--dossier", str(dossier)])

    assert code != 0
    sorti = capsys.readouterr()
    message = sorti.out + sorti.err
    for groupe in FRAGMENTS_REFUS[nom]:
        assert any(f in message or f in message.lower() for f in groupe), \
            (nom, groupe, message)
    assert _contenus(dossier) == avant  # lots.json et 01-pieces.md inchangés


# ---------------------------------------------------------------------------
# 3. `lots enregistrer` — tolérance NFC et espaces multiples
# ---------------------------------------------------------------------------

def test_enregistrer_tolere_les_chemins_mal_normalises(tmp_path, capsys):
    dossier = _dossier_alorti(tmp_path, capsys)
    nfd = unicodedata.normalize("NFD", "dce/Plan L2 étage.pdf")
    tri = _tri_valide()
    tri["lots"][0]["pieces"] = ["dce/LOT  02/CCTP lot 02.pdf", nfd]
    tri["lots"][1]["pieces"] = ["dce/LOT 05/DPGF lot 05.xlsx", nfd]
    tri["types_pieces"]["dce/LOT  02/CCTP lot 02.pdf"] = "CCTP"
    _ecrire_tri(dossier, tri)

    assert main(["lots", "enregistrer", "--dossier", str(dossier)]) == 0
    capsys.readouterr()

    reecrit = (dossier / "memoire" / "lots.json").read_text(encoding="utf-8")
    assert "dce/LOT 02/CCTP lot 02.pdf" in reecrit   # chemin de l'inventaire
    assert "dce/LOT  02" not in reecrit              # double espace corrigé
    assert "dce/Plan L2 étage.pdf" in reecrit        # NFC de l'inventaire
    assert nfd not in reecrit                        # la forme NFD ne reste pas


# ---------------------------------------------------------------------------
# 4. `lots enregistrer` après un choix
# ---------------------------------------------------------------------------

def test_enregistrer_conserve_le_choix_quand_les_lots_retenus_restent(tmp_path, capsys):
    dossier = _dossier_choix_fait(tmp_path, capsys)
    choix_avant = _lecture_du_tri(dossier)["choix"]
    tri = _tri_valide()           # les lots 02 et 05 existent toujours
    tri["choix"] = choix_avant    # l'agent recopie le choix existant tel quel
    _ecrire_tri(dossier, tri)

    assert main(["lots", "enregistrer", "--dossier", str(dossier),
                 "--json"]) == 0
    sortie = json.loads(capsys.readouterr().out)
    assert sortie["choix"] == choix_avant
    assert _lecture_du_tri(dossier)["choix"] == choix_avant


def test_enregistrer_conserve_le_choix_enregistre_meme_si_l_agent_le_reecrit(
        tmp_path, capsys):
    """Le choix des lots vient du relevé de l'enregistrement : réécrire le tri
    avec un autre choix ne change rien, ni à la sortie, ni au fichier."""
    dossier = _dossier_choix_fait(tmp_path, capsys)
    vrai_choix = _lecture_du_tri(dossier)["choix"]
    tri = _tri_valide()           # les lots 02 et 05 existent toujours
    tri["choix"] = {"retenus": ["05"], "par": "Agent",
                    "date": "2026-11-23T10:00:00+00:00"}  # falsifié par l'agent
    _ecrire_tri(dossier, tri)

    assert main(["lots", "enregistrer", "--dossier", str(dossier),
                 "--json"]) == 0
    sortie = json.loads(capsys.readouterr().out)
    assert sortie["choix"] == vrai_choix
    assert _lecture_du_tri(dossier)["choix"] == vrai_choix


def test_enregistrer_remise_a_zero_du_choix_si_un_lot_retenu_disparait(tmp_path, capsys):
    dossier = _dossier_choix_fait(tmp_path, capsys)  # 02 et 05 retenus
    choix_avant = _lecture_du_tri(dossier)["choix"]
    tri = _tri_valide()
    tri["lots"] = [tri["lots"][0]]                   # le lot 05 disparaît
    tri["lots"][0]["pieces"].append("dce/LOT 05/DPGF lot 05.xlsx")
    tri["choix"] = choix_avant
    _ecrire_tri(dossier, tri)

    assert main(["lots", "enregistrer", "--dossier", str(dossier)]) == 0
    sorti = capsys.readouterr()
    message = sorti.out + sorti.err
    assert "05" in message                           # la sortie le dit
    assert "choix" in message.lower()
    assert _lecture_du_tri(dossier)["choix"] is None


# ---------------------------------------------------------------------------
# 5. `lots choisir`
# ---------------------------------------------------------------------------

def test_choisir_cree_les_analyses_et_ecrit_le_choix(tmp_path, capsys):
    dossier = _dossier_tri_enregistre(tmp_path, capsys)
    assert main(["lots", "choisir", "--lots", "02,05", "--par", "Camille",
                 "--dossier", str(dossier)]) == 0
    capsys.readouterr()

    attendu = [_rubrique_normalisee(t) for t in RUBRIQUES]
    for lot in ("02", "05"):
        analyse = dossier / "analyse" / f"lot-{lot}.md"
        texte = analyse.read_text(encoding="utf-8")
        assert _rubriques(texte) == attendu
        assert texte.count(MARQUEUR) >= 9
        contenu_json = json.loads(
            (dossier / "analyse" / f"lot-{lot}.json").read_text("utf-8"))
        assert contenu_json == {"questions_acheteur": []}

    tri = _lecture_du_tri(dossier)
    assert tri["choix"]["retenus"] == ["02", "05"]  # dans l'ordre donné
    assert tri["choix"]["par"] == "Camille"
    date = tri["choix"]["date"]
    instant = datetime.datetime.fromisoformat(
        date[:-1] + "+00:00" if date.endswith("Z") else date)
    assert instant.utcoffset() == datetime.timedelta(0)  # ISO 8601 UTC


def test_choisir_accepte_le_numero_sans_zero_de_garde(tmp_path, capsys):
    dossier = _dossier_tri_enregistre(tmp_path, capsys)
    assert main(["lots", "choisir", "--lots", "2", "--par", "Camille",
                 "--dossier", str(dossier)]) == 0
    capsys.readouterr()
    assert _lecture_du_tri(dossier)["choix"]["retenus"] == ["02"]


def test_choisir_conserve_l_ordre_donne_et_tolere_les_espaces(tmp_path, capsys):
    dossier = _dossier_tri_enregistre(tmp_path, capsys)
    assert main(["lots", "choisir", "--lots", "05, 02", "--par", "Camille",
                 "--dossier", str(dossier)]) == 0
    capsys.readouterr()
    assert _lecture_du_tri(dossier)["choix"]["retenus"] == ["05", "02"]


def test_choisir_ne_ecrase_jamais_une_analyse_remplie(tmp_path, capsys):
    dossier = _dossier_tri_enregistre(tmp_path, capsys)
    assert main(["lots", "choisir", "--lots", "02", "--par", "Camille",
                 "--dossier", str(dossier)]) == 0
    capsys.readouterr()
    chemin_md = dossier / "analyse" / "lot-02.md"
    chemin_json = dossier / "analyse" / "lot-02.json"
    contenu_md = "## En bref\n\nAnalyse déjà rédigée par l'équipe.\n"
    chemin_md.write_text(contenu_md, encoding="utf-8")
    chemin_json.write_text(
        '{"questions_acheteur": [{"id": "I-1", "question": '
        '"Un délai supplémentaire est-il possible ?"}]}\n',
        encoding="utf-8")

    assert main(["lots", "choisir", "--lots", "02,05", "--par", "Camille",
                 "--dossier", str(dossier)]) == 0
    capsys.readouterr()

    assert chemin_md.read_text(encoding="utf-8") == contenu_md
    questions = json.loads(chemin_json.read_text("utf-8"))["questions_acheteur"]
    assert questions[0]["id"] == "I-1"


CAS_REFUS_CHOISIR = [
    ("lot_inconnu", "02,07", "Camille",
     [["Lot inconnu : 07"], ["Lots du DCE : 02, 05"]]),
    ("doublon", "02,02", "Camille", [["02"]]),
    ("liste_vide", "", "Camille", [["lots"]]),
    ("par_vide", "02", "", [["par", "nom"]]),
]


@pytest.mark.parametrize("nom,lots,par,fragments", CAS_REFUS_CHOISIR,
                         ids=[c[0] for c in CAS_REFUS_CHOISIR])
def test_choisir_refuse_et_ne_cree_rien(tmp_path, capsys, nom, lots, par, fragments):
    dossier = _dossier_tri_enregistre(tmp_path, capsys)
    avant = _contenus(dossier)
    capsys.readouterr()

    code = main(["lots", "choisir", "--lots", lots, "--par", par,
                 "--dossier", str(dossier)])

    assert code != 0
    sorti = capsys.readouterr()
    message = sorti.out + sorti.err
    for groupe in fragments:
        assert any(f in message or f in message.lower() for f in groupe), \
            (nom, groupe, message)
    assert _contenus(dossier) == avant
    assert not (dossier / "analyse" / "lot-02.md").exists()


def test_choisir_exige_un_tri_enregistre(tmp_path, capsys):
    dossier = _dossier_alorti(tmp_path, capsys)  # pas de memoire/lots.json
    capsys.readouterr()
    code = main(["lots", "choisir", "--lots", "02", "--par", "Camille",
                 "--dossier", str(dossier)])
    assert code != 0
    sorti = capsys.readouterr()
    message = sorti.out + sorti.err
    assert "tri" in message.lower() or "lots.json" in message
    assert not (dossier / "analyse" / "lot-02.md").exists()
    assert not (dossier / "memoire" / "lots.json").exists()


def test_choisir_garde_les_analyses_du_lot_retire(tmp_path, capsys):
    dossier = _dossier_choix_fait(tmp_path, capsys)  # 02 et 05 retenus
    assert (dossier / "analyse" / "lot-05.md").exists()
    marque = "Analyse du lot 05 déjà rédigée avant son retrait (fictif)."
    (dossier / "analyse" / "lot-05.md").write_text(marque, encoding="utf-8")
    (dossier / "analyse" / "lot-05.json").write_text(
        json.dumps({"questions_acheteur": _question()}, ensure_ascii=False),
        encoding="utf-8")

    tri = _tri_valide()
    tri["lots"] = [tri["lots"][0]]                   # nouveau tri sans le 05
    tri["lots"][0]["pieces"].append("dce/LOT 05/DPGF lot 05.xlsx")
    _ecrire_tri(dossier, tri)
    assert main(["lots", "enregistrer", "--dossier", str(dossier)]) == 0
    capsys.readouterr()
    assert main(["lots", "choisir", "--lots", "02", "--par", "Camille",
                 "--dossier", str(dossier)]) == 0
    capsys.readouterr()

    # les fichiers du lot retiré restent sur le disque, tels que rédigés :
    # le choix suivant ne les remet pas au gabarit
    contenu_05 = (dossier / "analyse" / "lot-05.md").read_text("utf-8")
    assert marque in contenu_05
    assert MARQUEUR not in contenu_05
    questions = json.loads(
        (dossier / "analyse" / "lot-05.json").read_text("utf-8"))
    assert questions["questions_acheteur"][0]["id"] == "I-1"


def test_choisir_marche_non_alloti_avec_le_lot_unique(tmp_path, capsys):
    source = tmp_path / "DCE"
    source.mkdir()
    ecrire_pdf(source / "RC.pdf", [
        "Reglement de la consultation du marche",
        "Le marche n'est pas alloti.",
    ])
    ecrire_pdf(source / "CCTP.pdf", [
        "Cahier des clauses techniques particulieres",
        "La prestation couvre l'ensemble du marche.",
    ])
    dossier = tmp_path / "reponse"
    assert main(["init", str(source), "--dossier", str(dossier)]) == 0
    capsys.readouterr()

    tri = {
        "schema_version": 1,
        "allotissement": "unique",
        "lots": [{
            "id": "unique",
            "intitule": "Prestation unique",
            "pieces": ["dce/CCTP.pdf"],
            "parties_communes": [],
            "recommandation": {"avis": "repondre", "raison": "Dans le métier."},
        }],
        "pieces_communes": ["dce/RC.pdf"],
        "pieces_illisibles": [],
        "types_pieces": {"dce/RC.pdf": "RC", "dce/CCTP.pdf": "CCTP"},
        "choix": None,
    }
    _ecrire_tri(dossier, tri)
    assert main(["lots", "enregistrer", "--dossier", str(dossier)]) == 0
    capsys.readouterr()

    assert main(["lots", "choisir", "--lots", "unique", "--par", "Camille",
                 "--dossier", str(dossier)]) == 0
    capsys.readouterr()
    assert (dossier / "analyse" / "lot-unique.md").exists()
    assert _lecture_du_tri(dossier)["choix"]["retenus"] == ["unique"]


# ---------------------------------------------------------------------------
# 6. `lots rapport`
# ---------------------------------------------------------------------------

def test_rapport_ecrit_la_page_et_le_recueil_des_questions(tmp_path, capsys):
    dossier = _dossier_choix_fait(tmp_path, capsys)
    questions_02 = _questions_conformes(2)
    _analyse_faite(dossier, "02", questions_02)
    _analyse_faite(dossier, "05")

    assert main(["lots", "rapport", "--dossier", str(dossier)]) == 0
    capsys.readouterr()

    page = dossier / "memoire" / "rapport-lots.html"
    assert page.exists()
    html = page.read_text(encoding="utf-8")
    assert "Électricité courants forts" in html      # intitulé du lot 02
    assert "Courants faibles" in html                # intitulé du lot 05
    assert "Dérive possible du périmètre." in html   # raison du lot 05
    assert "Camille" in html                          # qui a choisi
    assert "RC.pdf" in html and "CCAP.pdf" in html    # pièces communes
    assert "analyse en cours" not in html             # analyses faites

    questions = dossier / "memoire" / "lots-analyses.json"
    assert questions.exists()
    recueil = json.loads(questions.read_text("utf-8"))
    assert set(recueil["lots"]) == {"02", "05"}
    assert recueil["lots"]["02"]["questions_acheteur"] == questions_02

    # contexte puis question, dans cet ordre
    premiere = questions_02[0]
    assert premiere["contexte"] in html
    assert premiere["question"] in html
    assert html.index(premiere["contexte"]) < html.index(premiere["question"])


def _probleme_rubrique_manquante(dossier: Path) -> None:
    texte = "\n\n".join(
        f"## {titre}\n\nRédigé." for titre in RUBRIQUES if titre != "Avis") + "\n"
    (dossier / "analyse" / "lot-02.md").write_text(texte, encoding="utf-8")


def _probleme_rubrique_hors_ordre(dossier: Path) -> None:
    titres = list(RUBRIQUES)
    titres[0], titres[1] = titres[1], titres[0]
    texte = "\n\n".join(f"## {t}\n\nRédigé." for t in titres) + "\n"
    (dossier / "analyse" / "lot-02.md").write_text(texte, encoding="utf-8")


def _probleme_marqueur_restant(dossier: Path) -> None:
    texte = _analyse_texte() + "\n" + MARQUEUR + "\n"
    (dossier / "analyse" / "lot-02.md").write_text(texte, encoding="utf-8")


def _probleme_json_illisible(dossier: Path) -> None:
    _analyse_faite(dossier, "02")
    (dossier / "analyse" / "lot-02.json").write_text("{oops", encoding="utf-8")


def _probleme_question(non_conforme: dict):
    def preparer(dossier: Path) -> None:
        _analyse_faite(dossier, "02", non_conforme)
    return preparer


CAS_PROBLEMES = [
    ("rubrique_manquante", _probleme_rubrique_manquante),
    ("rubrique_hors_ordre", _probleme_rubrique_hors_ordre),
    ("marqueur_restant", _probleme_marqueur_restant),
    ("json_illisible", _probleme_json_illisible),
    ("question_sans_point_d_interrogation", _probleme_question(
        _question(question="Pouvez-vous confirmer le nombre de prises"))),
    ("sources_vides", _probleme_question(_question(sources=[]))),
    ("impact_prix_vide", _probleme_question(_question(impact_prix=""))),
    ("id_hors_format", _probleme_question(_question(id="Q1"))),
    ("id_en_double", _probleme_question(_question() + _question())),
    ("fragment_fichier_md", _probleme_question(_question(
        question="Le dossier analyse/lot-02.md impose-t-il une visite ?"))),
    ("fragment_chemin_dce", _probleme_question(_question(
        question="Les pièces sous dce/RC.pdf doivent-elles être relues ?"))),
    ("fragment_chemin_windows_dans_le_contexte", _probleme_question(_question(
        contexte="Le CCTP renvoie à dce\\RC.pdf pour les prescriptions."))),
    ("fragment_chemin_windows_dans_la_question", _probleme_question(_question(
        question="Les prescriptions de analyse\\support.pdf s'appliquent-elles "
                 "au lot ?"))),
    ("fragment_chemin_windows_dans_les_sources", _probleme_question(_question(
        sources=["CCTP article 4.2", "dce\\LOT 02\\CCTP lot 02.pdf"]))),
    ("fragment_commande_remporte", _probleme_question(_question(
        question="Faut-il lancer remporte etat avant la remise ?"))),
]


@pytest.mark.parametrize("nom,preparer", CAS_PROBLEMES,
                         ids=[c[0] for c in CAS_PROBLEMES])
def test_rapport_liste_les_problemes_sans_bloquer(tmp_path, capsys, nom, preparer):
    dossier = _dossier_choix_fait(tmp_path, capsys)
    preparer(dossier)
    _analyse_faite(dossier, "05")  # lot 05 : analyse conforme, donc prête
    capsys.readouterr()

    assert main(["lots", "rapport", "--dossier", str(dossier), "--json"]) == 0
    sortie = json.loads(capsys.readouterr().out)
    assert sortie["ok"] is True
    # le problème du lot 02 est listé, sans bloquer la page
    assert "02" in json.dumps(sortie.get("problemes")), sortie.get("problemes")
    page = (dossier / "memoire" / "rapport-lots.html").read_text(encoding="utf-8")
    # l'état annoncé est celui du lot nommé : le lot à problème reste
    # « en cours », le lot conforme est bien « prête »
    assert "Lot 02 – analyse en cours" in page, page
    assert "Lot 02 – analyse prête" not in page
    assert "Lot 05 – analyse prête" in page
    assert "Lot 05 – analyse en cours" not in page


def test_rapport_recueil_sans_le_json_illisible(tmp_path, capsys):
    dossier = _dossier_choix_fait(tmp_path, capsys)
    _probleme_json_illisible(dossier)
    capsys.readouterr()

    assert main(["lots", "rapport", "--dossier", str(dossier)]) == 0
    capsys.readouterr()
    recueil = json.loads(
        (dossier / "memoire" / "lots-analyses.json").read_text("utf-8"))
    # seul le lot 05 a un JSON lisible
    assert set(recueil["lots"]) == {"05"}


def test_rapport_ouvrir_appelle_le_navigateur_avec_l_uri(tmp_path, monkeypatch, capsys):
    dossier = _dossier_choix_fait(tmp_path, capsys)
    appels: list[str] = []
    monkeypatch.setattr(webbrowser, "open", lambda uri: appels.append(uri) or True)
    assert main(["lots", "rapport", "--dossier", str(dossier), "--ouvrir"]) == 0
    capsys.readouterr()
    assert len(appels) == 1
    assert appels[0].startswith("file://")
    assert appels[0].endswith("rapport-lots.html")


def test_rapport_sans_ouvrir_n_appelle_pas_le_navigateur(tmp_path, monkeypatch, capsys):
    dossier = _dossier_choix_fait(tmp_path, capsys)
    appels: list[str] = []
    monkeypatch.setattr(webbrowser, "open", lambda uri: appels.append(uri) or True)
    assert main(["lots", "rapport", "--dossier", str(dossier)]) == 0
    capsys.readouterr()
    assert appels == []


def test_rapport_ouvrir_quand_le_navigateur_refuse_dit_la_page_a_ouvrir(
        tmp_path, monkeypatch, capsys):
    """Si `webbrowser.open` rend False, la commande réussit, la page reste
    publiée et la sortie dit où elle est (« Page à ouvrir », `ouverte: false`
    en JSON). Simulation : webbrowser.open est remplacé."""
    dossier = _dossier_choix_fait(tmp_path, capsys)
    appels: list[str] = []

    def refuser(uri: str) -> bool:
        appels.append(uri)
        return False

    monkeypatch.setattr(webbrowser, "open", refuser)
    assert main(["lots", "rapport", "--dossier", str(dossier), "--ouvrir",
                 "--json"]) == 0
    sortie = json.loads(capsys.readouterr().out)
    assert sortie["ok"] is True
    assert sortie["ouverte"] is False
    texte = json.dumps(sortie, ensure_ascii=False)
    assert "Page à ouvrir" in texte, texte
    assert "rapport-lots.html" in texte, texte
    assert appels  # le navigateur a bien été sollicité
    assert (dossier / "memoire" / "rapport-lots.html").is_file()


def test_rapport_ouvrir_quand_le_navigateur_echoue_dit_la_page_a_ouvrir(
        tmp_path, monkeypatch, capsys):
    """Si `webbrowser.open` lève une erreur, la commande réussit quand même et
    dit la page à ouvrir. Simulation : webbrowser.open est remplacé."""
    dossier = _dossier_choix_fait(tmp_path, capsys)

    def exploser(uri: str) -> bool:
        raise RuntimeError("aucun navigateur disponible")

    monkeypatch.setattr(webbrowser, "open", exploser)
    assert main(["lots", "rapport", "--dossier", str(dossier), "--ouvrir"]) == 0
    sortie = capsys.readouterr()
    assert "Page à ouvrir" in sortie.out, sortie
    assert "rapport-lots.html" in sortie.out, sortie
    assert (dossier / "memoire" / "rapport-lots.html").is_file()


# ---------------------------------------------------------------------------
# nombres hors norme (NaN, Infinity, -Infinity) à l'entrée, sortie JSON stricte
# ---------------------------------------------------------------------------

def _refuser_constante(x: str):
    raise AssertionError(f"constante JSON hors norme dans la sortie : {x}")


@pytest.mark.parametrize("litteral", ["NaN", "Infinity", "-Infinity"])
def test_enregistrer_refuse_les_nombres_hors_norme_du_tri(tmp_path, capsys, litteral):
    """Un nombre NaN/Infinity/-Infinity du tri est refusé à la lecture : la
    commande échoue sans rien modifier, et même sa sortie d'erreur reste du
    JSON strict (aucune constante hors norme n'y revient)."""
    dossier = _dossier_alorti(tmp_path, capsys)
    brut = json.dumps(_tri_valide(), ensure_ascii=False)
    brut = brut.replace('"choix": null', f'"choix": null, "controle": {litteral}')
    _ecrire_tri(dossier, brut=brut)
    avant = _contenus(dossier)
    capsys.readouterr()

    assert main(["lots", "enregistrer", "--dossier", str(dossier), "--json"]) != 0
    sorti = capsys.readouterr()
    objet = json.loads(sorti.out, parse_constant=_refuser_constante)
    message = json.dumps(objet, ensure_ascii=False)
    assert "lots.json" in message, message
    assert "nombres valides" in message, message
    assert _contenus(dossier) == avant


def test_rapport_signale_les_nombres_hors_norme_de_l_analyse(tmp_path, capsys):
    """Un Infinity dans analyse/lot-02.json est refusé à la lecture : le lot
    est signalé en analyse en cours avec le conseil d'enregistrer le fichier
    avec des nombres valides, sans bloquer le rapport du lot conforme."""
    dossier = _dossier_choix_fait(tmp_path, capsys)
    _analyse_faite(dossier, "02")
    (dossier / "analyse" / "lot-02.json").write_text(
        '{"questions_acheteur": [{"id": "I-1", '
        '"contexte": "Deux pièces du lot donnent des valeurs différentes.", '
        '"question": "Quelle valeur retenir ?", '
        '"sources": ["CCTP article 4.2"], "impact_prix": Infinity}]}\n',
        encoding="utf-8")
    _analyse_faite(dossier, "05", _questions_conformes(1))
    capsys.readouterr()

    assert main(["lots", "rapport", "--dossier", str(dossier), "--json"]) == 0
    sorti = capsys.readouterr()
    sortie = json.loads(sorti.out, parse_constant=_refuser_constante)
    assert sortie["ok"] is True
    problemes = json.dumps(sortie.get("problemes"), ensure_ascii=False)
    assert "lot-02.json" in problemes, problemes
    assert "nombres valides" in problemes, problemes
    page = (dossier / "memoire" / "rapport-lots.html").read_text(encoding="utf-8")
    assert "Lot 02 – analyse en cours" in page, page
    assert "Lot 05 – analyse prête" in page, page


def test_rapport_exige_un_tri_enregistre(tmp_path, capsys):
    dossier = _dossier_alorti(tmp_path, capsys)  # pas de memoire/lots.json
    capsys.readouterr()
    code = main(["lots", "rapport", "--dossier", str(dossier)])
    assert code != 0
    sorti = capsys.readouterr()
    message = sorti.out + sorti.err
    assert "tri" in message.lower() or "lots.json" in message
    assert not (dossier / "memoire" / "rapport-lots.html").exists()


# ---------------------------------------------------------------------------
# 7. `etat` — libellés de l'étape analyse
# ---------------------------------------------------------------------------

def test_etat_tri_absent_annonce_la_repartition_par_lot(tmp_path, capsys):
    dossier = _dossier_alorti(tmp_path, capsys)
    capsys.readouterr()
    assert main(["etat", "--dossier", str(dossier)]) == 0
    sortie = capsys.readouterr().out
    assert "Analyse : lire le DCE et répartir les pièces par lot." in sortie
    assert "analyse_a_lancer" not in sortie
    assert "schema_version" not in sortie
    assert '"lots"' not in sortie


def test_etat_tri_sans_choix_annonce_les_lots_a_choisir(tmp_path, capsys):
    dossier = _dossier_tri_enregistre(tmp_path, capsys)
    assert main(["etat", "--dossier", str(dossier)]) == 0
    sortie = capsys.readouterr().out
    assert "Analyse : lots à choisir (02, 05)." in sortie
    assert "analyse_a_lancer" not in sortie


def test_etat_apres_choix_libelle_par_lot(tmp_path, capsys):
    dossier = _dossier_choix_fait(tmp_path, capsys)
    _analyse_faite(dossier, "02", _questions_conformes(3))
    assert main(["etat", "--dossier", str(dossier)]) == 0
    sortie = capsys.readouterr().out.replace("\u2019", "'")
    assert "Analyse : lots retenus 02, 05" in sortie
    message_attendu = ("Analyse : lots retenus 02, 05 — "
                       "lot 02 prête (3 questions à l'acheteur), lot 05 en cours.")
    assert message_attendu in sortie.replace("\u2019", "'")
    assert "analyse_a_lancer" not in sortie

    assert main(["etat", "--dossier", str(dossier), "--json"]) == 0
    donnees = json.loads(capsys.readouterr().out)
    assert "lots" in donnees
    # le même état, structuré : pas un résumé vide sous cette clé
    etat_lots = donnees["lots"]
    assert isinstance(etat_lots, dict) and etat_lots
    assert etat_lots["message"].replace("\u2019", "'") == message_attendu


def test_etat_dossier_ancien_annonce_la_reprise_par_lot(tmp_path, capsys):
    dossier = _dossier_alorti(tmp_path, capsys)
    (dossier / "02-analyse.md").write_text(
        "# Analyse du DCE\n\nAncienne note de travail.\n", encoding="utf-8")
    capsys.readouterr()
    assert main(["etat", "--dossier", str(dossier)]) == 0
    sortie = capsys.readouterr().out
    assert "Analyse à refaire par lot" in sortie
    assert "analyse_a_lancer" not in sortie


# ---------------------------------------------------------------------------
# 8. `init` — plus de déduction du lot par le nom
# ---------------------------------------------------------------------------

def test_init_ne_deduit_plus_le_lot_du_nom(tmp_path, capsys):
    source = tmp_path / "DCE"
    source.mkdir()
    fabriquer_docx(source / "RC.docx")
    ecrire_pdf(source / "Plan L2 étage.pdf",
               ["Plan d execution de l etage 2 du batiment A."])
    ecrire_pdf(source / "CCTP_LOT02.pdf", [
        "Cahier des clauses techniques particulieres",
        "Le lot 02 couvre l electricite courants forts.",
    ])
    fabriquer_docx(source / "AE lot 5.docx")
    dossier = tmp_path / "reponse"
    assert main(["init", str(source), "--dossier", str(dossier)]) == 0
    capsys.readouterr()

    inventaire = (dossier / "01-pieces.md").read_text(encoding="utf-8")
    for chemin in ("dce/Plan L2 étage.pdf", "dce/CCTP_LOT02.pdf",
                   "dce/AE lot 5.docx"):
        ligne = next(l for l in inventaire.splitlines() if chemin in l)
        assert "| — | `dce/" in ligne, ligne

    assert not (dossier / "02-analyse.md").exists()
    assert (dossier / "memoire").is_dir()
    assert (dossier / "analyse").is_dir()
