"""Robustesse du plugin : en-têtes YAML stricts, fiches de sous-agents autonomes, mise en route sans uv, noms interdits.

Trois défauts attendus (rouges aujourd'hui) :
- 1.1 : plusieurs en-têtes de SKILL.md se lisent avec Claude Code mais sont refusés
  par un lecteur YAML strict (`yaml.safe_load`), à cause de descriptions non
  quotées qui contiennent « : ».
- 1.5 : les fiches de sous-agents renvoient leur procédure par un lien relatif
  `../references/` et la variable `CLAUDE_PLUGIN_ROOT`, que le sous-agent ne
  résout pas, et ne disent pas quoi faire si `remporte` manque du `PATH`.
- 1.8 : quand `remporte` n'est pas installée et que `uv` manque, la skill de
  mise en route ne propose pas d'installer uv elle-même après accord.

Et un garde-fou vert : aucun nom de client dans le dépôt. Les noms ne sont
connus de ce fichier que par leur empreinte SHA-256.
"""

import hashlib
import importlib.util
import re
import subprocess
import zipfile
from pathlib import Path

import pytest
import yaml

RACINE = Path(__file__).resolve().parent.parent
PLUGIN = RACINE / "plugin"

spec = importlib.util.spec_from_file_location("package_plugin", RACINE / "scripts" / "package_plugin.py")
packager = importlib.util.module_from_spec(spec)
spec.loader.exec_module(packager)

FICHES = sorted(PLUGIN.glob("skills/*/SKILL.md")) + sorted(PLUGIN.glob("agents/*.md"))

# 1.5 — Pour chaque sous-agent, la procédure à porter en clair dans la fiche et les
# marqueurs choisis. Ces marqueurs sont des règles métier et des commandes du CLI
# tirées de plugin/references/<procédure>.md : ce sont les invariants de la
# procédure (commandes à lancer, fichiers à écrire, interdits), pas des
# formulations quelconques, donc ils restent stables quand la procédure est
# recopiée ou reformulée légèrement.
PROCEDURES = {
    "lecteur-dce": (
        "lecture-dce.md",
        [
            "remporte fiche",
            "non précisé dans le DCE",
            "Ne lis jamais un CCTP d'un bloc",
        ],
    ),
    "redacteur-section": (
        "redaction-section.md",
        [
            "remporte guide redaction",
            "remporte base chercher",
            "[à compléter",
            "Ne coche pas le plan",
        ],
    ),
    "relecteur": (
        "relecture-ao.md",
        [
            "remporte guide relecture",
            "remporte cadre --couverture",
            "05-relecture.md",
            "Ne modifie aucune section",
        ],
    ),
}


def _en_tete(texte, origine):
    """Renvoie l'en-tête YAML d'une fiche, lu strictement."""
    assert texte.startswith("---\n"), f"{origine} : pas de front matter"
    fin = texte.find("\n---\n", 4)
    assert fin != -1, f"{origine} : front matter non fermé"
    return yaml.safe_load(texte[4:fin])


def _en_tete_verifiee(texte, origine):
    en_tete = _en_tete(texte, origine)
    assert isinstance(en_tete, dict), origine
    assert str(en_tete.get("name") or "").strip(), origine
    assert str(en_tete.get("description") or "").strip(), origine
    return en_tete


# 1.1 — chaque en-tête se lit avec un lecteur YAML strict et porte name et description.


@pytest.mark.parametrize("fiche", FICHES, ids=lambda p: p.relative_to(PLUGIN).as_posix())
def test_en_tete_de_fiche_lisible_par_un_lecteur_yaml_strict(fiche):
    _en_tete_verifiee(fiche.read_text(encoding="utf-8"), fiche.relative_to(PLUGIN).as_posix())


@pytest.mark.parametrize("plateforme", ["claude", "openai"])
def test_en_tetes_des_archives_de_plateforme_lisibles_par_un_lecteur_yaml_strict(tmp_path, plateforme):
    archive = tmp_path / f"{plateforme}.zip"
    packager.package_plugin(plateforme, archive)
    with zipfile.ZipFile(archive) as contenue:
        cibles = [
            nom for nom in contenue.namelist()
            if nom.endswith("/SKILL.md") or re.fullmatch(r"remporte/agents/[a-z-]+\.md", nom)
        ]
        assert cibles, plateforme
        for nom in sorted(cibles):
            _en_tete_verifiee(contenue.read(nom).decode("utf-8"), f"{plateforme}:{nom}")


# 1.5 — chaque fiche de sous-agent porte sa procédure en clair et sait quoi faire
# quand la commande remporte n'est pas dans le PATH.


@pytest.mark.parametrize("agent", sorted(PROCEDURES))
def test_la_fiche_du_sous_agent_porte_sa_procedure_en_clair(agent):
    reference, marqueurs = PROCEDURES[agent]
    fiche = (PLUGIN / "agents" / f"{agent}.md").read_text(encoding="utf-8")
    assert "../references/" not in fiche, agent
    assert "CLAUDE_PLUGIN_ROOT" not in fiche, agent
    procedure = (PLUGIN / "references" / reference).read_text(encoding="utf-8")
    for marqueur in marqueurs:
        assert marqueur in procedure, (reference, marqueur, "marqueur obsolète : corrige le test")
        assert marqueur in fiche, (agent, marqueur)


