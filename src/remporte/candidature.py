"""Formulaires de candidature DC1/DC2/DC4 : préparation des valeurs et remplissage.

`preparer` crée `candidature/valeurs.json` (une entrée par formulaire, chaque
champ à null) et ne remplace jamais un fichier existant. `remplir` lit ces
valeurs et écrit `candidature/DC1.docx`, `DC2.docx` et `DC4.docx` (ce dernier
seulement si une sous-traitance est déclarée), en écrivant dans le XML des
formulaires officiels vierges de `cerfa/` :

- texte : la valeur est ajoutée à la fin du paragraphe repéré par l'ancre de
  la carte (les libellés Cerfa sont coupés entre plusieurs runs : on ne
  remplace jamais dans un run, on concatène le paragraphe) ;
- case à cocher : cochée par index 1-based dans l'ordre du document. DC1 et
  DC2 portent des champs de formulaire `<w:checkBox>` ; les cases du DC4 sont
  des formes dessinées, cochées en les noircissant (choix DrawingML et repli
  VML modifiés ensemble).

Un champ sans valeur reste vide et est listé ; le fichier produit est un zip
reconstruit à l'identique, contrôlé comme XML bien formé.
"""

from __future__ import annotations

import importlib.resources
import io
import json
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree
from xml.sax.saxutils import escape

from remporte import espace

_RE_PARAGRAPHE = re.compile(r"<w:p[ >].*?</w:p>", re.S)
_RE_TEXTE = re.compile(r"(?P<ouvrant><w:t[^>]*>)(?P<texte>[^<]*)(?P<fermant></w:t>)")
_RE_TEXTE_PLAIN = re.compile(r"<w:t[^>]*>([^<]*)</w:t>")
_RE_CASE = re.compile(r"<w:checkBox>.*?</w:checkBox>", re.S)
_RE_BLOC_DESSINE = re.compile(r"<mc:AlternateContent>.*?</mc:AlternateContent>", re.S)

# Les cases du DC4 sont les seules formes dessinées de cette géométrie
# (carré de 11,7 pt, `filled="f"`) ; les autres blocs dessinés (traits,
# encadrés) en diffèrent.
_GEOMETRIE_CASE_DC4 = 'coordsize="147955,147955"'
_SEPARATEUR = "  "  # double espace entre le libellé et la valeur ajoutée


def cartes() -> dict:
    """Contenu de `cerfa/cartes.json` : formulaires, champs, ancres et cases."""
    ressource = importlib.resources.files("remporte") / "cerfa" / "cartes.json"
    return json.loads(ressource.read_text(encoding="utf-8"))


