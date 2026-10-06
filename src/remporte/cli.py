"""Interface en ligne de commande `remporte`.

Sortie texte lisible par défaut, `--json` pour un objet JSON unique sur stdout.
Codes retour : 0 succès, 1 erreur d'usage, 2 dossier de réponse introuvable.
"""

from __future__ import annotations

import argparse
import importlib.resources
import json
import re
import sys
from pathlib import Path

from remporte import __version__
from remporte import (
    cadre, candidature, charte, espace, export, formats, inventaire, lecture, recherche,
    lien, travail,
)


def main(argv: list[str] | None = None) -> int:
    parser = _construire_parser()
    args = parser.parse_args(argv)
    if getattr(args, "func", None) is None:
        parser.print_help()
        return 1
    try:
        return args.func(args)
    except espace.Erreur as erreur:
        print(f"Erreur : {erreur}", file=sys.stderr)
        return 1
    except Exception as erreur:  # noqa: BLE001 — jamais de trace Python brute
        print(f"Erreur : {type(erreur).__name__}: {erreur}", file=sys.stderr)
        return 1


# ---------------------------------------------------------------------------
# Construction du parseur
# ---------------------------------------------------------------------------

def _construire_parser() -> argparse.ArgumentParser:
    communes = argparse.ArgumentParser(add_help=False)
    communes.add_argument(
        "--json", action="store_true",
        help="sortie JSON unique sur stdout",
    )
    avec_dossier = argparse.ArgumentParser(add_help=False)
    avec_dossier.add_argument(
        "--dossier", metavar="CHEMIN",
        help="dossier de réponse (défaut : trouvé en remontant depuis le "
             "répertoire courant)",
    )

    parser = argparse.ArgumentParser(
        prog="remporte",
        description="Répondre à un appel d'offres publics avec votre agent IA : "
                    "lecture du DCE, analyse, plan, rédaction, export.",
    )
    parser.add_argument("--version", action="version",
                        version=f"remporte {__version__}")
    sous = parser.add_subparsers(dest="commande", metavar="commande")

    p = sous.add_parser(
        "init", parents=[communes],
        help="initialiser un dossier de réponse depuis un DCE (zip ou dossier)",
    )
    p.add_argument("source", metavar="DCE")
    p.add_argument(
        "--dossier", metavar="CHEMIN",
        help="dossier de réponse (défaut : <nom>-reponse/ dans le répertoire courant)",
    )
    p.add_argument(
        "--forcer", action="store_true",
        help="réindexer un dossier existant sans toucher aux fichiers remplis",
    )
    p.set_defaults(func=_cmd_init)

    p = sous.add_parser("etat", parents=[communes, avec_dossier],
                        help="état d'avancement des étapes")
    p.set_defaults(func=_cmd_etat)

    p = sous.add_parser("pieces", parents=[communes, avec_dossier],
                        help="inventaire des pièces du DCE")
    p.set_defaults(func=_cmd_pieces)

    p = sous.add_parser("lire", parents=[communes, avec_dossier],
                        help="texte converti d'une pièce (chemin contenant le "
                             "fragment, insensible à la casse)")
    p.add_argument("fragment", metavar="FRAGMENT")
    p.add_argument("--page", type=int, default=None, metavar="N",
                   help="ne rendre que la page N (PDF uniquement)")
    p.add_argument("--tout", action="store_true",
                   help="rendre tout le texte même d'une pièce longue")
    p.set_defaults(func=_cmd_lire)

    p = sous.add_parser("chercher", parents=[communes, avec_dossier],
                        help="retrouver un passage dans tout le DCE")
    p.add_argument("requete", metavar="TERMES")
    p.add_argument("--limite", type=int, default=5)
    p.set_defaults(func=_cmd_chercher)

    p = sous.add_parser("formats", parents=[communes, avec_dossier],
                        help="formats attendus par l'acheteur : soutenance, "
                             "pages, cadres Excel/Word à compléter")
    p.set_defaults(func=_cmd_formats)

    p_cand = sous.add_parser("candidature", parents=[communes],
                             help="formulaires DC1/DC2/DC4 officiels")
    sous_cand = p_cand.add_subparsers(dest="sous_commande", metavar="action",
                                      required=True)
    pc = sous_cand.add_parser("preparer", parents=[communes, avec_dossier],
                              help="créer candidature/valeurs.json (jamais "
                                   "remplacé s'il existe)")
    pc.set_defaults(func=_cmd_candidature_preparer)
    pc = sous_cand.add_parser("remplir", parents=[communes, avec_dossier],
                              help="écrire candidature/DC1.docx, DC2.docx et "
                                   "DC4.docx (si sous-traitance)")
    pc.set_defaults(func=_cmd_candidature_remplir)

    p = sous.add_parser("cadre", parents=[communes, avec_dossier],
                        help="trame de réponse imposée par l'acheteur (CRT)")
    p.add_argument("fragment", nargs="?", default=None, metavar="FRAGMENT",
                   help="pièce à analyser (défaut : la pièce classée CRT)")
    p.add_argument("--couverture", action="store_true",
                   help="exigences numérotées qu'aucune section ne cite encore")
    p.set_defaults(func=_cmd_cadre)

    p_base = sous.add_parser("base", parents=[communes],
                             help="base d'informations de l'entreprise")
    sous_base = p_base.add_subparsers(dest="sous_commande", metavar="action",
                                      required=True)
    pb = sous_base.add_parser("indexer", parents=[communes],
                              help="convertir et indexer un dossier de documents")
    pb.add_argument("source", metavar="DOSSIER", nargs="?", default=None,
                    help="défaut : ressources/ de l'espace de travail")
    pb.set_defaults(func=_cmd_base_indexer)
    pb = sous_base.add_parser("chercher", parents=[communes],
                              help="chercher dans la base entreprise")
    pb.add_argument("requete", metavar="TERMES")
    pb.add_argument("--limite", type=int, default=5)
    pb.set_defaults(func=_cmd_base_chercher)

    p = sous.add_parser("guide", help="méthode d'une étape (sans argument : liste)")
    p.add_argument("etape", nargs="?", default=None, metavar="ETAPE")
    p.set_defaults(func=_cmd_guide)

    p = sous.add_parser(
        "exporter", parents=[communes, avec_dossier],
        help="produire memoire.docx, dossier.html et les documents de travail "
             "(analyse, feuille de route, matrice de conformité)",
    )
    p.add_argument(
        "--formats",
        default="docx,html,analyse,feuille,matrice", metavar="LISTE",
        help="formats parmi docx,html,analyse,feuille,matrice (défaut : tous)",
    )
    p.set_defaults(func=_cmd_exporter)

    p = sous.add_parser("espace", parents=[communes],
                        help="créer un espace de travail : ressources/ et DCEs/")
    p.add_argument("chemin", nargs="?", default=".", metavar="CHEMIN",
                   help="défaut : le répertoire courant")
    p.set_defaults(func=_cmd_espace)

    p = sous.add_parser("fiche", parents=[communes],
                        help="fiche entreprise lue par les agents (créée par /remporte:init)")
    p.add_argument("--creer", action="store_true",
                   help="créer la fiche depuis le gabarit si elle n'existe pas")
    p.set_defaults(func=_cmd_fiche)

    p = sous.add_parser("html", parents=[communes],
                        help="mettre un fichier markdown en page HTML (charte Remporte)")
    p.add_argument("source", metavar="FICHIER.md")
    p.add_argument("-o", "--sortie", default=None, metavar="FICHIER.html",
                   help="défaut : même nom, extension .html")
    p.set_defaults(func=_cmd_html)

    p = sous.add_parser("offre", help="l'offre Remporte en un écran")
    p.set_defaults(func=_cmd_offre)

    return parser


