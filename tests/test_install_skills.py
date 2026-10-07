import importlib.util
from pathlib import Path
import pytest

spec = importlib.util.spec_from_file_location("install_skills", Path(__file__).resolve().parent.parent / "scripts/install_skills.py")
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)

def test_preview_install_and_conflict(tmp_path):
    source = tmp_path / "source"
    skill = source / "remporte-init"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("---\nname: remporte-init\n---\n")
    dest = tmp_path / "target"
    assert len(installer.install_skills(source, dest)) == 1
    assert not dest.exists()
    installer.install_skills(source, dest, apply=True)
    preserved = (dest / "remporte-init/SKILL.md").read_bytes()
    with pytest.raises(FileExistsError):
        installer.install_skills(source, dest, apply=True)
    assert (dest / "remporte-init/SKILL.md").read_bytes() == preserved

def test_no_partial_install_on_conflict(tmp_path):
    source = tmp_path / "source"
    for name in ("remporte-init", "remporte-relecture-ao"):
        skill = source / name
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text(f"---\nname: {name}\n---\n")
    dest = tmp_path / "target"
    (dest / "remporte-relecture-ao").mkdir(parents=True)
    with pytest.raises(FileExistsError):
        installer.install_skills(source, dest, apply=True)
    assert not (dest / "remporte-init").exists()

def test_refuse_symlink(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "remporte-init").symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(ValueError):
        installer.install_skills(source, tmp_path / "dest", apply=True)
