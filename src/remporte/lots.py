"""Tri des pièces, choix des lots et suivi des analyses du DCE."""

from __future__ import annotations

import datetime
import hashlib
import html
import importlib.resources
import json
import re
import unicodedata
import webbrowser
from difflib import get_close_matches
from pathlib import Path
from tempfile import NamedTemporaryFile

from remporte import charte, espace
from remporte.espace import Erreur

RUBRIQUES = (
    "En bref",
    "Identité",
    "Ce que l'acheteur attend vraiment",
    "Critères et pondérations",
    "Pièces à remettre et formes imposées",
    "Incohérences entre pièces",
    "Pièces illisibles ou absentes",
    "Documents de référence et versions",
    "Avis",
)

_TRI = Path("memoire/lots.json")
_TRI_ENREGISTRE = Path(".remporte/lots.json")
_AVIS = {"repondre": "Répondre", "a_discuter": "À discuter",
         "ne_pas_repondre": "Ne pas répondre"}
_TYPES = ("RC", "CCAP", "CCTP", "DPGF", "BPU", "plan", "autre")
_LIGNE_INVENTAIRE = re.compile(r"^(\| [^|]+ \| )[^|]*( \| `(dce/[^`]+)` \|)", re.M)
_FRAGMENT_INTERNE = re.compile(
    r"\b[\w.-]+\.(?:md|json)\b|(?<!\w)(?:dce|analyse|\.remporte)/"
    r"|\bremporte\s+(?:init|etat|pieces|lire|chercher|formats|cadre|lots|livraison|"
    r"candidature|exporter|base|espace|fiche|html|guide)\b", re.IGNORECASE,
)
_ILLISIBLE = object()


def _texte(valeur) -> bool:
    return isinstance(valeur, str) and bool(valeur.strip())


def _json(donnees) -> str:
    return json.dumps(donnees, ensure_ascii=False, indent=2) + "\n"


def _texte_fichier(chemin: Path) -> str:
    try:
        return chemin.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise Erreur(f"Le fichier {chemin.name} est absent.") from None
    except (OSError, UnicodeError):
        raise Erreur(f"Le fichier {chemin.name} est illisible.") from None


def _objet_sans_doublon(paires: list[tuple[str, object]]) -> dict:
    objet = {}
    for nom, valeur in paires:
        if nom in objet:
            if nom.startswith("dce/"):
                raise Erreur(f"La pièce {nom} figure deux fois dans le relevé.")
            raise Erreur("Le tri des lots contient une information en double.")
        objet[nom] = valeur
    return objet


def _lire_objet(chemin: Path) -> dict:
    try:
        donnees = json.loads(_texte_fichier(chemin), object_pairs_hook=_objet_sans_doublon)
    except ValueError:
        donnees = None
    if not isinstance(donnees, dict):
        raise Erreur(f"Le fichier {chemin.name} est illisible.")
    return donnees


def _normaliser_chemin(chemin: str) -> str:
    return re.sub(r" +", " ", unicodedata.normalize("NFC", chemin))


def _chemins_du_dce(inventaire: dict[str, dict]):
    variantes: dict[str, list[str]] = {}
    for chemin in inventaire:
        variantes.setdefault(_normaliser_chemin(chemin), []).append(chemin)

    def resoudre(chemin) -> str:
        if not _texte(chemin) or not chemin.startswith("dce/") or "\\" in chemin:
            raise Erreur(f"Chemin de pièce du DCE invalide : {chemin}.")
        if any(partie in ("", ".", "..") for partie in chemin.split("/")):
            raise Erreur(f"Chemin de pièce du DCE invalide : {chemin}.")
        if chemin in inventaire:
            return chemin
        normalise = _normaliser_chemin(chemin)
        correspondances = variantes.get(normalise, [])
        if len(correspondances) == 1:
            return correspondances[0]
        if correspondances:
            raise Erreur(f"Plusieurs pièces correspondent à {chemin} : "
                         f"{', '.join(correspondances)}.")
        proches = get_close_matches(normalise, variantes, n=1, cutoff=0)
        indication = f" Pièce la plus proche : {variantes[proches[0]][0]}." if proches else ""
        raise Erreur(f"Pièce inconnue : {chemin}.{indication}")

    return resoudre