@pytest.mark.parametrize("agent", sorted(PROCEDURES))
def test_la_fiche_du_sous_agent_sait_faire_sans_remporte_dans_le_path(agent):
    fiche = (PLUGIN / "agents" / f"{agent}.md").read_text(encoding="utf-8")
    assert "~/.local/bin/remporte" in fiche, agent
    assert r"%USERPROFILE%\.local\bin\remporte.exe" in fiche, agent
    assert "compte rendu" in fiche.lower(), agent


# 1.8 — la skill de mise en route (init) installe uv elle-même, après accord de
# l'utilisateur et sans droits administrateur.


def _cas_uv_absent():
    """Fenêtre du texte d'init qui décrit le cas d'un uv absent.

    On part de la première mention de l'absence d'uv dans la skill et on garde
    tout ce qui suit jusqu'à la fin de la section : c'est là que vivent la
    proposition, l'accord demandé et les commandes d'installation.
    """
    texte = (PLUGIN / "skills" / "init" / "SKILL.md").read_text(encoding="utf-8")
    sections = [s for s in texte.split("\n## ") if "uv" in s and "absent" in s]
    assert sections, "la skill de mise en route (init) ne décrit pas le cas d'un uv absent"
    section = sections[0]
    return section[max(0, section.index("absent") - 20):]


def test_la_mise_en_route_propose_d_installer_uv():
    fenetre = _cas_uv_absent()
    assert "https://astral.sh/uv/install.sh" in fenetre, "pas de commande macOS/Linux"
    assert "https://astral.sh/uv/install.ps1" in fenetre, "pas de commande Windows PowerShell"


def test_la_mise_en_route_attend_l_accord_avant_d_installer_uv():
    fenetre = _cas_uv_absent()
    accord = fenetre.find("accord")
    assert accord != -1, "aucun accord demandé dans le cas d'un uv absent"
    commande = fenetre.find("astral.sh/uv/install.sh")
    assert commande != -1, "pas de commande d'installation à accorder"
    assert accord < commande, "l'accord doit être demandé avant de lancer l'installateur"


def test_l_installation_d_uv_ne_demande_pas_de_droits_administrateur():
    fenetre = _cas_uv_absent()
    assert "~/.local/bin" in fenetre, "l'installateur doit viser le dossier de l'utilisateur"
    assert re.search(r"administrateur", fenetre, re.I), "l'absence de droits requis doit être dite"


# Garde-fou vert — aucun nom de client dans le dépôt. Chaque mot des fichiers
# suivis par git est comparé, en minuscules, à des empreintes SHA-256 : le nom
# lui-même n'est écrit nulle part. Les données binaires en data-URI (polices
# embarquées) sont neutralisées avant la lecture des mots.

EMPREINTES_INTERDITES = {
    "313ce7d71787960e3bb5f8258c173ae466b4e08e1e7d24b9c7a5ba81c9a02d96",
    "038439e692b8af4000ab141a3082cbb9a016ec4f32c13b0e756c563fbec661e7",
}
CHEMINS_SURVEILLES = ("src", "docs", "plugin", "tests", "scripts", "README.md", "PRIVACY.md")


def _empreinte(mot):
    return hashlib.sha256(mot.lower().encode("utf-8")).hexdigest()


def _mentions_interdites(racine, empreintes=EMPREINTES_INTERDITES, chemins=CHEMINS_SURVEILLES):
    commande = ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"]
    if chemins:
        commande += ["--", *chemins]
    resultat = subprocess.run(commande, cwd=racine, capture_output=True, check=True)
    mentions = []
    for nom in filter(None, resultat.stdout.decode("utf-8").split("\0")):
        fichier = Path(racine) / nom
        if not fichier.is_file():
            continue
        try:
            texte = fichier.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for numero, ligne in enumerate(texte.splitlines(), 1):
            ligne = re.sub(r"(data:[^;,]+;base64,)[A-Za-z0-9+/=]+", r"\1", ligne)
            for mot in re.findall(r"\w+", ligne):
                if _empreinte(mot) in empreintes:
                    mentions.append(f"{nom}:{numero}:{mot}")
    return mentions


def test_aucun_nom_de_client_dans_le_depot():
    mentions = _mentions_interdites(RACINE)
    assert not mentions, "Mentions à retirer :\n" + "\n".join(mentions)


def test_le_garde_fou_detecte_un_nom_en_clair(tmp_path):
    """Preuve que le garde-fou peut échouer : sur un dépôt jetable, un nom dont
    l'empreinte est interdite est repéré, y compris en majuscules ; le même mot
    noyé dans une police embarquée ne l'est pas."""
    mot = "Exemplenom"
    empreintes = {_empreinte(mot)}
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    fichier = tmp_path / "page.html"
    police = f"<style>@font-face{{src:url(data:font/woff2;base64,AA{mot}AA)}}</style>"
    fichier.write_text(police + "\n", encoding="utf-8")
    assert _mentions_interdites(tmp_path, empreintes, chemins=()) == []
    fichier.write_text(police + f"<p>{mot.upper()}</p>\n", encoding="utf-8")
    assert _mentions_interdites(tmp_path, empreintes, chemins=()) == [f"page.html:1:{mot.upper()}"]
