"""Préparer un paquet à transférer dans Muse ou ChatGPT Work."""
from __future__ import annotations

import argparse
from email.parser import Parser
import json
from pathlib import Path
import tempfile
import zipfile

from package_skills import ROOT, build_archive


def build_cloud(platform: str, wheel: Path, output: Path) -> Path:
    if platform not in {"muse", "chatgpt-work"}:
        raise ValueError("Plateforme attendue : muse ou chatgpt-work")
    if wheel.is_symlink() or output.is_symlink():
        raise ValueError("Lien symbolique interdit")
    if output.exists():
        raise FileExistsError(output)
    for path in (output.absolute(), *output.absolute().parents):
        if path.is_symlink():
            raise ValueError(f"Dossier lié interdit : {path}")
    output = output.resolve()
    if (ROOT / "plugin").resolve() in output.parents:
        raise ValueError("Sortie interdite dans la source plugin")
    manifest = json.loads((ROOT / "plugin/plugin.json").read_text(encoding="utf-8"))
    with zipfile.ZipFile(wheel) as archive:
        metadata_paths = [name for name in archive.namelist() if name.endswith(".dist-info/METADATA")]
        if len(metadata_paths) != 1:
            raise ValueError("Métadonnées du paquet CLI invalides")
        metadata = Parser().parsestr(archive.read(metadata_paths[0]).decode("utf-8"))
        if metadata["Name"] != "remporte" or metadata["Version"] != manifest["version"]:
            raise ValueError("Le CLI et les compétences doivent avoir la même version")
    with tempfile.TemporaryDirectory(prefix="remporte-cloud-") as temp:
        skills_zip = build_archive("portable", Path(temp).resolve() / "skills.zip")
        with zipfile.ZipFile(skills_zip) as archive:
            entries = {name: archive.read(name) for name in archive.namelist()}
    entries["remporte/cli/" + wheel.name] = wheel.read_bytes()
    entries["remporte/install_skills.py"] = (ROOT / "scripts/install_skills.py").read_bytes()
    entries["remporte/DEMARRAGE.md"] = (
        "# Remporte dans " + ("Muse" if platform == "muse" else "ChatGPT Work") + "\n\n"
        "Ce paquet contient le CLI et six compétences autonomes. Il n'est pas un connecteur publié dans un annuaire.\n\n"
        "## Demande à donner à votre agent\n\n"
        "Lis ce fichier et vérifie que tu peux exécuter des commandes, lire et écrire les fichiers de cet environnement. "
        "Si ces accès manquent, arrête et explique la limite. N'utilise aucun chemin de mon ordinateur personnel.\n\n"
        "Vérifie `remporte --version`. Pour installer cette version, propose `uv tool install ./cli/" + wheel.name + "` "
        "depuis le dossier de ce paquet et attends mon accord. Si uv manque, propose la procédure officielle "
        "https://docs.astral.sh/uv/getting-started/installation/ ; respecte les autorisations réseau et installation de la plateforme. "
        "Ne prétends pas que l'outil est installé avant une vérification réussie de sa version.\n\n"
        "Lis `skills/remporte-init/SKILL.md` et accompagne-moi pour choisir un dossier de travail dans cet environnement. "
        "Demande mes documents d'entreprise et mon DCE, puis utilise les fichiers que j'y ai fournis. "
        "Lis ensuite `skills/remporte-nouvel-ao/SKILL.md` pour conduire la réponse. "
        "Chaque compétence contient ses propres références dans references/. Les autres compétences sont dans skills/. "
        "Si ta plateforme permet d'enregistrer des compétences personnalisées, utilise son mécanisme documenté ; "
        "sinon lis ces fichiers directement à chaque étape. N'invente pas un dossier système de compétences.\n\n"
        "Conserve les validations de l'analyse, du go/no-go et du plan avant la rédaction. "
        "Ne fabrique aucune référence, aucun effectif ni certification. "
        "Si aucun agent indépendant ne peut relire, signale que la relecture a lieu dans le même contexte. "
        "Remets les exports Word, HTML et Excel via le mécanisme de fichiers de cette plateforme. "
        "Ne publie et ne dépose jamais la réponse à un marché sans ma demande.\n"
    ).encode("utf-8")
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(entries.items()):
            archive.writestr(name, data)
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--platform", required=True, choices=["muse", "chatgpt-work"])
    parser.add_argument("--wheel", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    print(build_cloud(args.platform, args.wheel, args.output))