def _ids(tri: dict) -> list[str]:
    return [lot["id"] for lot in tri["lots"]]


def _valider_lots(tri: dict) -> list[str]:
    if type(tri.get("schema_version")) is not int or tri["schema_version"] != 1:
        raise Erreur("La version du tri des lots doit être 1.")
    if tri.get("allotissement") not in ("lots", "unique"):
        raise Erreur("Précisez si le marché est alloti ou s'il comporte un lot unique.")
    if not isinstance(tri.get("lots"), list) or not tri["lots"]:
        raise Erreur("Le tri doit contenir au moins un lot.")
    ids: list[str] = []
    for lot in tri["lots"]:
        identifiant = lot.get("id") if isinstance(lot, dict) else None
        if not _texte(identifiant):
            raise Erreur(f"Renseignez l'identifiant du lot n° {len(ids) + 1}.")
        if identifiant in (".", "..") or not re.fullmatch(r"[\w. -]+", identifiant):
            raise Erreur(f"Identifiant de lot invalide : {identifiant}.")
        if identifiant in ids:
            raise Erreur(f"Le lot {identifiant} figure deux fois dans le tri.")
        ids.append(identifiant)
        if not _texte(lot.get("intitule")):
            raise Erreur(f"Renseignez l'intitulé du lot {identifiant}.")
        avis = lot.get("recommandation")
        code = avis.get("avis") if isinstance(avis, dict) else None
        if not isinstance(code, str) or code not in _AVIS:
            raise Erreur(f"L'avis sur le lot {identifiant} doit être Répondre, À discuter "
                         "ou Ne pas répondre.")
        if not _texte(avis.get("raison")):
            raise Erreur(f"Renseignez la raison de l'avis sur le lot {identifiant}.")
    if tri["allotissement"] == "unique":
        if ids != ["unique"]:
            raise Erreur("Un marché non alloti doit contenir un seul lot, nommé « unique ».")
    elif "unique" in ids:
        raise Erreur("Le lot « unique » est réservé aux marchés non allotis.")
    return ids


def _lire_tri(dossier: Path) -> dict:
    tri = _lire_objet(dossier / _TRI)
    ids = _valider_lots(tri)
    pieces = _lire_objet(dossier / ".remporte/etat.json").get("pieces")
    if not isinstance(pieces, list) or any(
        not isinstance(piece, dict) or not _texte(piece.get("chemin"))
        or not _texte(piece.get("statut")) for piece in pieces
    ):
        raise Erreur("L'inventaire des pièces du DCE est illisible.")
    inventaire = {f"dce/{piece['chemin']}": piece for piece in pieces}
    resoudre = _chemins_du_dce(inventaire)

    def chemins(valeur, libelle: str) -> list[str]:
        if not isinstance(valeur, list):
            raise Erreur(f"Renseignez la liste des {libelle}.")
        return [resoudre(chemin) for chemin in valeur]

    reparties = set()
    for lot in tri["lots"]:
        identifiant = lot["id"]
        liees = lot.get("parties_communes")
        if not isinstance(liees, list):
            raise Erreur(f"Renseignez les lots qui ont une partie commune avec le lot {identifiant}.")
        for autre in liees:
            if autre == identifiant or autre not in ids:
                raise Erreur(f"Partie commune du lot {identifiant} : lot {autre} invalide.")
        lot["pieces"] = chemins(lot.get("pieces"), f"pièces du lot {identifiant}")
        reparties.update(lot["pieces"])
    tri["pieces_communes"] = chemins(tri.get("pieces_communes"), "pièces communes")
    tri["pieces_illisibles"] = chemins(tri.get("pieces_illisibles"), "pièces illisibles")
    lisibles = {chemin for chemin, piece in inventaire.items() if piece["statut"] == "ok"}
    declarees = lisibles.intersection(tri["pieces_illisibles"])
    if declarees:
        raise Erreur(f"Pièces lisibles déclarées illisibles : {', '.join(sorted(declarees))}.")
    restantes = lisibles - reparties - set(tri["pieces_communes"])
    if restantes:
        raise Erreur(f"Pièces lisibles non réparties : {', '.join(sorted(restantes))}.")

    types = tri.get("types_pieces")
    if not isinstance(types, dict):
        raise Erreur("Renseignez le type de chaque pièce lisible du DCE.")
    normalises: dict[str, str] = {}
    for chemin, type_piece in types.items():
        chemin = resoudre(chemin)
        if type_piece not in _TYPES:
            raise Erreur(f"Type de pièce inconnu pour {chemin} : {type_piece}.")
        if chemin in normalises and normalises[chemin] != type_piece:
            raise Erreur(f"Deux types différents sont indiqués pour {chemin}.")
        normalises[chemin] = type_piece
    manquants = lisibles - normalises.keys()
    if manquants:
        raise Erreur(f"Type manquant pour les pièces : {', '.join(sorted(manquants))}.")
    tri["types_pieces"] = normalises
    return tri


