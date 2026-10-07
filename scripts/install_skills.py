"""Installer les compétences exportées dans un dossier choisi, sans écrasement."""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import shutil


def install_skills(source: Path, destination: Path, *, apply: bool = False) -> list[str]:
    source = source.expanduser().absolute()
    destination = destination.expanduser().absolute()
    for root in (source, destination):
        if any(path.is_symlink() for path in (root, *root.parents)):
            raise ValueError(f"Dossier lié interdit : {root}")
    if not source.is_dir():
        raise ValueError(f"Dossier de compétences absent : {source}")
    skills = sorted(source.iterdir())
    if not skills:
        raise ValueError("Aucune compétence à installer")
    for skill in skills:
        if not re.fullmatch(r"remporte-[a-z0-9-]+", skill.name) or not skill.is_dir():
            raise ValueError(f"Compétence inattendue : {skill}")
        if skill.is_symlink() or any(p.is_symlink() for p in skill.rglob("*")):
            raise ValueError(f"Lien symbolique dans {skill}")
        text = (skill / "SKILL.md").read_text(encoding="utf-8")
        if not re.search(rf"^name: {re.escape(skill.name)}$", text, re.M):
            raise ValueError(f"Nom de compétence incohérent : {skill}")
        target = destination / skill.name
        if target.exists() or target.is_symlink():
            raise FileExistsError(f"Compétence déjà présente, conservée : {target}")
    plan = [str(destination / skill.name) for skill in skills]
    if apply:
        destination.mkdir(parents=True, exist_ok=True)
        for skill in skills:
            shutil.copytree(skill, destination / skill.name)
    return plan


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--destination", required=True, type=Path)
    parser.add_argument("--apply", action="store_true", help="exécuter le plan affiché")
    args = parser.parse_args()
    for path in install_skills(args.source, args.destination, apply=args.apply):
        print(path)
    if not args.apply:
        print("Aperçu uniquement. Ajouter --apply pour installer.")


if __name__ == "__main__":
    main()
