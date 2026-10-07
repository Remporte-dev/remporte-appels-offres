#!/usr/bin/env python3
"""Package the Remporte skills as portable Agent Skills archives."""

from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = ROOT / "plugin" / "skills"
REFERENCES_DIR = ROOT / "plugin" / "references"
PLATFORMS = ("gemini", "hermes", "openclaw", "portable", "pi")


def _validate(output: Path) -> Path:
    if output.is_symlink():
        raise ValueError("refusing a symlink output path")
    if output.exists():
        raise ValueError("output already exists")
    parent = output.parent.resolve()
    target = parent / output.name
    for ancestor in (output.absolute(), *output.absolute().parents):
        if ancestor.exists() and ancestor.is_symlink():
            raise ValueError(f"refusing symlink in output path: {ancestor}")
    for source in (ROOT / "plugin", SKILLS_DIR, REFERENCES_DIR):
        resolved = source.resolve()
        if target == resolved or resolved in target.parents:
            raise ValueError("output must be outside the source directories")
    if not SKILLS_DIR.is_dir() or not REFERENCES_DIR.is_dir():
        raise ValueError("plugin skills or references source directory is missing")
    for path in (SKILLS_DIR, REFERENCES_DIR, *SKILLS_DIR.rglob("*"), *REFERENCES_DIR.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"refusing symlink in source: {path}")
    return target


def _portable_skill(name: str, source: Path) -> tuple[str, set[str]]:
    text = source.read_text(encoding="utf-8")
    match = re.match(r"\A---\s*\n(.*?)\n---\s*(?:\n|\Z)", text, re.S)
    if not match:
        raise ValueError(f"missing YAML frontmatter: {source}")
    header = match.group(1)
    body = text[match.end():]
    header = re.sub(r"(?m)^name:\s*.*$", f"name: remporte-{name}", header)
    header = re.sub(r"(?m)^argument-hint:\s*.*\n?", "", header)
    header = re.sub(r"(?m)^disable-model-invocation:\s*.*\n?", "", header)
    header = re.sub(r"\$remporte:([a-z0-9-]+)|/remporte:([a-z0-9-]+)",
                    lambda m: "remporte-" + (m.group(1) or m.group(2)), header)
    if not re.search(r"(?m)^name:\s*remporte-" + re.escape(name) + r"\s*$", header):
        raise ValueError(f"missing frontmatter name in {source}")

    references: set[str] = set()
    def rewrite_reference(match: re.Match[str]) -> str:
        filename = match.group(1)
        references.add(filename)
        return f"references/{filename}"
    body = re.sub(r"\.\./\.\./references/([A-Za-z0-9_.-]+\.md)", rewrite_reference, body)
    # Platform-specific invocation syntax becomes a neutral skill name.
    body = re.sub(r"\$remporte:([a-z0-9-]+)|/remporte:([a-z0-9-]+)",
                  lambda m: "remporte-" + (m.group(1) or m.group(2)), body)
    body = re.sub(r"remporte:(lecteur-dce|redacteur-section|relecteur)", r"remporte-\1", body)
    # Nom qualifié d'une compétence du plugin (`remporte:chiffrage`) : nom portable.
    body = re.sub(r"`remporte:([a-z0-9-]+)`", r"`remporte-\1`", body)
    # Replace specialized-agent routing with skills first, generic sub-agent fallback,
    # and disclosed self-execution when delegation is unavailable.
    body = re.sub(r"Si l'agent spécialisé `[^`]+` est indisponible,\s*transmets cette procédure(?:(?:,| et) le dossier)?(?: et la section)? à un sous-agent générique si l'environnement en propose un\. Sinon,\s*(?:exécute la procédure toi-même|rédige la section toi-même|relis le mémoire toi-même)\.",
                  "Utilise d'abord la compétence Remporte correspondante si elle est disponible. Sinon, transmets la procédure, le dossier et la tâche à un sous-agent générique si l'environnement en propose un. Si tu l'exécutes toi-même faute de sous-agent, indique clairement à l'utilisateur que tu as travaillé sans relecture ou délégation indépendante.", body)
    body = re.sub(r"(?m)^\| Index et analyse \|.*$", "| Index et analyse | compétence `remporte-lecture-dce`, procédure `references/lecture-dce.md` |", body)
    body = re.sub(r"(?m)^\| Rédaction \|.*$", "| Rédaction | compétence `remporte-redaction-section`, procédure `references/redaction-section.md` |", body)
    body = re.sub(r"(?m)^\| Relecture \|.*$", "| Relecture | compétence `remporte-relecture-ao`, procédure `references/relecture-ao.md` |", body)
    body = body.replace("## 4. Le parcours, avec des sous-agents", "## 4. Le parcours avec les compétences Remporte")
    body = body.replace("Tu orchestres ; les lectures et rédactions lourdes partent à des sous-agents,\nqui ménagent l'abonnement et ton propre contexte :",
                        "Utilise d'abord les compétences Remporte indiquées dans le tableau. Si une compétence manque, transmets la procédure à un sous-agent générique si l'environnement en propose un. Si tu exécutes toi-même une étape faute de sous-agent, indique clairement cette limite à l'utilisateur : cette étape ne bénéficie alors pas d'une contribution indépendante.")
    body = body.replace("Si un agent spécialisé est indisponible, transmets la procédure correspondante et le chemin du dossier à un sous-agent générique si l’environnement en propose un. Sinon, exécute toi-même cette étape avec `remporte guide <étape>`, dans le même ordre. Pour la rédaction et la relecture, applique le même recours.",
                        "Pour chaque étape, utilise la compétence Remporte correspondante. Si elle n'est pas disponible, transmets la procédure et le dossier à un sous-agent générique si l'environnement en propose un. Sinon, réalise toi-même l'étape avec `remporte guide <étape>` et signale que tu n'as pas eu de contribution indépendante.")
    # Les points d'entrée distribués ne conservent pas les instructions d'un autre harnais.
    body = re.sub(r"Pour Codex,.*?propre à Claude Code\.\n", "Demande la compétence Remporte par son nom ou décris la tâche.\n", body)
    body = re.sub(r"Dans Codex,.*?propre à Claude Code\. ", "", body)
    body = re.sub(r"`(remporte-[a-z-]+)` dans Codex ou `\1` dans Claude Code", r"la compétence `\1`", body)
    body = re.sub(r"`(remporte-[a-z-]+)` dans Codex, `/??\1` dans Claude Code", r"la compétence `\1`", body)
    body = body.replace("(`remporte-init` dans Codex, `remporte-init` dans Claude Code)", "(compétence `remporte-init`)")
    body = body.replace("demandez `remporte-nouvel-ao` dans Codex, ou utilisez `remporte-nouvel-ao` dans Claude Code", "demandez la compétence `remporte-nouvel-ao`")
    if name == "nouvel-ao":
        table = """| Étape | Procédure |
|---|---|
| Index et analyse | compétence `remporte-lecture-dce`, [lecture du DCE](references/lecture-dce.md) |
| Go/No-Go | avec l'utilisateur, `remporte guide go-no-go`, analyse et `remporte fiche` |
| Plan | `remporte guide plan` |
| Rédaction | compétence `remporte-redaction-section`, [rédaction d'une section](references/redaction-section.md) |
| Relecture | compétence `remporte-relecture-ao`, [relecture](references/relecture-ao.md) |
| Livrables | `remporte guide livrables`, puis la compétence Remporte du livrable, en demandant d'abord le modèle de l'entreprise |
| Documents de travail | `remporte exporter` |
"""
        body = re.sub(r"(?m)^\| Étape \|.*?^\| Documents de travail \|[^\n]*\n", table, body, flags=re.S)
        references.update({"lecture-dce.md", "redaction-section.md", "relecture-ao.md"})
    return f"---\n{header.strip()}\n---\n{body}", references


