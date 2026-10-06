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

from remporte import cadre, espace, export, inventaire, lecture, recherche


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
    p.set_defaults(func=_cmd_lire)

    p = sous.add_parser("chercher", parents=[communes, avec_dossier],
                        help="retrouver un passage dans tout le DCE")
    p.add_argument("requete", metavar="TERMES")
    p.add_argument("--limite", type=int, default=10)
    p.set_defaults(func=_cmd_chercher)

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
    pb.add_argument("source", metavar="DOSSIER")
    pb.set_defaults(func=_cmd_base_indexer)
    pb = sous_base.add_parser("chercher", parents=[communes],
                              help="chercher dans la base entreprise")
    pb.add_argument("requete", metavar="TERMES")
    pb.add_argument("--limite", type=int, default=10)
    pb.set_defaults(func=_cmd_base_chercher)

    p = sous.add_parser("guide", help="méthode d'une étape (sans argument : liste)")
    p.add_argument("etape", nargs="?", default=None, metavar="ETAPE")
    p.set_defaults(func=_cmd_guide)

    p = sous.add_parser("exporter", parents=[communes, avec_dossier],
                        help="produire export/memoire.docx et export/dossier.html")
    p.add_argument("--formats", default="docx,html", metavar="LISTE",
                   help="formats parmi docx,html (défaut : les deux)")
    p.set_defaults(func=_cmd_exporter)

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
    if args.dossier:
        dossier = Path(args.dossier)
    else:
        nom = source.stem or source.name
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
    print(texte)
    return 0


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


def _identifiant(point: dict) -> str | None:
    """« PP 009 » d'un point issu d'une liste numérotée, sinon None."""
    trouve = re.match(r"([A-Z]+) ?(\d+) — ", point["titre"])
    return f"{trouve.group(1)} {trouve.group(2)}" if trouve else None


def _afficher_couverture(dossier: Path, resultat: dict, en_json: bool) -> int:
    """Exigences numérotées du CRT qu'aucune section ne cite par son identifiant."""
    if resultat["origine"] != "liste":
        print("Le contrôle de couverture demande un CRT à exigences numérotées "
              "(« PP 001 »…) ; celui-ci n'en a pas. Relisez-le point par point.")
        return 0
    texte = "\n".join(
        f.read_text(encoding="utf-8", errors="replace")
        for f in sorted((dossier / "sections").glob("*.md"))
    )
    absents = []
    for point in resultat["points"]:
        prefixe, numero = _identifiant(point).split()
        motif = rf"(?<![A-Za-z]){prefixe}[ _-]?0*{int(numero)}(?!\d)"
        if not re.search(motif, texte):
            absents.append(point)
    total = len(resultat["points"])
    if en_json:
        _sortie_json({"total": total, "absents": absents})
        return 0
    print(f"Exigences du CRT citées dans les sections : {total - len(absents)} sur {total}.")
    for point in absents:
        print(f"  absente : {point['titre']}")
    if absents:
        print("Citez l'identifiant (ex. « PP 009 ») dans la section qui y répond.")
    return 0


def _cmd_base_indexer(args) -> int:
    source = Path(args.source)
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


def _cmd_guide(args) -> int:
    if not args.etape:
        print("Étapes du dossier de réponse :")
        for etape in espace.ETAPES:
            print(f"  remporte guide {etape}")
        print("Aussi : remporte offre")
        return 0
    if args.etape not in espace.ETAPES:
        print(f"Erreur : étape inconnue « {args.etape} ».", file=sys.stderr)
        print("Étapes : " + ", ".join(espace.ETAPES), file=sys.stderr)
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


def _cmd_exporter(args) -> int:
    dossier, code = _dossier_ou_code(args)
    if dossier is None:
        return code
    formats = {f.strip().lower() for f in args.formats.split(",") if f.strip()}
    inconnus = formats - {"docx", "html"}
    if inconnus:
        print(f"Erreur : formats inconnus : {', '.join(sorted(inconnus))} "
              "(choix : docx, html)", file=sys.stderr)
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
    return 0


def _cmd_offre(args) -> int:
    contenu = _lire_ressource("guides", "offre.md")
    if contenu is None:
        print("Pas encore de guide « offre » : il sera livré dans une "
              "prochaine version du paquet.")
        return 1
    print(contenu.rstrip())
    return 0
