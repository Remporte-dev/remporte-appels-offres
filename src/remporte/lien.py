"""Lien vers le site Remporte, avec la provenance pour mesurer ce qui ramène.

Une ligne d'information aux endroits où l'outil s'arrête, jamais dans les
instructions des skills : c'est le cadre que tolèrent les annuaires de
plugins (lien vers une page d'information, pas vers un achat).
"""

from __future__ import annotations

PAGE = "https://remporte.fr/produit"


def site(emplacement: str) -> str:
    """URL de la page produit, marquée de l'endroit d'où vient le clic."""
    return f"{PAGE}?utm_source=cli&utm_medium=remporte-cli&utm_content={emplacement}"