def build_archive(platform: str, output: Path) -> Path:
    if platform not in PLATFORMS:
        raise ValueError(f"unsupported platform: {platform}")
    target = _validate(output)
    manifest = json.loads((ROOT / "plugin" / "plugin.json").read_text(encoding="utf-8"))
    entries: dict[str, bytes] = {}
    names = sorted(p.parent.name for p in SKILLS_DIR.glob("*/SKILL.md") if p.is_file())
    if not names:
        raise ValueError("no skill found")
    for name in names:
        skill, refs = _portable_skill(name, SKILLS_DIR / name / "SKILL.md")
        prefix = f"remporte/skills/remporte-{name}/"
        entries[prefix + "SKILL.md"] = skill.encode("utf-8")
        for reference in sorted(refs):
            ref = REFERENCES_DIR / reference
            if not ref.is_file():
                raise ValueError(f"referenced source does not exist: {ref}")
            entries[prefix + "references/" + reference] = ref.read_bytes()
    if platform == "gemini":
        entries["remporte/gemini-extension.json"] = json.dumps({
            "name": "remporte", "version": manifest["version"],
            "description": manifest["description"], "contextFileName": "GEMINI.md",
        }, ensure_ascii=False, indent=2).encode("utf-8") + b"\n"
        entries["remporte/GEMINI.md"] = (
            "# Remporte\n\nUtilise les commandes Remporte et les fichiers accessibles dans l'environnement de travail. "
            "Active et suis les compétences Remporte pertinentes dans `skills/` pour chaque tâche. "
            "N'invente aucune information et conserve les validations humaines prévues par les compétences.\n"
        ).encode("utf-8")
    else:
        destination = {
            "hermes": "~/.hermes/skills", "openclaw": "~/.openclaw/skills",
            "pi": "~/.pi/agent/skills", "portable": "un dossier de votre choix",
        }[platform]
        entries["remporte/README.md"] = (
            "# Compétences Remporte\n\nCopiez les sous-dossiers de `skills/` dans `" + destination + "`. "
            "Chaque compétence est autonome avec ses fichiers de référence.\n"
        ).encode("utf-8")
    entries["remporte/LICENSE"] = (ROOT / "LICENSE").read_bytes()
    entries["remporte/install_skills.py"] = (ROOT / "scripts/install_skills.py").read_bytes()
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for path, data in sorted(entries.items()):
            archive.writestr(path, data)
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--platform", required=True, choices=PLATFORMS)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        print(build_archive(args.platform, args.output))
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
