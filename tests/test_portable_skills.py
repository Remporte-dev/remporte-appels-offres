import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "package_skills.py"
SKILL_NAMES = {
    "remporte-init", "remporte-lecture-dce", "remporte-nouvel-ao",
    "remporte-redaction-section", "remporte-relecture-ao", "remporte-repondre-ao",
    "remporte-memoire-technique", "remporte-cadre-reponse", "remporte-fichier-impose",
    "remporte-chiffrage", "remporte-visuels", "remporte-soutenance", "remporte-candidature",
}


def run_export(output: Path, platform="portable", check=True):
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--platform", platform, "--output", str(output)],
        cwd=ROOT, capture_output=True, text=True, check=check,
    )


@pytest.mark.parametrize("platform", ["gemini", "hermes", "openclaw", "portable", "pi"])
def test_export_extracts_portable_self_contained_skills(tmp_path, platform):
    archive_path = tmp_path / f"{platform}.zip"
    run_export(archive_path, platform)
    extract = tmp_path / "extracted"
    with zipfile.ZipFile(archive_path) as archive:
        archive.extractall(extract)
    root = extract / "remporte"
    skill_dirs = sorted((root / "skills").iterdir())
    assert {p.name for p in skill_dirs} == SKILL_NAMES
    for directory in skill_dirs:
        skill_file = directory / "SKILL.md"
        text = skill_file.read_text(encoding="utf-8")
        assert re.search(r"(?m)^name: " + re.escape(directory.name) + r"$", text)
        assert "propre à Claude Code" not in text
        assert "dans Codex ou" not in text
        if directory.name == "remporte-nouvel-ao":
            table = text.split("| Étape |", 1)[1].split("\n\n", 1)[0]
            assert all(line.count("|") == 3 for line in table.splitlines() if line.startswith("|"))
        assert "disable-model-invocation" not in text
        assert not re.search(r"(?:\$|/)remporte:[a-z0-9-]+", text)
        assert "../../references/" not in text
        assert not re.search(r"(?:Claude Code|Codex).{0,40}(?:\$remporte:|/remporte:)", text, re.I)
        assert "remporte:lecteur-dce" not in text
        assert "remporte:redacteur-section" not in text
        assert "remporte:relecteur" not in text
        # A copied skill remains usable by itself, with every relative reference present.
        isolated = tmp_path / "isolated" / directory.name
        isolated.mkdir(parents=True)
        for item in directory.iterdir():
            if item.is_dir():
                import shutil
                shutil.copytree(item, isolated / item.name)
            else:
                (isolated / item.name).write_bytes(item.read_bytes())
        for relative in re.findall(r"\]\((references/[^)]+)\)", text):
            assert (isolated / relative).is_file()
    assert not any("agents/" in name or "openai.yaml" in name for name in zipfile.ZipFile(archive_path).namelist())
    if platform == "gemini":
        manifest = json.loads((root / "gemini-extension.json").read_text())
        source_manifest = json.loads((ROOT / "plugin" / "plugin.json").read_text())
        assert manifest == {
            "name": "remporte", "version": source_manifest["version"],
            "description": source_manifest["description"], "contextFileName": "GEMINI.md",
        }
        assert "MCP" not in (root / "GEMINI.md").read_text()
        assert "skills/" in (root / "GEMINI.md").read_text()
    else:
        readme = (root / "README.md").read_text()
        expected = {"hermes": "~/.hermes/skills", "openclaw": "~/.openclaw/skills",
                    "pi": "~/.pi/agent/skills", "portable": "un dossier de votre choix"}[platform]
        assert expected in readme


def test_refuses_existing_output(tmp_path):
    output = tmp_path / "exists.zip"
    output.write_text("keep")
    result = run_export(output, check=False)
    assert result.returncode != 0
    assert output.read_text() == "keep"


def test_refuses_symlink_output(tmp_path):
    actual = tmp_path / "actual.zip"
    actual.write_text("keep")
    link = tmp_path / "link.zip"
    link.symlink_to(actual)
    result = run_export(link, check=False)
    assert result.returncode != 0
    assert actual.read_text() == "keep"


def test_refuses_output_under_plugin_source():
    output = ROOT / "plugin" / "skills-export-test.zip"
    result = run_export(output, check=False)
    assert result.returncode != 0
    assert not output.exists()
