"""Charte Remporte : une page HTML autonome à partir de markdown.

Une seule fonction de mise en page, `page_depuis_markdown` : l'agent écrit du
markdown, le CLI produit la page. La page inclut telles quelles les deux
feuilles du kit HTML Remporte (`kit_charte/`) : jetons, composants, logo
et polices embarquées (licence SIL OFL), aucune ressource réseau. Elle n'ajoute
que la mise en page du texte markdown, écrite avec les jetons du kit.
Le mémoire et `dossier.html`, documents destinés à l'acheteur, n'utilisent pas
cette charte : ils restent neutres.
"""

from __future__ import annotations

import base64
import hashlib
import html
import re
from functools import cache
from pathlib import Path
from urllib.parse import urlsplit

import markdown
from markdown.extensions import Extension
from markdown.treeprocessors import Treeprocessor

_KIT = Path(__file__).parent / "kit_charte"

# Mise en page du texte markdown, avec les seuls jetons du kit.
_CSS_PAGE = """
  .doc-head{position:relative;overflow:hidden;background:var(--bg);border-bottom:1px solid var(--line)}
  .doc-head .container{max-width:960px;position:relative;padding-top:var(--s6);padding-bottom:var(--s7)}
  .doc-head .kicker{margin-top:var(--s7)}
  .doc-head .h1{font-size:clamp(32px,5vw,56px);margin-top:var(--s3)}
  .doc{max-width:960px;padding-top:var(--s7);padding-bottom:var(--s8)}
  .doc > h1{font-size:clamp(28px,3.6vw,40px);letter-spacing:-.035em;line-height:1.1;
    margin:var(--s8) 0 var(--s5);padding-top:var(--s7);border-top:1px solid var(--line-strong)}
  .doc > h2{font-size:clamp(22px,2.6vw,28px);letter-spacing:-.025em;line-height:1.2;
    margin:var(--s7) 0 var(--s4)}
  .doc > h2::before{content:"// ";color:var(--accent);font:600 .55em/1 var(--mono);vertical-align:.3em}
  .doc > h3{font-size:18px;letter-spacing:-.01em;margin:var(--s5) 0 var(--s3)}
  .doc > p,.doc > ul,.doc > ol{max-width:72ch;color:var(--ink-700)}
  .doc table.data{margin:var(--s4) 0 var(--s5);display:block;overflow-x:auto}
  .doc table.data th{background:var(--bg-alt)}
  .doc table.data td:first-child{min-width:9rem;font-weight:600;color:var(--navy)}
  .doc thead:not(:has(th:not(:empty))){display:none}
  .doc blockquote.callout{margin:var(--s4) 0}
  .doc blockquote.callout p:last-child{margin-bottom:0}
  .doc code{font:500 .86em var(--mono);background:var(--accent-soft);color:var(--accent-strong);
    border:1px solid var(--accent-line);border-radius:var(--r-sm);padding:1px 6px}
  .doc hr{border:0;border-top:1px solid var(--line);margin:var(--s6) 0}
  .site-footer .container{max-width:960px}
  @media print{
    .doc-head .grid-bg,.doc-head .halo{display:none}
    .doc table.data{display:table}
    .doc table.data tr,.doc blockquote{break-inside:avoid}
    .doc > h1{break-before:page;border-top:0;padding-top:0;margin-top:0}
  }
"""


# Le texte converti vient en partie du DCE, écrit par un tiers : aucun HTML brut, aucun
# lien actif hors http(s) et mailto, aucune ressource chargée depuis le réseau.
_SCHEMAS_LIENS = {"", "http", "https", "mailto"}


def _schema(url: str) -> str:
    return urlsplit(re.sub(r"[\x00-\x20\x7f]", "", url)).scheme.lower()


class _LiensSurs(Treeprocessor):
    def run(self, racine):
        for element in racine.iter():
            if "href" in element.attrib and _schema(element.attrib["href"]) not in _SCHEMAS_LIENS:
                del element.attrib["href"]
            if "src" in element.attrib and _schema(element.attrib["src"]) != "":
                del element.attrib["src"]