def _preuve(tri: dict) -> dict:
    contenu = json.dumps(tri, sort_keys=True).encode("ascii")
    return {"empreinte": hashlib.sha256(contenu).hexdigest(), "choix": tri["choix"]}


def _preuve_enregistree(dossier: Path) -> dict:
    chemin = dossier / _TRI_ENREGISTRE
    if not chemin.exists():
        return {}
    preuve = _lire_objet(chemin)
    choix = preuve.get("choix")
    if "choix" not in preuve or not _texte(preuve.get("empreinte")) or (
        choix is not None and (
            not isinstance(choix, dict) or not isinstance(choix.get("retenus"), list)
            or not choix["retenus"] or not all(map(_texte, choix["retenus"]))
            or not _texte(choix.get("par")) or not _texte(choix.get("date"))
        )
    ):
        raise Erreur("Le relevé du choix des lots est illisible.")
    return preuve


def lire(dossier: Path) -> dict:
    """Lit le tri enregistré, après contrôle de l'inventaire actuel."""
    dossier = Path(dossier)
    tri = _lire_tri(dossier)
    if "choix" not in tri or _preuve_enregistree(dossier) != _preuve(tri):
        raise Erreur("Enregistrez le tri des lots avec « remporte lots enregistrer ».")
    return tri


def _ecrire(fichiers: dict[Path, str], *, nouveaux: tuple[Path, ...] = ()) -> None:
    """Prépare toutes les écritures avant de publier les fichiers un à un."""
    temporaires: dict[Path, Path] = {}
    chemin = next(iter(fichiers))
    try:
        for chemin in fichiers:
            if chemin.parent.resolve() != chemin.parent or (
                chemin not in nouveaux and (chemin.is_symlink() or chemin.is_dir())
            ):
                raise Erreur(f"Impossible d'écrire le fichier {chemin.name} dans le dossier de réponse.")
        for chemin, texte in fichiers.items():
            chemin.parent.mkdir(exist_ok=True)
            with NamedTemporaryFile(dir=chemin.parent, delete=False) as temporaire:
                temporaires[chemin] = Path(temporaire.name)
                temporaire.write(texte.encode("utf-8"))
        for chemin, temporaire in temporaires.items():
            if chemin in nouveaux:
                try:
                    chemin.hardlink_to(temporaire)
                except FileExistsError:
                    pass
            else:
                temporaire.replace(chemin)
    except (OSError, UnicodeError):
        raise Erreur(f"Impossible d'écrire le fichier {chemin.name} dans le dossier de réponse.") from None
    finally:
        for temporaire in temporaires.values():
            temporaire.unlink(missing_ok=True)


