"""Export du dossier de réponse : mémoire DOCX et HTML autonome à deux onglets.

Le DOCX assemble les sections dans l'ordre de 04-plan.md. Le HTML est un seul
fichier autonome (CSS et JS inline, aucune ressource réseau) avec deux onglets
« Analyse » (02, 03) et « Mémoire » (sections), et le relevé des
`[à compléter : …]`.
"""

from __future__ import annotations

import html
import re
from pathlib import Path

import markdown

from remporte import espace


def exporter(dossier: Path, formats: set[str]) -> dict:
    """Exporte les formats demandés. Rend {"docx": chemin|None, "html": ...}."""
    dossier = Path(dossier)
    if not (dossier / ".remporte").is_dir():
        raise espace.Erreur(
            f"{dossier} n'est pas un dossier de réponse (pas de .remporte/)."
        )
    sections = espace.sections_plan(dossier)
    if not sections:
        raise espace.Erreur(
            "04-plan.md ne liste aucune section au format `- [ ] NN — Titre`. "
            "Complétez le plan (remporte guide plan) avant d'exporter."
        )
    resultat: dict[str, Path | None] = {"docx": None, "html": None}
    if "docx" in formats:
        resultat["docx"] = _exporter_docx(dossier, sections)
    if "html" in formats:
        resultat["html"] = _exporter_html(dossier, sections)
    return resultat


# ---------------------------------------------------------------------------
# DOCX (python-docx) — markdown des sections → titres, listes, tableaux
# ---------------------------------------------------------------------------

_RE_MORCEAUX = re.compile(r"(\*\*.+?\*\*|\*.+?\*)")


def _texte_pour_acheteur(texte: str) -> str:
    """Retire les notes de travail : une citation `>` est une note de l'agent
    (critère servi, sources consultées), pas un contenu pour l'acheteur."""
    return "\n".join(l for l in texte.splitlines() if not l.lstrip().startswith(">"))


def _sans_titre_propre(texte: str) -> str:
    """Retire le titre de premier niveau qui ouvre la section (`# 01 — …`) :
    le titre du plan fait foi et l'export l'écrit lui-même, sans doublon."""
    lignes = texte.splitlines()
    for index, ligne in enumerate(lignes):
        if ligne.strip():
            if re.match(r"^#\s", ligne):
                del lignes[index]
            break
    return "\n".join(lignes)


def _exporter_docx(dossier: Path, sections: list[dict]) -> Path:
    from docx import Document

    document = Document()
    document.add_heading("Mémoire technique", 0)
    for section in sections:
        fichier = (dossier / "sections" / section["fichier"]) \
            if section["fichier"] else None
        if fichier is None or not fichier.exists():
            document.add_heading(f"{section['numero']} — {section['titre']}", 1)
            document.add_paragraph(
                f"[section {section['numero']} manquante : {section['titre']}]"
            )
            continue
        document.add_heading(f"{section['numero']} — {section['titre']}", 1)
        texte = _texte_pour_acheteur(fichier.read_text(encoding="utf-8"))
        _ecrire_markdown_docx(document, _sans_titre_propre(texte))
    chemin = dossier / "export" / "memoire.docx"
    chemin.parent.mkdir(parents=True, exist_ok=True)
    document.save(str(chemin))
    return chemin


