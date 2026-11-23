"""Formulaires de candidature DC1/DC2/DC4 : préparation des valeurs et remplissage.

`preparer` crée `candidature/valeurs.json` (une entrée par formulaire, chaque
champ à null) et ne remplace jamais un fichier existant. `remplir` lit ces
valeurs et écrit `DC1.docx`, `DC2.docx` et `DC4.docx` dans le dossier de remise
(DC4 seulement si une sous-traitance est déclarée), en écrivant dans le XML
des formulaires officiels vierges de `cerfa/` :

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

from collections.abc import Iterable
import importlib.resources
import io
import json
import re
import zipfile
from pathlib import Path
from tempfile import NamedTemporaryFile
from xml.etree import ElementTree
from xml.sax.saxutils import escape

from remporte import espace, livraison

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
_CONFIRMER = ("{nom} existe déjà dans le dossier de remise : "
              "il a peut-être été retouché. Confirmez le remplacement.")


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


def remplir(dossier: Path, lot: str | None = None, *, remplacer: bool = False) -> dict:
    """Écrit les formulaires renseignés dans le dossier de remise. Rend les chemins
    produits, les champs non remplis, les optionnels vides, les champs à porter
    à la main et les anomalies (ancre ou case introuvable)."""
    dossier = Path(dossier).resolve()
    chemin_valeurs = dossier / "candidature" / "valeurs.json"
    if not chemin_valeurs.exists():
        raise espace.Erreur(
            f"{chemin_valeurs} est absent : lancez `remporte candidature "
            "preparer` d'abord, complétez valeurs.json, puis relancez."
        )
    try:
        valeurs = json.loads(chemin_valeurs.read_text(encoding="utf-8"))
    except (OSError, ValueError) as erreur:
        raise espace.Erreur("Les valeurs de candidature sont illisibles.") from erreur
    if not isinstance(valeurs, dict):
        raise espace.Erreur("Les valeurs de candidature sont illisibles.")
    try:
        remise = livraison.chemin_dossier_lot(dossier, lot)
    except OSError as erreur:
        raise espace.Erreur("Le dossier de remise est inaccessible.") from erreur
    resultat: dict = {
        "produits": [],
        "non_produits": [],
        "non_remplis": {},
        "optionnels_vides": {},
        "manuels": {},
        "anomalies": {},
    }
    formulaires = cartes()["formulaires"]
    cibles = {formulaire: remise / f"{formulaire}.docx" for formulaire in formulaires}
    _verifier_cibles(cibles.values(), remplacer)
    documents = {}
    for formulaire, info in formulaires.items():
        valeurs_formulaire = valeurs.get(formulaire, {})
        renseigne = valeurs_formulaire.get("champs", {}) if isinstance(valeurs_formulaire, dict) else None
        if not isinstance(renseigne, dict) or any(not isinstance(c, dict) for c in renseigne.values()):
            raise espace.Erreur(f"Les valeurs de candidature du {formulaire} sont illisibles.")
        if formulaire == "DC4" and renseigne.get("sous_traitance", {}).get(
            "valeur"
        ) is not True:
            resultat["non_produits"].append({
                "formulaire": formulaire,
                "motif": "pas de sous-traitance déclarée",
            })
            continue
        cible = cibles[formulaire]
        xml = _remplir_formulaire(formulaire, info, renseigne, resultat)
        documents[cible] = (info["fichier"], xml)
        resultat["produits"].append({
            "formulaire": formulaire,
            "chemin": cible.relative_to(dossier).as_posix(),
        })

    _ecrire_formulaires(remise, documents, cibles.values(), remplacer)
    return resultat


def _ecrire_formulaires(remise: Path, documents: dict[Path, tuple[str, str]],
                        cibles: Iterable[Path], remplacer: bool) -> None:
    temporaires: dict[Path, Path] = {}
    crees: list[Path] = []
    cible_creation = None
    try:
        remise.mkdir(parents=True, exist_ok=True)
        for cible, (modele, xml) in documents.items():
            with NamedTemporaryFile(dir=remise, delete=False) as fichier:
                temporaire = Path(fichier.name)
            temporaires[cible] = temporaire
            _ecrire_docx(modele, xml, temporaire)
        _verifier_cibles(cibles, remplacer)
        for cible, temporaire in temporaires.items():
            if remplacer:
                temporaire.replace(cible)
            else:
                # La création du lien refuse une cible apparue entre le contrôle et l'écriture.
                cible_creation = cible
                cible.hardlink_to(temporaire)
                crees.append(cible)
    except OSError as erreur:
        for cree in crees:
            if cree.exists() and cree.samefile(temporaires[cree]):
                cree.unlink()
        if isinstance(erreur, FileExistsError) and cible_creation is not None:
            raise espace.Erreur(_CONFIRMER.format(nom=cible_creation.name)) from erreur
        raise espace.Erreur("Impossible d'enregistrer les formulaires dans le dossier de remise.") from erreur
    finally:
        for temporaire in temporaires.values():
            temporaire.unlink(missing_ok=True)


def _verifier_cibles(cibles: Iterable[Path], remplacer: bool) -> None:
    for cible in cibles:
        presente = cible.exists() or cible.is_symlink()
        if presente and not remplacer:
            raise espace.Erreur(_CONFIRMER.format(nom=cible.name))
        if presente and not cible.is_file():
            raise espace.Erreur(f"Impossible de remplacer {cible.name} dans le dossier de remise.")


# ---------------------------------------------------------------------------
# Remplissage d'un formulaire
# ---------------------------------------------------------------------------

def _remplir_formulaire(formulaire: str, info: dict, renseigne: dict, resultat: dict) -> str:
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
            if not isinstance(valeur, str) or valeur not in options:
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

    _controler_xml(xml, formulaire)
    return xml


def _xml_vierge(nom_fichier: str) -> str:
    ressource = importlib.resources.files("remporte") / "cerfa" / nom_fichier
    with zipfile.ZipFile(io.BytesIO(ressource.read_bytes())) as archive:
        return archive.read("word/document.xml").decode("utf-8")


def _controler_xml(xml: str, formulaire: str) -> None:
    try:
        ElementTree.fromstring(xml)
    except ElementTree.ParseError as erreur:
        raise espace.Erreur(
            f"Impossible de remplir {formulaire}. Vérifiez les valeurs de candidature."
        ) from erreur


def _ecrire_docx(nom_fichier: str, xml: str, cible: Path) -> None:
    """Reconstruit le docx du formulaire avec le document.xml modifié."""
    ressource = importlib.resources.files("remporte") / "cerfa" / nom_fichier
    with zipfile.ZipFile(io.BytesIO(ressource.read_bytes())) as archive:
        contenu = {nom: archive.read(nom) for nom in archive.namelist()}
    contenu["word/document.xml"] = xml.encode("utf-8")
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
