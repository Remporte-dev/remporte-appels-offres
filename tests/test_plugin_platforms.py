"""La source commune produit deux archives natives sans perdre les procédures."""

import importlib.util
import json
from pathlib import Path
import re
import zipfile

import pytest

ROOT = Path(__file__).resolve().parent.parent
PLUGIN = ROOT / "plugin"
spec = importlib.util.spec_from_file_location("package_plugin", ROOT / "scripts/package_plugin.py")
packager = importlib.util.module_from_spec(spec)
spec.loader.exec_module(packager)


def test_identite_et_versions_des_trois_manifests():
    claude = json.loads((PLUGIN / ".claude-plugin/plugin.json").read_text(encoding="utf-8"))
    codex = json.loads((PLUGIN / ".codex-plugin/plugin.json").read_text(encoding="utf-8"))
    portable = json.loads((PLUGIN / "plugin.json").read_text(encoding="utf-8"))
    for field in ("name", "version", "description", "author", "license", "repository"):
        assert claude[field] == codex[field] == portable[field]
    assert portable["extensions"]["com.openai"]["interface"] == codex["interface"]
    assert len(codex["interface"]["shortDescription"]) <= 30
    assert (PLUGIN / codex["skills"]).is_dir()


def test_les_deux_catalogues_pointent_sur_la_meme_source():
    native = json.loads((ROOT / ".agents/plugins/marketplace.json").read_text(encoding="utf-8"))
    claude = json.loads((ROOT / ".claude-plugin/marketplace.json").read_text(encoding="utf-8"))
    assert native["plugins"][0]["source"]["path"] == claude["plugins"][0]["source"]
    assert native["plugins"][0]["policy"]["installation"] == "AVAILABLE"


@pytest.mark.parametrize("platform", ["claude", "openai"])
def test_archives_natives_et_references_completes(tmp_path, platform):
    output = packager.package_plugin(platform, tmp_path / (platform + ".zip"))
    with zipfile.ZipFile(output) as archive:
        names = set(archive.namelist())
        if platform == "claude":
            assert "remporte/.claude-plugin/plugin.json" in names
            assert "remporte/agents/lecteur-dce.md" in names
            assert "remporte/.codex-plugin/plugin.json" not in names
            assert not any(name.endswith("openai.yaml") for name in names)
        else:
            assert "remporte/plugin.json" in names
            assert "remporte/.codex-plugin/plugin.json" in names
            assert not any(name.startswith("remporte/agents/") for name in names)
            assert not any("/.claude-plugin/" in name for name in names)
            for skill in ("init", "nouvel-ao", "repondre-ao", "lecture-dce", "redaction-section", "relecture-ao"):
                assert f"remporte/skills/{skill}/SKILL.md" in names
                assert f"remporte/skills/{skill}/agents/openai.yaml" in names
        archive.extractall(tmp_path / platform)
    # Toute référence Markdown relative doit survivre à l'export.
    extracted = tmp_path / platform / "remporte"
    for path in extracted.rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", text):
            if "://" in target or target.startswith("#"):
                continue
            target = target.split("#", 1)[0]
            resolved = (path.parent / target).resolve()
            assert extracted.resolve() in resolved.parents, (path, target)
            assert resolved.is_file(), (path, target)


def test_export_refuse_ecrasement_et_sortie_dans_source(tmp_path):
    output = tmp_path / "existant.zip"
    output.write_bytes(b"a conserver")
    with pytest.raises(FileExistsError):
        packager.package_plugin("openai", output)
    assert output.read_bytes() == b"a conserver"
    with pytest.raises(ValueError):
        packager.package_plugin("openai", PLUGIN / "export.zip")


def test_agents_claude_et_skills_openai_partagent_les_procedures():
    pairs = {"lecteur-dce": "lecture-dce", "redacteur-section": "redaction-section", "relecteur": "relecture-ao"}
    for agent, skill in pairs.items():
        agent_path = PLUGIN / "agents" / (agent + ".md")
        skill_path = PLUGIN / "skills" / skill / "SKILL.md"
        agent_text = agent_path.read_text(encoding="utf-8")
        skill_text = skill_path.read_text(encoding="utf-8")
        agent_ref = re.search(r"\]\(([^)]+)\)", agent_text).group(1)
        skill_ref = re.search(r"\]\(([^)]+)\)", skill_text).group(1)
        assert (agent_path.parent / agent_ref).resolve() == (skill_path.parent / skill_ref).resolve()
        assert f"name: {agent}\n" in agent_text
        assert "tools:" in agent_text
        assert f"model: {'inherit' if agent == 'relecteur' else 'sonnet'}\n" in agent_text