def _ecrire_markdown_docx(document, texte: str) -> None:
    lignes = texte.splitlines()
    index = 0
    while index < len(lignes):
        ligne = lignes[index].rstrip()
        if not ligne.strip():
            index += 1
            continue
        if ligne.lstrip().startswith("|"):
            bloc: list[str] = []
            while index < len(lignes) and lignes[index].lstrip().startswith("|"):
                bloc.append(lignes[index].strip())
                index += 1
            _tableau_docx(document, bloc)
            continue
        titre = re.match(r"^(#{1,6})\s+(.*)$", ligne)
        if titre:
            document.add_heading(titre.group(2).strip(), min(len(titre.group(1)), 6))
            index += 1
            continue
        puce = re.match(r"^(\s*)[-*]\s+(.*)$", ligne)
        if puce and not puce.group(2).startswith("*"):
            niveau = min(len(puce.group(1)) // 2 + 1, 3)
            _paragraphe_stylee(
                document, "List Bullet" if niveau == 1 else f"List Bullet {niveau}",
                puce.group(2),
            )
            index += 1
            continue
        numero = re.match(r"^(\s*)\d+[.)]\s+(.*)$", ligne)
        if numero:
            _paragraphe_stylee(document, "List Number", numero.group(2))
            index += 1
            continue
        # Les lignes coupées à la main forment un seul paragraphe, comme en
        # markdown : on rassemble jusqu'à la ligne vide ou au prochain bloc.
        morceaux = [ligne.strip()]
        index += 1
        while index < len(lignes) and _ligne_de_paragraphe(lignes[index]):
            morceaux.append(lignes[index].strip())
            index += 1
        paragraphe = document.add_paragraph()
        _paragraphe_avec_format(paragraphe, " ".join(morceaux))


def _ligne_de_paragraphe(ligne: str) -> bool:
    """Ligne qui prolonge le paragraphe en cours (ni vide, ni début de bloc)."""
    nette = ligne.strip()
    if not nette or nette.startswith(("|", "#", ">")):
        return False
    return not re.match(r"^([-*]\s|\d+[.)]\s)", nette)


def _paragraphe_stylee(document, nom_style: str, texte: str) -> None:
    try:
        paragraphe = document.add_paragraph(style=nom_style)
    except KeyError:
        paragraphe = document.add_paragraph()
    _paragraphe_avec_format(paragraphe, texte)


def _paragraphe_avec_format(paragraphe, texte: str) -> None:
    """Texte markdown inline → runs DOCX (gras, italique)."""
    for morceau in _RE_MORCEAUX.split(texte):
        if not morceau:
            continue
        if morceau.startswith("**") and morceau.endswith("**") and len(morceau) >= 5:
            run = paragraphe.add_run(morceau[2:-2])
            run.bold = True
        elif morceau.startswith("*") and morceau.endswith("*") and len(morceau) >= 3:
            run = paragraphe.add_run(morceau[1:-1])
            run.italic = True
        else:
            paragraphe.add_run(morceau)


def _tableau_docx(document, bloc: list[str]) -> None:
    lignes_cellules: list[list[str]] = []
    for ligne in bloc:
        if re.fullmatch(r"\|[\s:\-|]*\|", ligne):
            continue  # ligne séparatrice d'en-tête
        temporaire = ligne.strip().strip("|").replace("\\|", "\x00")
        lignes_cellules.append(
            [cellule.strip().replace("\x00", "|") for cellule in temporaire.split("|")]
        )
    if not lignes_cellules:
        return
    largeur = max(len(ligne) for ligne in lignes_cellules)
    table = document.add_table(rows=len(lignes_cellules), cols=largeur)
    try:
        table.style = "Table Grid"
    except KeyError:
        pass
    for i, ligne in enumerate(lignes_cellules):
        for j in range(largeur):
            table.cell(i, j).text = ligne[j] if j < len(ligne) else ""


# ---------------------------------------------------------------------------
# HTML autonome — deux onglets + relevé des « [à compléter : …] »
# ---------------------------------------------------------------------------

_RE_A_COMPLETER = re.compile(r"\[\s*à compléter\s*:([^\]]*)\]")


def _exporter_html(dossier: Path, sections: list[dict]) -> Path:
    analyse = "\n\n".join(
        _lire_markdown(dossier / nom)
        for nom in ("02-analyse.md", "03-go-no-go.md")
    )
    onglets = [("Analyse", _vers_html(analyse))]
    parties_memoire: list[str] = []
    for section in sections:
        fichier = (dossier / "sections" / section["fichier"]) \
            if section["fichier"] else None
        if fichier is None or not fichier.exists():
            parties_memoire.append(
                f"<p class='manquante'>[section {section['numero']} manquante : "
                f"{html.escape(section['titre'])}]</p>"
            )
            continue
        parties_memoire.append(
            _vers_html(_texte_pour_acheteur(fichier.read_text(encoding="utf-8")))
        )
    onglets.append(("Mémoire", "\n".join(parties_memoire)))
    page = _page_html(onglets, _releve_a_completer(dossier, sections))
    chemin = dossier / "export" / "dossier.html"
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text(page, encoding="utf-8")
    return chemin


def _lire_markdown(chemin: Path) -> str:
    if not chemin.exists():
        return f"*(fichier {chemin.name} absent)*"
    return chemin.read_text(encoding="utf-8", errors="replace")


def _vers_html(texte: str) -> str:
    return markdown.markdown(texte, extensions=["tables"])


def _releve_a_completer(dossier: Path, sections: list[dict]) -> list[str]:
    fichiers = [dossier / "02-analyse.md", dossier / "03-go-no-go.md"]
    fichiers += [
        dossier / "sections" / s["fichier"] for s in sections if s["fichier"]
    ]
    releve: list[str] = []
    for fichier in fichiers:
        if not fichier.exists():
            continue
        texte = fichier.read_text(encoding="utf-8", errors="replace")
        for trouve in _RE_A_COMPLETER.finditer(texte):
            demande = trouve.group(1).strip()
            releve.append(f"{fichier.name} : [à compléter :{demande}]")
    return releve


_PAGE = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Réponse — dossier de consultation</title>
<style>
  body {{ font-family: system-ui, -apple-system, sans-serif; margin: 0 auto;
         max-width: 60rem; padding: 0 1rem 3rem; color: #1c2430;
         background: #f7f8fa; line-height: 1.55; }}
  h1 {{ font-size: 1.4rem; margin: 1.5rem 0 .5rem; }}
  nav {{ display: flex; gap: .4rem; border-bottom: 2px solid #d7dce3;
        margin: 1rem 0 1.5rem; }}
  nav button {{ border: none; background: none; padding: .55rem .9rem;
        font-size: 1rem; cursor: pointer; color: #5a6472;
        border-bottom: 3px solid transparent; margin-bottom: -2px; }}
  nav button.actif {{ color: #103c8c; font-weight: 600;
        border-bottom-color: #103c8c; }}
  section.onglet {{ background: #fff; border: 1px solid #e3e7ec;
        border-radius: 8px; padding: 1.2rem 1.6rem; }}
  table {{ border-collapse: collapse; margin: .8rem 0; width: 100%; }}
  th, td {{ border: 1px solid #d7dce3; padding: .35rem .55rem;
        font-size: .95rem; text-align: left; vertical-align: top; }}
  th {{ background: #eef1f5; }}
  .manquante {{ color: #a33; }}
  aside {{ margin-top: 1.6rem; background: #fff7e8; border: 1px solid #ecd9ad;
        border-radius: 8px; padding: .8rem 1.2rem; }}
  aside ul {{ margin: .4rem 0 0; padding-left: 1.2rem; }}
  code {{ background: #eef1f5; border-radius: 4px; padding: .05rem .3rem; }}
</style>
</head>
<body>
<h1>Réponse à la consultation</h1>
<nav>
{boutons}
</nav>
{corps}
{releve}
<script>
function afficherOnglet(id) {{
  document.querySelectorAll('.onglet').forEach(
    function (el) {{ el.hidden = el.id !== id; }});
  document.querySelectorAll('nav button').forEach(function (b) {{
    b.classList.toggle('actif', b.dataset.cible === id);
  }});
}}
</script>
</body>
</html>
"""


_CLASSE_ACTIF = ' class="actif"'


def _page_html(onglets: list[tuple[str, str]], releve: list[str]) -> str:
    boutons = "\n".join(
        f"<button type='button' data-cible='onglet-{index}'"
        f"{_CLASSE_ACTIF if index == 0 else ''} "
        f"onclick=\"afficherOnglet('onglet-{index}')\">"
        f"{html.escape(titre)}</button>"
        for index, (titre, _) in enumerate(onglets)
    )
    corps = "\n".join(
        f"<section class='onglet' id='onglet-{index}'"
        f"{' hidden' if index else ''}>{corps}</section>"
        for index, (_, corps) in enumerate(onglets)
    )
    if releve:
        bloc_releve = (
            "<aside><strong>Informations manquantes à fournir par "
            "l'entreprise</strong><ul>"
            + "".join(f"<li>{html.escape(ligne)}</li>" for ligne in releve)
            + "</ul></aside>"
        )
    else:
        bloc_releve = ""
    return _PAGE.format(boutons=boutons, corps=corps, releve=bloc_releve)