def enregistrer(dossier: Path) -> dict:
    dossier = Path(dossier).resolve()
    tri = _lire_tri(dossier)
    preuve = dossier / _TRI_ENREGISTRE
    choix = _preuve_enregistree(dossier).get("choix")
    if tri.get("choix") is not None and choix is None:
        raise Erreur("Laisser le choix des lots vide : seul l'utilisateur peut le renseigner.")
    if "choix" not in tri:
        raise Erreur("Le tri doit indiquer si le choix des lots a été fait.")
    ids = _ids(tri)
    disparus = [lot for lot in choix["retenus"] if lot not in ids] if choix else []
    tri["choix"] = None if disparus else choix
    morceaux: dict[str, list[str]] = {}
    for lot in tri["lots"]:
        for chemin in dict.fromkeys(lot["pieces"]):
            morceaux.setdefault(espace._nom(chemin), []).append(lot["id"])
    for chemin in tri["pieces_communes"]:
        morceaux[espace._nom(chemin)] = ["commun"]
    inventaire = dossier / "01-pieces.md"
    texte = _LIGNE_INVENTAIRE.sub(
        lambda ligne: ligne[1] + ", ".join(morceaux.get(ligne[3], ["—"])) + ligne[2],
        _texte_fichier(inventaire),
    )
    _ecrire({inventaire: texte, dossier / _TRI: _json(tri), preuve: _json(_preuve(tri))})
    resultat = {"lots": ids, "pieces_communes": len(tri["pieces_communes"]), "choix": tri["choix"]}
    if disparus:
        resultat["message"] = f"Choix des lots à refaire. Lots retirés du tri : {', '.join(disparus)}."
    return resultat


def _numero(identifiant: str) -> str | None:
    if not identifiant.isdecimal():
        return None
    return "".join(str(unicodedata.decimal(c)) for c in identifiant).lstrip("0") or "0"


def choisir(dossier: Path, demande: str, par: str) -> dict:
    dossier = Path(dossier).resolve()
    tri = lire(dossier)
    ids = _ids(tri)
    retenus: list[str] = []
    for valeur in demande.split(","):
        demande_id = valeur if valeur in ids else valeur.strip()
        if not demande_id:
            continue
        identifiant = demande_id
        if identifiant not in ids:
            numero = _numero(identifiant)
            equivalences = [lot for lot in ids if numero is not None and _numero(lot) == numero]
            if len(equivalences) != 1:
                raise Erreur(f"Lot inconnu : {demande_id}. Lots du DCE : {', '.join(ids)}.")
            identifiant = equivalences[0]
        if identifiant in retenus:
            raise Erreur(f"Le lot {identifiant} a été choisi deux fois.")
        retenus.append(identifiant)
    if not retenus:
        raise Erreur("La liste des lots à retenir est vide.")
    if not _texte(par):
        raise Erreur("Renseignez le nom de la personne qui choisit les lots.")

    gabarit = importlib.resources.files("remporte") / "gabarits" / "analyse-lot.md"
    modele = gabarit.read_text(encoding="utf-8")
    fichiers = {}
    for identifiant in retenus:
        base = dossier / "analyse" / f"lot-{identifiant}"
        for extension, contenu in (("md", modele), ("json", _json({"questions_acheteur": []}))):
            chemin = base.parent / f"{base.name}.{extension}"
            if not chemin.exists() and not chemin.is_symlink():
                fichiers[chemin] = contenu
    nouveaux = tuple(fichiers)
    tri["choix"] = {
        "retenus": retenus, "par": par.strip(),
        "date": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
    }
    fichiers[dossier / _TRI] = _json(tri)
    fichiers[dossier / _TRI_ENREGISTRE] = _json(_preuve(tri))
    _ecrire(fichiers, nouveaux=nouveaux)
    return {"choix": tri["choix"]}


