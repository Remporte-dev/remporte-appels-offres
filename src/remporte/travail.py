"""Espace de travail : un dossier `ressources/` et un dossier `DCEs/`.

```
<espace>/
  AGENTS.md, CLAUDE.md, .remporte-espace
  ressources/            documents de l'entreprise, fiche-entreprise.md, .index/
  DCEs/<appel d'offres>/ un dossier de réponse par consultation
```

Les commandes repèrent l'espace en remontant depuis le répertoire courant,
grâce au fichier `.remporte-espace`. Hors d'un espace, la base reste dans
`~/.remporte/base/`.
"""

from __future__ import annotations

import importlib.resources
from pathlib import Path

MARQUEUR = ".remporte-espace"
RESSOURCES = "ressources"
DCES = "DCEs"


def trouver_espace(depart: Path | None = None) -> Path | None:
    """Premier dossier contenant `.remporte-espace`, en remontant."""
    courant = Path(depart or Path.cwd()).resolve()
    for candidat in (courant, *courant.parents):
        if (candidat / MARQUEUR).is_file():
            return candidat
    return None


def creer_espace(racine: Path) -> dict:
    """Crée l'espace (ou le complète) sans jamais écraser un fichier existant."""
    racine = Path(racine)
    (racine / RESSOURCES).mkdir(parents=True, exist_ok=True)
    (racine / DCES).mkdir(parents=True, exist_ok=True)
    crees: list[str] = []
    fichiers = {
        MARQUEUR: "Espace de travail remporte. Ne pas supprimer.\n",
        "AGENTS.md": _gabarit("AGENTS-espace.md"),
        "CLAUDE.md": "@AGENTS.md\n",
        "GEMINI.md": "@./AGENTS.md\n",
        f"{RESSOURCES}/fiche-entreprise.md": _gabarit("fiche-entreprise.md"),
    }
    for relatif, contenu in fichiers.items():
        chemin = racine / relatif
        if not chemin.exists():
            chemin.write_text(contenu, encoding="utf-8")
            crees.append(relatif)
    return {"espace": str(racine.resolve()), "crees": crees}


def _gabarit(nom: str) -> str:
    return (importlib.resources.files("remporte") / "gabarits" / nom).read_text(
        encoding="utf-8"
    )