# ---------------------------------------------------------------------------
# Aides
# ---------------------------------------------------------------------------

def _sortie_json(objet) -> None:
    print(json.dumps(objet, ensure_ascii=False, indent=2))


def _dossier_reponse(args) -> Path | None:
    """Dossier de réponse explicite ou trouvé en remontant depuis le cwd."""
    if getattr(args, "dossier", None):
        candidat = Path(args.dossier)
        if (candidat / ".remporte").is_dir():
            return candidat
        return None
    return espace.trouver_dossier(Path.cwd())


def _dossier_ou_code(args) -> tuple[Path | None, int]:
    dossier = _dossier_reponse(args)
    if dossier is None:
        cible = getattr(args, "dossier", None) or str(Path.cwd())
        print(
            f"Erreur : pas de dossier de réponse (.remporte/) dans {cible} "
            "ni au-dessus. Lancez `remporte init <DCE>` d'abord.",
            file=sys.stderr,
        )
        return None, 2
    return dossier, 0


def _etat_json(dossier: Path) -> dict | None:
    chemin = dossier / ".remporte" / "etat.json"
    if not chemin.exists():
        return None
    return json.loads(chemin.read_text(encoding="utf-8"))


def _nombre(n: int) -> str:
    return f"{n:,}".replace(",", " ")


