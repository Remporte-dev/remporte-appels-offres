import importlib.util
from pathlib import Path
import sys
import zipfile
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location("package_cloud", ROOT / "scripts/package_cloud.py")
cloud = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cloud)

@pytest.mark.parametrize("platform", ["muse", "chatgpt-work"])
def test_cloud_bundle_has_matching_cli_and_self_contained_skills(tmp_path, platform):
    import json
    version = json.loads((ROOT / "plugin/plugin.json").read_text())["version"]
    wheel = tmp_path / f"remporte-{version}-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr(f"remporte-{version}.dist-info/METADATA", f"Name: remporte\nVersion: {version}\n")
    output = cloud.build_cloud(platform, wheel, tmp_path / "cloud.zip")
    with zipfile.ZipFile(output) as archive:
        assert archive.read("remporte/cli/" + wheel.name) == wheel.read_bytes()
        assert len([p for p in archive.namelist() if p.endswith("SKILL.md")]) == 13
        startup = archive.read("remporte/DEMARRAGE.md").decode()
        assert "attends mon accord" in startup
        assert "skills/remporte-init/SKILL.md" in startup
        assert "N'utilise aucun chemin de mon ordinateur personnel" in startup
    with pytest.raises(FileExistsError):
        cloud.build_cloud(platform, wheel, output)

def test_cloud_refuses_mismatched_cli(tmp_path):
    wheel = tmp_path / "wrong.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("remporte-0.1.dist-info/METADATA", "Name: remporte\nVersion: 0.1\n")
    with pytest.raises(ValueError, match="même version"):
        cloud.build_cloud("muse", wheel, tmp_path / "cloud.zip")