def preparer(dossier: Path) -> Path:
    """Crée `candidature/valeurs.json` avec chaque champ à null. Jamais de
    remplacement d'un fichier existant."""
    dossier = Path(dossier)
    if not (dossier / ".remporte").is_dir():
        raise espace.Erreur(
            f"{dossier} n'est pas un dossier de réponse (pas de .remporte/). "
            "Lancez `remporte init <DCE>` d'abord."
        )
    cible = dossier / "candidature" / "valeurs.json"
    if cible.exists():
        raise espace.Erreur(
            f"{cible} existe déjà. Complétez-le tel quel ; il n'est jamais "
            "remplacé par l'outil."
        )
    valeurs = {
        formulaire: {
            "fichier": info["fichier"],
            "label": info["label"],
            "champs": {
                champ["var"]: {
                    "rubrique": champ["rubrique"],
                    "label": champ["label"],
                    "type": champ["type"],
                    "options": champ.get("options"),
                    "valeur": None,
                }
                for champ in info["champs"]
            },
        }
        for formulaire, info in cartes()["formulaires"].items()
    }
    cible.parent.mkdir(parents=True, exist_ok=True)
    cible.write_text(
        json.dumps(valeurs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return cible


def remplir(dossier: Path) -> dict:
    """Écrit les formulaires renseignés dans `candidature/`. Rend les chemins
    produits, les champs non remplis, les optionnels vides, les champs à porter
    à la main et les anomalies (ancre ou case introuvable)."""
    dossier = Path(dossier)
    chemin_valeurs = dossier / "candidature" / "valeurs.json"
    if not chemin_valeurs.exists():
        raise espace.Erreur(
            f"{chemin_valeurs} est absent : lancez `remporte candidature "
            "preparer` d'abord, complétez valeurs.json, puis relancez."
        )
    valeurs = json.loads(chemin_valeurs.read_text(encoding="utf-8"))
    resultat: dict = {
        "produits": [],
        "non_produits": [],
        "non_remplis": {},
        "optionnels_vides": {},
        "manuels": {},
        "anomalies": {},
    }
    for formulaire, info in cartes()["formulaires"].items():
        renseigne = valeurs.get(formulaire, {}).get("champs", {})
        if formulaire == "DC4" and renseigne.get("sous_traitance", {}).get(
            "valeur"
        ) is not True:
            resultat["non_produits"].append({
                "formulaire": formulaire,
                "motif": "pas de sous-traitance déclarée "
                         "(champ sous_traitance de valeurs.json)",
            })
            continue
        _remplir_formulaire(dossier, formulaire, info, renseigne, resultat)
    return resultat


# ---------------------------------------------------------------------------
# Remplissage d'un formulaire
# ---------------------------------------------------------------------------

def _remplir_formulaire(dossier: Path, formulaire: str, info: dict,
                        renseigne: dict, resultat: dict) -> None:
    non_remplis: list[str] = []
    optionnels_vides: list[str] = []
    manuels: list[str] = []
    anomalies: dict[str, str] = {}
    xml = _xml_vierge(info["fichier"])
    for champ in info["champs"]:
        var = champ["var"]
        valeur = renseigne.get(var, {}).get("valeur")
        if champ["type"] == "manuelle":
            manuels.append(var)
            continue
        if valeur is None or valeur == "":
            (optionnels_vides if champ.get("optionnel") else non_remplis).append(var)
            continue
        erreur = None
        if champ["type"] == "texte":
            xml, erreur = _ecrire_texte(xml, champ, str(valeur))
        elif champ["type"] == "pointilles":
            xml, erreur = _ecrire_pointilles(xml, champ, str(valeur))
        elif champ["type"] == "choix":
            options = champ.get("options") or {}
            if valeur not in options:
                erreur = f"valeur « {valeur} » hors choix : {', '.join(options)}"
            else:
                xml, erreur = (_noircir_case_dessinee(xml, options[valeur])
                               if formulaire == "DC4"
                               else _cocher_case(xml, options[valeur]))
        elif champ["type"] == "drapeau":
            continue  # déjà traité (déclencheur de production du DC4)
        if erreur:
            anomalies[var] = erreur
    if anomalies:
        resultat["anomalies"][formulaire] = anomalies
    if non_remplis:
        resultat["non_remplis"][formulaire] = non_remplis
    if optionnels_vides:
        resultat["optionnels_vides"][formulaire] = optionnels_vides
    if manuels:
        resultat["manuels"][formulaire] = manuels

    _controler_xml(xml, formulaire, info["fichier"])
    cible = dossier / "candidature" / f"{formulaire}.docx"
    _ecrire_docx(info["fichier"], xml, cible)
    resultat["produits"].append({
        "formulaire": formulaire,
        "chemin": cible.relative_to(dossier).as_posix(),
    })


def _xml_vierge(nom_fichier: str) -> str:
    ressource = importlib.resources.files("remporte") / "cerfa" / nom_fichier
    with zipfile.ZipFile(io.BytesIO(ressource.read_bytes())) as archive:
        return archive.read("word/document.xml").decode("utf-8")


def _controler_xml(xml: str, formulaire: str, nom_fichier: str) -> None:
    try:
        ElementTree.fromstring(xml)
    except ElementTree.ParseError as erreur:
        raise espace.Erreur(
            f"{formulaire} ({nom_fichier}) : XML invalide après remplissage "
            f"({erreur}). Aucun fichier n'a été écrit."
        ) from erreur


def _ecrire_docx(nom_fichier: str, xml: str, cible: Path) -> None:
    """Reconstruit le docx du formulaire avec le document.xml modifié."""
    ressource = importlib.resources.files("remporte") / "cerfa" / nom_fichier
    with zipfile.ZipFile(io.BytesIO(ressource.read_bytes())) as archive:
        contenu = {nom: archive.read(nom) for nom in archive.namelist()}
    contenu["word/document.xml"] = xml.encode("utf-8")
    cible.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(cible, "w", zipfile.ZIP_DEFLATED) as sortie:
        for nom, donnees in contenu.items():
            sortie.writestr(nom, donnees)


# ---------------------------------------------------------------------------
# Écritures dans le XML
# ---------------------------------------------------------------------------

def _paragraphe_cible(xml: str, ancre: str, occurrence: int
                      ) -> re.Match | None:
    """N-ième paragraphe dont le texte concaténé contient l'ancre."""
    vues = 0
    for trouve in _RE_PARAGRAPHE.finditer(xml):
        texte = "".join(_RE_TEXTE_PLAIN.findall(trouve.group(0)))
        if ancre in texte:
            vues += 1
            if vues == occurrence:
                return trouve
    return None


def _ecrire_texte(xml: str, champ: dict, valeur: str) -> tuple[str, str | None]:
    """Ajoute la valeur à la fin du paragraphe repéré par l'ancre (dans le
    dernier run texte, jamais au milieu d'un libellé coupé entre runs)."""
    ancre = champ["ancre"]
    occurrence = champ.get("occurrence", 1)
    trouve = _paragraphe_cible(xml, ancre, occurrence)
    if trouve is None:
        return xml, f"ancre introuvable : « {ancre} » (occurrence {occurrence})"
    paragraphe = trouve.group(0)
    runs = list(_RE_TEXTE.finditer(paragraphe))
    if not runs:
        return xml, f"ancre « {ancre} » : paragraphe sans texte modifiable"
    dernier = runs[-1]
    ouvrant = dernier.group("ouvrant")
    if "xml:space" not in ouvrant:
        ouvrant = ouvrant[:-1] + ' xml:space="preserve">'
    remplace = (ouvrant + dernier.group("texte")
                + escape(_SEPARATEUR + valeur) + dernier.group("fermant"))
    nouveau = paragraphe[:dernier.start()] + remplace + paragraphe[dernier.end():]
    return xml[:trouve.start()] + nouveau + xml[trouve.end():], None


def _ecrire_pointilles(xml: str, champ: dict, valeur: str) -> tuple[str, str | None]:
    """Écrit la valeur dans les pointillés qui suivent l'ancre (DC1 : lot n°)."""
    ancre = champ["ancre"]
    occurrence = champ.get("occurrence", 1)
    trouve = _paragraphe_cible(xml, ancre, occurrence)
    if trouve is None:
        return xml, f"ancre introuvable : « {ancre} » (occurrence {occurrence})"
    paragraphe = trouve.group(0)
    motif = re.compile(re.escape(ancre) + r"[…. \s]+")
    nouveau, nombre = motif.subn(
        lambda m: ancre + " " + escape(valeur) + " ", paragraphe, count=1
    )
    if nombre == 0:
        return xml, f"pointillés introuvables après « {ancre} »"
    return xml[:trouve.start()] + nouveau + xml[trouve.end():], None


def _cocher_case(xml: str, index: int) -> tuple[str, str | None]:
    """Coche le n-ième champ `<w:checkBox>` (ordre du document) en insérant
    `<w:checked w:val="1"/>` juste après l'ouverture (ordre du schéma)."""
    cases = list(_RE_CASE.finditer(xml))
    if not 1 <= index <= len(cases):
        return xml, f"case {index} absente (le formulaire en compte {len(cases)})"
    bloc = cases[index - 1]
    contenu = bloc.group(0)
    if "<w:checked" in contenu:
        contenu = re.sub(r"<w:checked[^>]*/>", '<w:checked w:val="1"/>', contenu)
    else:
        contenu = contenu.replace(
            "<w:checkBox>", '<w:checkBox><w:checked w:val="1"/>', 1
        )
    return xml[:bloc.start()] + contenu + xml[bloc.end():], None


def _noircir_case_dessinee(xml: str, index: int) -> tuple[str, str | None]:
    """Noircit la n-ième case dessinée du DC4 (ordre du document) : les cases
    sont des formes présentes en double (choix DrawingML + repli VML), les
    deux représentations sont modifiées pour rester cohérentes. Le filtre ne
    regarde que la géométrie : une case déjà noircie doit rester à son rang,
    sinon les index des cases suivantes décaleraient."""
    cases = [m for m in _RE_BLOC_DESSINE.finditer(xml)
             if _GEOMETRIE_CASE_DC4 in m.group(0)]
    if not 1 <= index <= len(cases):
        return xml, f"case {index} absente (le formulaire en compte {len(cases)})"
    bloc = cases[index - 1]
    contenu = bloc.group(0)
    contenu = contenu.replace(
        'filled="f"', 'filled="t" fillcolor="#000000"', 1
    )
    contenu = contenu.replace(
        "</a:custGeom>",
        '</a:custGeom><a:solidFill><a:srgbClr val="000000"/></a:solidFill>', 1
    )
    return xml[:bloc.start()] + contenu + xml[bloc.end():], None