def _tableau_texte(en_tetes: list[str], lignes: list[list[str]]) -> str:
    largeurs = [len(entete) for entete in en_tetes]
    for ligne in lignes:
        for i, cellule in enumerate(ligne):
            largeurs[i] = max(largeurs[i], len(cellule))

    def _ligne(cellules: list[str]) -> str:
        return "  ".join(
            cellule.ljust(largeurs[i]) for i, cellule in enumerate(cellules)
        ).rstrip()

    sortie = [_ligne(en_tetes), "  ".join("-" * l for l in largeurs)]
    sortie += [_ligne(ligne) for ligne in lignes]
    return "\n".join(sortie)


def _lire_ressource(*parties: str) -> str | None:
    ressource = importlib.resources.files("remporte")
    for partie in parties:
        ressource = ressource / partie
    if not ressource.is_file():
        return None
    return ressource.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Commandes
# ---------------------------------------------------------------------------

def _cmd_init(args) -> int:
    source = Path(args.source)
    if not source.exists():
        print(f"Erreur : source introuvable : {source}", file=sys.stderr)
        return 1
    racine = travail.trouver_espace()
    nom = source.stem or source.name
    if args.dossier:
        dossier = Path(args.dossier)
    elif racine is not None:
        dossier = racine / travail.DCES / nom
    else:
        dossier = Path.cwd() / f"{nom}-reponse"
    print(f"Initialisation depuis {source}…")
    donnees = espace.initialiser(source, dossier, forcer=args.forcer)
    if args.json:
        _sortie_json(donnees)
        return 0
    pieces = donnees["pieces"]
    lues = sum(1 for p in pieces if p["statut"] == "ok")
    print(f"Dossier de réponse : {dossier}")
    print(f"Pièces : {len(pieces)} ({lues} converties)")
    for message in inventaire.pieces_attendues_absentes({p["type"] for p in pieces}):
        print(f"  ! {message}")
    a_remplir = sorted({p["type"] for p in pieces} & espace.PIECES_REMPLISSABLES)
    if a_remplir:
        print(f"  Pièces à remplir dans le format de l'acheteur ({', '.join(a_remplir)}) : "
              f"disponible avec Remporte, {lien.site('init')}")
    print("Suite : remporte etat")
    return 0


