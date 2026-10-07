"""Préparer les archives natives Claude Code et OpenAI depuis la même source."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parent.parent


def package_plugin(platform: str, output: Path, plugin: Path | None = None) -> Path:
    if platform not in {"claude", "openai"}:
        raise ValueError("Plateforme attendue : claude ou openai")
    plugin = (plugin or ROOT / "plugin").resolve()
    output = output.resolve()
    if output == plugin or plugin in output.parents:
        raise ValueError("L'archive doit être écrite hors du dossier plugin")
    if output.exists():
        raise FileExistsError(output)
    manifest_path = (".claude-plugin/plugin.json" if platform == "claude" else "plugin.json")
    manifest = json.loads((plugin / manifest_path).read_text(encoding="utf-8"))
    if manifest.get("name") != "remporte" or not manifest.get("version"):
        raise ValueError("Identité du plugin invalide")
    selected = []
    for path in sorted(plugin.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"Lien symbolique interdit dans une archive : {path}")
        if not path.is_file():
            continue
        relative = path.relative_to(plugin)
        if platform == "openai" and relative.parts[0] in {".claude-plugin", "agents"}:
            continue
        if platform == "claude" and (relative.parts[0] == ".codex-plugin" or relative.as_posix() == "plugin.json" or relative.name == "openai.yaml"):
            continue
        if path.suffix not in {".md", ".json", ".yaml"} and relative.as_posix() != "LICENSE":
            raise ValueError(f"Fichier inattendu dans le plugin : {relative}")
        selected.append((path, relative))
    if not any(relative.name == "SKILL.md" for _, relative in selected):
        raise ValueError("Le plugin ne contient aucune skill")
    output.parent.mkdir(parents=True, exist_ok=True)
    # Mode x : une archive précédente n'est jamais écrasée.
    with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for path, relative in selected:
            archive.write(path, "remporte/" + relative.as_posix())
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--platform", choices=["claude", "openai"], required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(package_plugin(args.platform, args.output))


if __name__ == "__main__":
    main()
