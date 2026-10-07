"""Le plugin Claude Code reste conforme aux contrôles de l'annuaire Claude."""

import json
import re
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
PLUGIN = RACINE / "plugin"


def test_marketplace_pointe_sur_le_dossier_plugin():
    marketplace = json.loads((RACINE / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    (entree,) = marketplace["plugins"]
    assert entree["source"] == "./plugin"
    assert (PLUGIN / ".claude-plugin" / "plugin.json").is_file()


def test_versions_alignees():
    manifeste = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    projet = (RACINE / "pyproject.toml").read_text(encoding="utf-8")
    assert f'version = "{manifeste["version"]}"' in projet
    for champ in ("name", "description", "author", "license", "homepage", "repository"):
        assert manifeste.get(champ), champ


def test_fichiers_lisibles_par_le_controle_automatique():
    fichiers = [p for p in PLUGIN.rglob("*") if p.is_file() or p.is_symlink()]
    assert len(fichiers) <= 512
    for fichier in fichiers:
        assert not fichier.is_symlink(), fichier
        assert fichier.name not in {".DS_Store", "Thumbs.db", "desktop.ini"}, fichier
        assert fichier.suffix in {".md", ".json", ""}, fichier
        assert fichier.stat().st_size < 256 * 1024, fichier


def test_skills_et_agents_sans_renvoi_vers_l_offre():
    for fichier in [*PLUGIN.glob("skills/*/SKILL.md"), *PLUGIN.glob("agents/*.md")]:
        assert "remporte.fr" not in fichier.read_text(encoding="utf-8"), fichier


def test_readme_du_plugin():
    texte = (PLUGIN / "README.md").read_text(encoding="utf-8")
    hors_code = re.sub(r"```.*?```", "", texte, flags=re.S)
    assert len(hors_code.split()) >= 40
    exemples = texte.split("## Exemples", 1)[1].split("\n## ", 1)[0]
    assert exemples.count("\n- ") >= 3
    assert (PLUGIN / "LICENSE").read_text(encoding="utf-8") == (RACINE / "LICENSE").read_text(encoding="utf-8")