def _cmd_etat(args) -> int:
    dossier, code = _dossier_ou_code(args)
    if dossier is None:
        return code
    etat = espace.etat(dossier)
    if args.json:
        _sortie_json(etat)
        return 0
    print(f"Dossier : {etat['dossier']}")
    for nom in espace.ETAPES:
        info = etat["etapes"][nom]
        detail = "" if info["marqueurs"] is None else f" ({info['marqueurs']} restants)"
        print(f"  {nom:<10} [{info['etat']}]{detail}")
    if etat["prochaine"]:
        print(f"Prochaine étape : {etat['prochaine']}")
        print(f"  {etat['commande']}")
    else:
        print("Toutes les étapes sont faites.")
    return 0


def _cmd_pieces(args) -> int:
    dossier, code = _dossier_ou_code(args)
    if dossier is None:
        return code
    donnees = _etat_json(dossier)
    if donnees is None:
        print(
            f"Erreur : {dossier} n'a pas d'inventaire (etat.json absent). "
            "Relancez `remporte init`.",
            file=sys.stderr,
        )
        return 1
    pieces = donnees["pieces"]
    if args.json:
        _sortie_json({"pieces": pieces})
        return 0
    lignes = [
        [p["type"], p["lot"] or "—", p["statut"],
         str(p["pages"]) if p["pages"] is not None else "—",
         _nombre(p["texte"]) if p["texte"] else "0", f"dce/{p['chemin']}"]
        for p in pieces
    ]
    print(_tableau_texte(
        ["Type", "Lot", "Statut", "Pages", "Texte", "Pièce"], lignes
    ))
    for p in pieces:
        if p["statut"] != "ok":
            print(f"  ! dce/{p['chemin']} : {p['statut']} — {p['motif']}")
    return 0


def _page_du_texte(texte: str, numero: int) -> str | None:
    parties = re.split(r"<!-- page (\d+) -->", texte)
    if numero == 1:
        return parties[0].strip() or None
    for i in range(1, len(parties), 2):
        if int(parties[i]) == numero:
            return parties[i + 1].strip() or None
    return None


def _cmd_lire(args) -> int:
    dossier, code = _dossier_ou_code(args)
    if dossier is None:
        return code
    donnees = _etat_json(dossier)
    if donnees is None:
        print(
            f"Erreur : {dossier} n'a pas d'inventaire (etat.json absent). "
            "Relancez `remporte init`.",
            file=sys.stderr,
        )
        return 1
    fragment = args.fragment.lower()
    # `remporte lire rc` doit trouver « Reglement de la consultation.pdf » :
    # un type de pièce connu se cherche d'abord dans l'inventaire.
    candidats = [p for p in donnees["pieces"] if p.get("type", "").lower() == fragment]
    if not candidats:
        candidats = [p for p in donnees["pieces"] if fragment in p["chemin"].lower()]
    if not candidats:
        print(f"Aucune pièce dont le chemin contient « {args.fragment} ».")
        print("Pièces du dossier :")
        for p in donnees["pieces"]:
            print(f"  dce/{p['chemin']}")
        return 1
    if len(candidats) > 1:
        print(f"{len(candidats)} pièces contiennent « {args.fragment} » :")
        for p in candidats:
            print(f"  dce/{p['chemin']}")
        print("Précisez le fragment.")
        return 1
    piece = candidats[0]
    if piece["statut"] != "ok":
        print(f"dce/{piece['chemin']} : {piece['statut']} — "
              f"{piece['motif'] or 'texte indisponible'}")
        return 1
    cache = dossier / ".remporte" / "texte" / (piece["chemin"] + ".md")
    if cache.exists():
        texte = cache.read_text(encoding="utf-8", errors="replace")
    else:
        conversion = lecture.convertir(dossier / "dce" / piece["chemin"])
        if conversion.statut != "ok":
            print(f"dce/{piece['chemin']} : {conversion.statut} — "
                  f"{conversion.motif or 'texte indisponible'}")
            return 1
        texte = conversion.texte
    if args.page is not None:
        extrait = _page_du_texte(texte, args.page)
        if extrait is None:
            print(f"Page {args.page} absente de dce/{piece['chemin']}.")
            return 1
        print(extrait)
        return 0
    if len(texte) > _SEUIL_PIECE_LONGUE and not args.tout:
        print(_sommaire(texte, piece["chemin"]))
        return 0
    print(texte)
    return 0