class _SansHtmlBrut(Extension):
    def extendMarkdown(self, md):
        md.preprocessors.deregister("html_block")
        md.inlinePatterns.deregister("html")
        md.treeprocessors.register(_LiensSurs(md), "liens_surs", 0)


def csp(script: str | None = None) -> str:
    """Politique de sécurité des pages produites : rien ne se charge du réseau,
    seul le script de la page elle-même (par son empreinte) peut s'exécuter."""
    regle = "default-src 'none'; style-src 'unsafe-inline'; font-src data:; img-src data:"
    if script is None:
        return regle
    empreinte = base64.b64encode(hashlib.sha256(script.encode("utf-8")).digest()).decode()
    return f"{regle}; script-src 'sha256-{empreinte}'"


def html_depuis_markdown(texte: str, extensions: list[str] | None = None) -> str:
    """Markdown → HTML, sans HTML brut ni lien dangereux : le HTML écrit dans le
    texte s'affiche comme du texte. Les commentaires (marqueurs `<!-- à remplir -->`,
    repères de page) restent invisibles, comme avant."""
    texte = re.sub(r"<!--.*?-->", "", texte, flags=re.S)
    return markdown.markdown(texte, extensions=[*(extensions or []), _SansHtmlBrut()])


@cache
def _feuilles_du_kit() -> str:
    return "\n".join(
        (_KIT / nom).read_text(encoding="utf-8")
        for nom in ("remporte-polices.css", "remporte.css")
    )


def _premier_titre(texte: str) -> tuple[str | None, str]:
    """Le premier titre `#` du texte, et le texte sans lui."""
    trouve = re.search(r"^#\s+(.+?)\s*#*\s*$", texte, re.MULTILINE)
    if not trouve:
        return None, texte
    return trouve.group(1).strip(), texte[:trouve.start()] + texte[trouve.end():]


def _composer(corps: str) -> str:
    """Branche le HTML issu du markdown sur les composants du kit."""
    corps = corps.replace("<table>", '<table class="data">')
    return corps.replace("<blockquote>", '<blockquote class="callout">')


def page_depuis_markdown(texte: str, titre: str | None = None) -> str:
    """Page HTML autonome, à la charte Remporte, à partir d'un texte markdown.

    Le premier titre `#` du texte devient le titre de la page ; `titre` sert
    d'étiquette au-dessus de lui et de titre d'onglet (à défaut, ce premier titre).
    """
    titre_page, reste = _premier_titre(texte)
    etiquette = titre or titre_page or "Remporte"
    titre_page = titre_page or etiquette
    if etiquette == titre_page:
        etiquette = "Document de travail"
    corps = _composer(html_depuis_markdown(reste, ["tables", "sane_lists"]))
    entete = (
        '<header class="doc-head">\n'
        '<div class="grid-bg left"></div><div class="halo left"></div>\n'
        '<div class="container">\n'
        '<span class="brand">remporte<span class="dot">.</span></span>\n'
        f'<span class="kicker">{html.escape(etiquette)}</span>\n'
        f'<h1 class="h1">{html.escape(titre_page)}</h1>\n'
        "</div>\n</header>\n"
    )
    pied = (
        '<footer class="site-footer"><div class="container">'
        '<span class="brand">remporte<span class="dot">.</span></span>'
        "</div></footer>\n"
    )
    return (
        '<!DOCTYPE html>\n<html lang="fr">\n<head>\n<meta charset="utf-8">\n'
        f'<meta http-equiv="Content-Security-Policy" content="{csp()}">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{html.escape(titre or titre_page)}</title>\n"
        f"<style>\n{_feuilles_du_kit()}\n{_CSS_PAGE}</style>\n"
        f"</head>\n<body>\n{entete}"
        f'<main class="container doc">\n{corps}\n</main>\n{pied}</body>\n</html>\n'
    )