def _titre(texte: str) -> str:
    return " ".join(texte.strip().rstrip(":").lower().replace("’", "'").split())


def _problemes_rubriques(texte: str) -> list[str]:
    attendues = [_titre(titre) for titre in RUBRIQUES]
    titres = [_titre(titre) for titre in re.findall(r"^##[ \t]+(.+)$", texte, re.M)]
    manquantes = [titre for titre in RUBRIQUES if _titre(titre) not in titres]
    problemes = []
    if manquantes:
        problemes.append(f"Rubriques manquantes : {', '.join(manquantes)}.")
    elif [titre for titre in titres if titre in attendues] != attendues:
        problemes.append("Respectez l'ordre des neuf rubriques de l'analyse.")
    if espace.MARQUEUR in texte:
        problemes.append("Des passages de l'analyse restent à remplir.")
    return problemes


def _controler_questions(questions: list) -> tuple[list[dict], list[str]]:
    deja_vus = set()
    conformes = []
    problemes = []
    for rang, question in enumerate(questions, 1):
        identifiant = question.get("id") if isinstance(question, dict) else None
        if not _texte(identifiant) or not re.fullmatch(r"I-[0-9]+", identifiant):
            detail = f" (« {identifiant} »)" if _texte(identifiant) else ""
            problemes.append(f"Question n° {rang}{detail} : indiquez un numéro comme I-1.")
            continue
        if identifiant in deja_vus:
            problemes.append(f"Question {identifiant} : ce numéro est déjà utilisé.")
            continue
        deja_vus.add(identifiant)
        contexte = question.get("contexte")
        texte = question.get("question")
        impact = question.get("impact_prix")
        sources = question.get("sources")
        erreurs = []
        if not _texte(contexte):
            erreurs.append("précisez le contexte")
        if not _texte(texte) or not texte.rstrip().endswith("?"):
            erreurs.append("rédigez une question qui se termine par un point d'interrogation")
        if not _texte(impact):
            erreurs.append("précisez l'incidence sur le prix")
        if not isinstance(sources, list) or not sources or not all(map(_texte, sources)):
            erreurs.append("citez les sources")
        fragments = [contexte, texte, *(sources if isinstance(sources, list) else [])]
        if any(isinstance(champ, str) and _FRAGMENT_INTERNE.search(champ) for champ in fragments):
            erreurs.append("retirez les références internes au dossier de travail")
        if erreurs:
            problemes.append(f"Question {identifiant} : {', '.join(erreurs)}.")
        else:
            conformes.append(question)
    return conformes, problemes


def _analyse(dossier: Path, identifiant: str) -> tuple[object, list[dict], list[str]]:
    racine = dossier / "analyse"
    try:
        texte = _texte_fichier(racine / f"lot-{identifiant}.md")
    except Erreur as erreur:
        problemes = [str(erreur)]
    else:
        problemes = _problemes_rubriques(texte)
    chemin = racine / f"lot-{identifiant}.json"
    try:
        contenu = json.loads(_texte_fichier(chemin))
    except Erreur as erreur:
        return _ILLISIBLE, [], [*problemes, str(erreur)]
    except ValueError:
        return _ILLISIBLE, [], [*problemes, f"Le fichier {chemin.name} est illisible."]
    questions = contenu.get("questions_acheteur") if isinstance(contenu, dict) else None
    if not isinstance(questions, list):
        return contenu, [], [*problemes, "Renseignez la liste des questions à l'acheteur."]
    conformes, erreurs = _controler_questions(questions)
    return contenu, conformes, problemes + erreurs


def _texte_html(texte: str) -> str:
    """Insère les textes du dossier comme du texte dans la page de lecture."""
    texte = html.escape(" ".join(texte.splitlines()), quote=False)
    return re.sub(r"[\\`*_{}\[\]()!#|~]", lambda m: f"&#{ord(m[0])};", texte)


