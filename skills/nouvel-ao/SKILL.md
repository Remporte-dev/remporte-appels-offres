---
name: nouvel-ao
description: Démarrer la réponse à un nouvel appel d'offres public à partir de son DCE (zip ou dossier), puis la conduire étape par étape avec l'utilisateur jusqu'aux fichiers à déposer. À lancer quand l'utilisateur tape /remporte:nouvel-ao, éventuellement suivi du chemin du DCE.
disable-model-invocation: true
argument-hint: "[chemin du DCE, zip ou dossier]"
---

# Nouvel appel d'offres

Tu conduis la réponse avec l'utilisateur. Une étape à la fois ; à chaque point
de décision, tu t'arrêtes et tu lui demandes. Français simple, sans jargon
informatique.

Si `remporte --version` ne répond pas, propose d'abord `/remporte:init`.

## 1. Le DCE

Chemin donné en argument : $ARGUMENTS

S'il est vide, demande où se trouve le DCE téléchargé (le zip de la
plateforme ou le dossier décompressé). Demande aussi où ranger la réponse :
par défaut, un dossier `<nom>-reponse` dans le répertoire courant.

Lance `remporte init "<DCE>"` (avec `--dossier "<chemin>"` si l'utilisateur
a choisi un autre emplacement). Toutes les commandes suivantes prennent
`--dossier "<chemin du dossier de réponse>"` si tu n'es pas lancé dedans.

## 2. Premier état du dossier

Lis `01-pieces.md` et `remporte formats`, puis résume en cinq lignes au plus :
pièces trouvées, pièces illisibles ou manquantes (le RC surtout), cadre de
réponse imposé ou non, contraintes de forme (pages, fichier à compléter,
soutenance). Signale ce qui bloque.

## 3. Trois questions à l'utilisateur, avant d'analyser

1. Quels lots l'intéressent, s'il y en a plusieurs ?
2. Quelle est sa date limite interne (souvent quelques jours avant celle de
   l'acheteur) ?
3. Veut-il valider à chaque étape, ou seulement au go/no-go et à la fin ?

## 4. Le parcours, avec des sous-agents

Tu orchestres ; les lectures et rédactions lourdes partent à des sous-agents,
qui ménagent l'abonnement et ton propre contexte :

| Étape | Qui | Comment |
|---|---|---|
| Index et analyse | sous-agent `remporte:lecteur-dce` | donne-lui le chemin du dossier ; il écrit `00-index.md` et `02-analyse.md` |
| Go/No-Go | toi, avec l'utilisateur | `remporte guide go-no-go`, à partir de l'analyse et de `remporte fiche` |
| Plan | toi | `remporte guide plan` |
| Rédaction | un sous-agent `remporte:redacteur-section` par section | lance-les par lots de trois ou quatre en parallèle, les plus pondérées d'abord ; coche le plan quand chacun a rendu |
| Relecture | sous-agent `remporte:relecteur` | il écrit `05-relecture.md` ; toi, tu appliques les corrections |
| Export | toi | `remporte exporter` |

Sans sous-agents disponibles, fais toi-même chaque étape avec
`remporte guide <étape>`, dans le même ordre.

Trois arrêts obligatoires, quel que soit le mode choisi :

- **après l'analyse** : présente les critères pondérés et les points de
  vigilance, demande s'il manque quelque chose ;
- **au go/no-go** : la décision appartient à l'utilisateur. Présente ta
  recommandation et ses raisons, et attends sa réponse ;
- **après le plan** : fais valider la trame avant de rédiger.

Pendant la rédaction, regroupe les informations manquantes et pose-les
ensemble, plutôt qu'une par une.

## 5. La fin

Après `remporte exporter`, donne à l'utilisateur :
- les fichiers produits (`export/`, `candidature/` s'il y a lieu) ;
- la liste de ce qu'il doit encore fournir, signer ou remplir ;
- la date limite de remise, rappelée.

Ouvre-lui `export/feuille-de-route.html` s'il le souhaite : c'est le
récapitulatif à garder sous les yeux jusqu'au dépôt.
