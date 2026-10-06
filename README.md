# remporte

**Répondre à un appel d'offres public avec votre agent IA.**

Un outil gratuit et open source de [Remporte](https://remporte.fr/produit?utm_source=github&utm_medium=readme&utm_content=entete), le logiciel de réponse aux appels d'offres.

`remporte` est un outil en ligne de commande, gratuit et open source, qui
donne à votre agent (Claude Code, Codex, Gemini CLI, Pi, ou tout agent qui
sait lancer une commande) ce qu'il faut pour répondre à un marché public :

- il **lit le DCE** : décompresse le zip, convertit RC, CCTP, CCAP, AE,
  bordereaux et annexes en texte, et reconnaît chaque pièce ;
- il **guide l'agent étape par étape** : analyse, go/no-go, plan, rédaction,
  relecture, export, avec une méthode écrite par des gens qui répondent à des
  appels d'offres ;
- il **vérifie que le mémoire répond à tout** : quand le cadre de réponse
  numérote ses exigences, il liste celles qu'aucune section ne traite encore ;
- il **cherche** dans le DCE et dans les documents de votre entreprise ;
- il **exporte** le mémoire technique en Word, le dossier en une page HTML et
  trois documents de travail : page d'analyse, feuille de route et matrice de
  conformité.

Aucun compte, aucun serveur : tout reste sur votre poste. Le raisonnement est
fait par votre agent, avec votre abonnement.

## Installation

```
uv tool install git+https://github.com/Remporte-dev/remporte
# ou : pipx install git+https://github.com/Remporte-dev/remporte
```

Il faut Python 3.10 ou plus récent ; `uv` l'installe tout seul si besoin.

## L'espace de travail

Tout vit dans un seul dossier, sur votre poste ou dans un dossier partagé :

```
Remporte/
  ressources/              vos documents, fiche-entreprise.md, index de recherche
  DCEs/
    2026-05-mairie-voirie/ un dossier par appel d'offres
```

```
remporte espace ~/Remporte                  # une fois
# déposez vos références, CV, certifications dans ~/Remporte/ressources/
cd ~/Remporte && remporte base indexer      # à refaire quand les documents changent
remporte init ~/Téléchargements/DCE.zip     # crée DCEs/DCE/
cd DCEs/DCE && claude                       # ou codex, gemini, pi…
```

Puis demandez à l'agent : « réponds à cet appel d'offres ». Chaque dossier
contient un `AGENTS.md` qui lui indique la marche à suivre.

## Les étapes

| Étape | Fichier | Ce que fait l'agent |
|---|---|---|
| pieces | `01-pieces.md` | Vérifie l'inventaire, signale les pièces illisibles |
| analyse | `02-analyse.md` | Critères pondérés, exigences, pièces à remettre, clauses |
| go-no-go | `03-go-no-go.md` | Décide s'il faut répondre, liste ce qu'il faut réunir |
| plan | `04-plan.md` | Trame calée sur le cadre de réponse ou sur les critères |
| redaction | `sections/` | Une section par fichier, preuves tirées de votre base |
| relecture | `05-relecture.md` | Note le mémoire avec la grille de l'acheteur |
| export | `export/` | `memoire.docx`, `dossier.html`, `analyse.html`, `feuille-de-route.html`, `matrice-conformite.xlsx` |

`remporte etat` dit où on en est ; `remporte guide <étape>` donne la méthode.

## Commandes

```
remporte espace [chemin]         créer l'espace de travail (ressources/, DCEs/)
remporte init <dce>              créer un dossier de réponse (dans DCEs/)
remporte etat                    avancement et prochaine étape
remporte guide [étape]           méthode de l'étape
remporte pieces                  inventaire des pièces
remporte lire <type ou nom>      texte d'une pièce (sommaire si elle est longue)
remporte chercher "<termes>"     recherche dans le DCE
remporte cadre                   trame imposée par le cadre de réponse
remporte cadre --couverture      exigences qu'aucune section ne traite encore
remporte formats                 formats attendus par l'acheteur (soutenance,
                                 pages, cadres Excel/Word à compléter)
remporte candidature preparer    créer candidature/valeurs.json (DC1/DC2/DC4)
remporte candidature remplir     écrire les formulaires officiels renseignés
remporte base indexer <dossier>  indexer les documents de l'entreprise
remporte base chercher "<t>"     recherche dans ces documents
remporte fiche [--creer]         fiche entreprise lue par tous les agents
remporte exporter                mémoire Word, analyse et feuille de route HTML,
                                 matrice de conformité Excel
remporte html <fichier.md>       mettre n'importe quel markdown en page HTML
remporte offre                   ce que Remporte fait en plus
```

Toutes acceptent `--json`.

## Économiser son abonnement

Le CLI fait sans modèle tout ce qui peut l'être : lecture et conversion du
DCE, recherche, contrôle de couverture, mise en page HTML, Word et Excel.
Une pièce longue se lit par son sommaire puis par page. `remporte guide
modeles` indique la puissance de modèle utile à chaque étape et quand confier
une lecture à un sous-agent léger. La base de l'entreprise est rangée dans
`~/.remporte/base/` ; la variable `REMPORTE_BASE` en change l'emplacement.

## Avec Claude Code

Le dépôt est aussi un plugin Claude Code :

```
/plugin marketplace add Remporte-dev/remporte
/plugin install remporte@remporte
```

Puis deux commandes suffisent :

- **`/remporte:init`**, une fois par poste : vérifie l'outil, indexe vos
  documents et construit la fiche entreprise que liront tous les agents ;
- **`/remporte:nouvel-ao <DCE.zip>`**, pour chaque appel d'offres : crée le
  dossier de réponse et conduit le parcours avec vous, avec trois arrêts de
  validation (analyse, go/no-go, plan).

Le plugin fournit trois sous-agents, pour lire une fois et rédiger en
parallèle sans épuiser l'abonnement : `lecteur-dce` (index et analyse du
DCE), `redacteur-section` (une section du mémoire) et `relecteur` (relecture
avec la grille de l'acheteur, par un agent qui n'a rien écrit).

## Ce que l'outil ne fait pas

Remplir l'acte d'engagement et le bordereau de prix (BPU, DPGF, DQE) dans le
format de l'acheteur, mettre le mémoire dans votre modèle Word, donner les
prix des marchés comparables déjà attribués : c'est ce que fait
[Remporte](https://remporte.fr/produit?utm_source=github&utm_medium=readme&utm_content=ne-fait-pas).

Les PDF scannés et les anciens fichiers Word `.doc` ne sont pas lus : ils sont
signalés dans l'inventaire.

## Licence

MIT.