def rapport(dossier: Path, *, ouvrir: bool = False) -> dict:
    dossier = Path(dossier).resolve()
    tri = lire(dossier)
    texte = ["# Rapport des lots"]
    for lot in tri["lots"]:
        avis = lot["recommandation"]
        texte += [f"## Lot {_texte_html(lot['id'])} – {_texte_html(lot['intitule'])}",
                  f"**{_AVIS[avis['avis']]}**\n\n{_texte_html(avis['raison'])}"]
    texte += ["## Pièces communes", "\n".join(f"- {_texte_html(p)}" for p in tri["pieces_communes"])
              or "Aucune pièce commune.", "## Lots retenus"]
    problemes = {}
    analyses = {}
    choix = tri["choix"]
    if choix is None:
        texte.append("Les lots restent à choisir.")
    else:
        ids = ", ".join(choix["retenus"])
        texte.append(f"Lots {_texte_html(ids)} choisis par {_texte_html(choix['par'])} "
                     f"le {_texte_html(choix['date'])}.")
        for identifiant in choix["retenus"]:
            contenu, questions, erreurs = _analyse(dossier, identifiant)
            if contenu is not _ILLISIBLE:
                analyses[identifiant] = contenu
            if erreurs:
                problemes[identifiant] = erreurs
            etape = "analyse en cours" if erreurs else "analyse prête"
            texte.append(f"### Lot {_texte_html(identifiant)} – {etape}")
            if erreurs:
                texte.append("\n".join(f"- {_texte_html(erreur)}" for erreur in erreurs))
            if questions:
                texte.append("**Questions à l'acheteur**")
            for question in questions:
                texte.extend((_texte_html(question["contexte"]), _texte_html(question["question"])))
    page = dossier / "memoire" / "rapport-lots.html"
    recueil = dossier / "memoire" / "lots-analyses.json"
    _ecrire({page: charte.page_depuis_markdown("\n\n".join(texte)),
             recueil: _json({"lots": analyses})})
    if ouvrir:
        webbrowser.open(page.as_uri())
    return {"html": str(page), "analyses": str(recueil), "problemes": problemes}


def etat(dossier: Path) -> dict:
    """État de l'analyse dans le dossier et pour chacun des lots retenus."""
    resultat: dict = {"etat": "a_faire", "disponibles": [], "choix": None, "analyses": {}}
    if not (dossier / _TRI).exists():
        if (dossier / "02-analyse.md").is_file():
            message = ("Analyse à refaire par lot : l'ancienne analyse unique reste lisible "
                       "comme note de travail.")
        else:
            message = "Analyse : lire le DCE et répartir les pièces par lot."
        return {**resultat, "message": message}
    try:
        tri = lire(dossier)
    except Erreur:
        return {**resultat, "message": "Analyse : vérifier et enregistrer la répartition des pièces par lot."}
    ids = _ids(tri)
    choix = tri["choix"]
    resultat.update(etat="en_cours", disponibles=ids, choix=choix)
    if choix is None:
        return {**resultat, "message": f"Analyse : lots à choisir ({', '.join(ids)})."}

    details = []
    for identifiant in choix["retenus"]:
        _, questions, erreurs = _analyse(dossier, identifiant)
        nombre = len(questions)
        resultat["analyses"][identifiant] = {"prete": not erreurs, "questions": nombre}
        libelle = "question" if nombre == 1 else "questions"
        detail = "en cours" if erreurs else f"prête ({nombre} {libelle} à l'acheteur)"
        details.append(f"lot {identifiant} {detail}")
    if all(analyse["prete"] for analyse in resultat["analyses"].values()):
        resultat["etat"] = "faite"
    resultat["message"] = (f"Analyse : lots retenus {', '.join(choix['retenus'])} — "
                           f"{', '.join(details)}.")
    return resultat
