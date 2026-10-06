"""Charte Remporte : une page HTML autonome à partir de markdown.

Une seule fonction de mise en page, `page_depuis_markdown` : l'agent écrit du
markdown, le CLI produit la page. Couleurs et polices de la plaquette
commerciale, CSS inline, aucune ressource réseau ni police téléchargée.
Le mémoire et `dossier.html`, documents destinés à l'acheteur, n'utilisent pas
cette charte : ils restent neutres.
"""

from __future__ import annotations

import html
import re

import markdown

BLEU_NUIT = "#1d2b50"
TERRACOTTA = "#c2410c"
FILET = "#e6e3db"
TEXTE_LEGER = "#6b7280"
FOND_CARTE = "#F9FAFB"

POLICE = '"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
POLICE_MONO = '"JetBrains Mono", ui-monospace, "SF Mono", Menlo, Consolas, monospace'

PIED_DE_PAGE = "Préparé avec remporte — remporte.fr"

_CSS = f"""
  * {{ box-sizing: border-box; }}
  body {{ margin: 0 auto; max-width: 56rem; padding: 0 1rem 2.5rem; background: #fff;
         color: {BLEU_NUIT}; font-family: {POLICE}; line-height: 1.55; }}
  h1 {{ font-size: 1.5rem; line-height: 1.25; margin: 1.8rem 0 .4rem;
       letter-spacing: -.01em; }}
  h1 + p strong:first-child {{ color: {TERRACOTTA}; }}
  h2 {{ font-size: 1.1rem; margin: 2rem 0 .7rem; padding-top: .8rem;
       border-top: 2px solid {BLEU_NUIT}; }}
  h3 {{ font-size: .98rem; margin: 1.2rem 0 .4rem; }}
  a {{ color: {TERRACOTTA}; }}
  table {{ border-collapse: collapse; width: 100%; margin: .7rem 0; font-size: .92rem;
          display: block; overflow-x: auto; }}
  th, td {{ border: 1px solid {FILET}; padding: .4rem .6rem; text-align: left;
           vertical-align: top; overflow-wrap: break-word; }}
  th {{ background: {FOND_CARTE}; white-space: nowrap; }}
  thead:not(:has(th:not(:empty))) {{ display: none; }}
  td:first-child {{ min-width: 7rem; }}
  code {{ background: {FOND_CARTE}; border-radius: 4px; padding: .05rem .3rem;
          font-family: {POLICE_MONO}; font-size: .85em; }}
  blockquote {{ border-left: 3px solid {TERRACOTTA}; margin: .8rem 0;
               padding: .2rem 1rem; background: {FOND_CARTE}; border-radius: 0 10px 10px 0; }}
  ul, ol {{ padding-left: 1.3rem; }}
  footer {{ margin-top: 2.5rem; padding-top: .8rem; border-top: 1px solid {FILET};
           color: {TEXTE_LEGER}; font-size: .8rem; }}
  @media print {{
    body {{ max-width: none; padding: 0; }}
    th, blockquote {{ background: none; }}
    tr, blockquote {{ break-inside: avoid; }}
    table {{ display: table; }}
  }}
"""


def page_depuis_markdown(texte: str, titre: str | None = None) -> str:
    """Page HTML autonome, à la charte Remporte, à partir d'un texte markdown.

    Le titre de l'onglet est `titre`, sinon le premier titre `#` du texte.
    """
    if titre is None:
        trouve = re.search(r"^#\s+(.+)$", texte, re.MULTILINE)
        titre = trouve.group(1).strip() if trouve else "Remporte"
    corps = markdown.markdown(texte, extensions=["tables", "sane_lists"])
    return (
        '<!DOCTYPE html>\n<html lang="fr">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{html.escape(titre)}</title>\n<style>{_CSS}</style>\n"
        f"</head>\n<body>\n{corps}\n<footer>{PIED_DE_PAGE}</footer>\n</body>\n</html>\n"
    )