# Au-delà, une pièce lue d'un bloc coûte cher à l'agent (un CCTP fait souvent
# plusieurs centaines de milliers de caractères) : on rend d'abord son sommaire.
_SEUIL_PIECE_LONGUE = 30_000


def _sommaire(texte: str, chemin: str) -> str:
    """Titres de la pièce (ou première ligne de chaque page d'un PDF), avec la
    façon de lire la suite sans tout charger."""
    taille = f"{len(texte):,}".replace(",", " ")
    lignes = [f"dce/{chemin} : {taille} caractères, pièce longue.", "Sommaire :"]
    titres = re.findall(r"^(#{1,3}) +(.+)$", texte, re.MULTILINE)
    if titres:
        for diese, titre in titres:
            lignes.append(f"{'  ' * (len(diese) - 1)}- {titre.strip()[:90]}")
    else:
        parties = re.split(r"<!-- page (\d+) -->", texte)
        pages = [("1", parties[0])] + list(zip(parties[1::2], parties[2::2]))
        repetees = _lignes_repetees([contenu for _, contenu in pages])
        for numero, contenu in pages:
            premiere = next(
                (l.strip() for l in contenu.splitlines()
                 if len(l.strip()) > 3 and _forme(l) not in repetees),
                "",
            )
            if premiere:
                lignes.append(f"  page {numero} : {premiere[:90]}")
    lignes += [
        "",
        "Pour lire sans tout charger : `remporte chercher \"<termes>\"` pour un passage,",
        "`remporte lire <pièce> --page N` pour une page, `--tout` pour l'ensemble.",
    ]
    return "\n".join(lignes)


def _forme(ligne: str) -> str:
    """Ligne sans chiffres ni blancs : « Page 3/185 » et « Page 4/185 » se valent."""
    return re.sub(r"[\d\s]+", "", ligne)


def _lignes_repetees(pages: list[str]) -> set[str]:
    """En-têtes et pieds de page : les lignes présentes sur au moins un tiers
    des pages."""
    compte: dict[str, int] = {}
    for contenu in pages:
        for forme in {_forme(l) for l in contenu.splitlines() if l.strip()}:
            compte[forme] = compte.get(forme, 0) + 1
    seuil = max(3, len(pages) // 3)
    return {forme for forme, nombre in compte.items() if nombre >= seuil}


def _indenter(texte: str) -> str:
    """Passage complet, indenté sous son rang : un extrait tronqué cachait les
    chiffres que l'agent venait chercher."""
    return "\n".join(f"   {ligne}" for ligne in texte.strip().splitlines())


def _cmd_chercher(args) -> int:
    dossier, code = _dossier_ou_code(args)
    if dossier is None:
        return code
    if not (dossier / ".remporte" / "index.sqlite").exists():
        print(
            f"Erreur : aucun index dans {dossier}. Relancez `remporte init` "
            "pour indexer le DCE.",
            file=sys.stderr,
        )
        return 1
    resultats = recherche.chercher_dce(dossier, args.requete, args.limite)
    if args.json:
        _sortie_json({"resultats": resultats})
        return 0
    if not resultats:
        print(f"Aucun passage du DCE ne correspond à « {args.requete} ».")
        return 0
    for rang, resultat in enumerate(resultats, 1):
        print(f"{rang}. {resultat['piece']} (score {resultat['score']:.2f})")
        print(_indenter(resultat["passage"]))
        print()
    return 0


def _cmd_cadre(args) -> int:
    dossier, code = _dossier_ou_code(args)
    if dossier is None:
        return code
    donnees = _etat_json(dossier)
    if donnees is None:
        print(
            f"Erreur : {dossier} n'a pas d'inventaire (etat.json absent). "
            "Relancez `remporte init`.",
            file=sys.stderr,
        )
        return 1
    pieces = donnees["pieces"]
    if args.fragment:
        candidats = [p for p in pieces
                     if args.fragment.lower() in p["chemin"].lower()]
        if not candidats:
            print(f"Aucune pièce dont le chemin contient « {args.fragment} ».")
            return 1
        if len(candidats) > 1:
            print(f"{len(candidats)} pièces contiennent « {args.fragment} » :")
            for p in candidats:
                print(f"  dce/{p['chemin']}")
            return 1
    else:
        candidats = [p for p in pieces if p["type"] == "CRT"]
        if not candidats:
            print("Aucun CRT identifié dans ce dossier. Nommez la pièce : "
                  "remporte cadre <fragment>")
            for p in pieces:
                print(f"  [{p['type']}] dce/{p['chemin']}")
            return 1
        if len(candidats) > 1:
            print("Plusieurs pièces classées CRT :")
            for p in candidats:
                print(f"  dce/{p['chemin']}")
            print("Précisez : remporte cadre <fragment>")
            return 1
    piece = candidats[0]
    resultat = cadre.extraire_cadre(dossier / "dce" / piece["chemin"])
    resultat["piece"] = f"dce/{piece['chemin']}"
    if args.couverture:
        return _afficher_couverture(dossier, resultat, args.json)
    if args.json:
        _sortie_json(resultat)
        return 0
    print(f"Cadre de réponse — dce/{piece['chemin']} "
          f"(origine : {resultat['origine']}, {len(resultat['points'])} points)")
    if not resultat["points"]:
        print("  Aucune demande explicite au candidat trouvée dans cette pièce.")
        return 0
    for point in resultat["points"]:
        chapitre = f"  [{point['niveau']}]" if point["niveau"] else ""
        print(f"  {point['numero']}. {point['titre']}{chapitre}")
    print(f"Total : {len(resultat['points'])} points. Si votre affichage est tronqué, "
          "`remporte cadre --json` les rend tous.")
    return 0


def _afficher_couverture(dossier: Path, resultat: dict, en_json: bool) -> int:
    """Exigences numérotées du CRT qu'aucune section ne cite par son identifiant."""
    entrees = cadre.couverture(dossier, resultat)
    if entrees is None:
        print("Le contrôle de couverture demande un CRT à exigences numérotées "
              "(« PP 001 »…) ; celui-ci n'en a pas. Relisez-le point par point.")
        return 0
    total = len(entrees)
    absents = [entree["point"] for entree in entrees if not entree["couverte"]]
    if en_json:
        _sortie_json({"total": total, "absents": absents})
        return 0
    print(f"Exigences du CRT citées dans les sections : {total - len(absents)} sur {total}.")
    for point in absents:
        print(f"  absente : {point['titre']}")
    if absents:
        print("Citez l'identifiant (ex. « PP 009 ») dans la section qui y répond.")
    return 0


def _cmd_formats(args) -> int:
    dossier, code = _dossier_ou_code(args)
    if dossier is None:
        return code
    donnees = _etat_json(dossier)
    if donnees is None:
        print(
            f"Erreur : {dossier} n'a pas d'inventaire (etat.json absent). "
            "Relancez `remporte init`.",
            file=sys.stderr,
        )
        return 1
    constats = formats.detecter(dossier, donnees["pieces"])
    if args.json:
        _sortie_json({"constats": constats})
        return 0
    if not constats:
        print("Aucune contrainte de forme détectée dans ce DCE.")
        return 0
    print(f"Formats attendus par l'acheteur ({len(constats)} constats) :")
    for constat in constats:
        print(f"- {formats.libelle(constat)}")
        print(f"  source : dce/{constat['piece']}")
        print(f"  « {constat['extrait']} »")
    return 0


def _cmd_candidature_preparer(args) -> int:
    dossier, code = _dossier_ou_code(args)
    if dossier is None:
        return code
    chemin = candidature.preparer(dossier)
    if args.json:
        _sortie_json({"valeurs": str(chemin)})
        return 0
    print(f"Valeurs de candidature : {chemin}")
    print("Renseignez chaque champ « valeur », puis : "
          "remporte candidature remplir")
    return 0


def _cmd_candidature_remplir(args) -> int:
    dossier, code = _dossier_ou_code(args)
    if dossier is None:
        return code
    resultat = candidature.remplir(dossier)
    if args.json:
        _sortie_json(resultat)
        return 0
    for produit in resultat["produits"]:
        print(f"{produit['formulaire']} → {dossier / produit['chemin']}")
    for non_produit in resultat["non_produits"]:
        print(f"{non_produit['formulaire']} → non produit "
              f"({non_produit['motif']})")
    _afficher_champs(
        "Champs non remplis (complétez candidature/valeurs.json puis "
        "relancez) :", resultat["non_remplis"])
    _afficher_champs(
        "Optionnels laissés vides (sans objet si vous n'avez rien à dire) :",
        resultat["optionnels_vides"])
    _afficher_champs("À porter à la main dans le fichier :",
                     resultat["manuels"])
    for formulaire, anomalies in resultat["anomalies"].items():
        for var, message in anomalies.items():
            print(f"  ! {formulaire}/{var} : {message}")
    return 0


def _afficher_champs(titre: str, par_formulaire: dict) -> None:
    if not par_formulaire:
        return
    print(titre)
    for formulaire, variables in par_formulaire.items():
        print(f"  {formulaire} : {', '.join(variables)}")


def _cmd_base_indexer(args) -> int:
    racine = travail.trouver_espace()
    if args.source:
        source = Path(args.source)
    elif racine is not None:
        source = racine / travail.RESSOURCES
    else:
        print("Erreur : indiquez le dossier des documents de l'entreprise, ou "
              "lancez la commande dans un espace de travail (remporte espace).",
              file=sys.stderr)
        return 1
    if not source.is_dir():
        print(f"Erreur : source introuvable ou pas un dossier : {source}",
              file=sys.stderr)
        return 1
    base = recherche.chemin_base()
    nombre = recherche.indexer_base(source, base)
    if args.json:
        _sortie_json({"base": str(base), "passages": nombre})
        return 0
    print(f"Base : {base}")
    print(f"Passages indexés : {_nombre(nombre)}")
    return 0


def _cmd_base_chercher(args) -> int:
    base = recherche.chemin_base()
    if not (base / "index.sqlite").exists():
        print(
            f"Erreur : base absente dans {base}. Lancez d'abord "
            "`remporte base indexer <dossier>`.",
            file=sys.stderr,
        )
        return 1
    resultats = recherche.chercher_base(base, args.requete, args.limite)
    if args.json:
        _sortie_json({"resultats": resultats})
        return 0
    if not resultats:
        print(f"Aucun passage de la base ne correspond à « {args.requete} ».")
        return 0
    for rang, resultat in enumerate(resultats, 1):
        print(f"{rang}. {resultat['piece']} (score {resultat['score']:.2f})")
        print(_indenter(resultat["passage"]))
        print()
    return 0


GUIDES_ANNEXES = {
    "formats": "limite de pages, fichier imposé, soutenance",
    "soutenance": "support préparé sur les fichiers de l'entreprise",
    "excel": "répondre dans un fichier Excel ou Word imposé",
    "candidature": "DC1, DC2, DC4",
    "modeles": "puissance de modèle et sous-agents par tâche",
}


def _cmd_guide(args) -> int:
    if not args.etape:
        print("Étapes du dossier de réponse :")
        for etape in espace.ETAPES:
            print(f"  remporte guide {etape}")
        print("Selon le dossier :")
        for nom, objet in GUIDES_ANNEXES.items():
            print(f"  remporte guide {nom:<12} {objet}")
        print("Aussi : remporte offre")
        return 0
    if args.etape not in espace.ETAPES and args.etape not in GUIDES_ANNEXES:
        print(f"Erreur : guide inconnu « {args.etape} ».", file=sys.stderr)
        print("Guides : " + ", ".join([*espace.ETAPES, *GUIDES_ANNEXES]), file=sys.stderr)
        return 1
    contenu = _lire_ressource("guides", f"{args.etape}.md")
    if contenu is None:
        print(
            f"Pas encore de guide pour l'étape « {args.etape} » : il sera "
            "livré dans une prochaine version du paquet."
        )
        return 1
    print(contenu.rstrip())
    return 0


def _cmd_espace(args) -> int:
    resultat = travail.creer_espace(Path(args.chemin))
    if args.json:
        _sortie_json(resultat)
        return 0
    print(f"Espace de travail : {resultat['espace']}")
    for relatif in resultat["crees"]:
        print(f"  créé : {relatif}")
    print("Déposez les documents de l'entreprise dans ressources/, complétez "
          "ressources/fiche-entreprise.md, puis : remporte base indexer")
    return 0


def _cmd_fiche(args) -> int:
    fiche = recherche.chemin_fiche()
    if args.creer and not fiche.exists():
        fiche.parent.mkdir(parents=True, exist_ok=True)
        fiche.write_text(_lire_ressource("gabarits", "fiche-entreprise.md"), encoding="utf-8")
        print(f"Fiche créée : {fiche}")
        return 0
    if not fiche.exists():
        print(f"Pas encore de fiche entreprise ({fiche}). Lancez /remporte:init, "
              "ou `remporte fiche --creer`.")
        return 1
    texte = fiche.read_text(encoding="utf-8")
    if args.json:
        _sortie_json({"chemin": str(fiche), "texte": texte})
    else:
        print(f"<!-- {fiche} -->")
        print(texte.rstrip())
    return 0


def _cmd_html(args) -> int:
    source = Path(args.source)
    if not source.is_file():
        print(f"Erreur : fichier introuvable : {source}", file=sys.stderr)
        return 1
    sortie = Path(args.sortie) if args.sortie else source.with_suffix(".html")
    texte = source.read_text(encoding="utf-8", errors="replace")
    sortie.write_text(charte.page_depuis_markdown(texte), encoding="utf-8")
    if args.json:
        _sortie_json({"html": str(sortie)})
    else:
        print(f"html : {sortie}")
    return 0


def _cmd_exporter(args) -> int:
    dossier, code = _dossier_ou_code(args)
    if dossier is None:
        return code
    formats = {f.strip().lower() for f in args.formats.split(",") if f.strip()}
    inconnus = formats - {"docx", "html", "analyse", "feuille", "matrice"}
    if inconnus:
        print(f"Erreur : formats inconnus : {', '.join(sorted(inconnus))} "
              "(choix : docx, html, analyse, feuille, matrice)", file=sys.stderr)
        return 1
    if not formats:
        formats = {"docx", "html"}
    resultat = export.exporter(dossier, formats)
    if args.json:
        _sortie_json({cle: str(valeur) if valeur else None
                      for cle, valeur in resultat.items()})
        return 0
    for format_, chemin in resultat.items():
        print(f"{format_} : {chemin}" if chemin else f"{format_} : non produit")
    print("Mémoire dans votre modèle Word, prix reportés dans le bordereau de "
          f"l'acheteur : disponible avec Remporte, {lien.site('export')}")
    return 0


def _cmd_offre(args) -> int:
    contenu = _lire_ressource("guides", "offre.md")
    if contenu is None:
        print("Pas encore de guide « offre » : il sera livré dans une "
              "prochaine version du paquet.")
        return 1
    print(contenu.rstrip())
    return 0
