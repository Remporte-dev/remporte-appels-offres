---
name: nouvel-ao
description: Démarrer la réponse à un nouvel appel d'offres public à partir de son DCE (zip ou dossier), puis la conduire étape par étape avec l'utilisateur jusqu'aux fichiers à déposer. À lancer quand l'utilisateur tape /remporte:nouvel-ao, éventuellement suivi du chemin du DCE.
disable-model-invocation: true
argument-hint: "[chemin du DCE, zip ou dossier]"
---

# Nouvel appel d'offres

Dans Codex, appelle cette compétence avec `$remporte:nouvel-ao` ou réponds à une demande naturelle de traitement d'un nouveau DCE. `/remporte:nouvel-ao` est un exemple de commande propre à Claude Code. Prends le chemin du DCE indiqué dans le message ou dans les arguments de la commande ; s'il manque, demande-le dans la conversation.

Tu conduis la réponse avec l'utilisateur. Une étape à la fois ; à chaque point
de décision, tu t'arrêtes et tu lui demandes. Français simple, sans jargon
informatique.

Vérifie que tu peux lancer des commandes et lire/écrire les fichiers du dossier choisi. Il faut les deux capacités. Si l'une manque, explique que la tâche demande un environnement avec accès aux commandes et aux fichiers, comme Codex, Claude Code/Cowork ou ChatGPT Work disposant de cet accès. Arrête cette étape si ces accès manquent.

Lance `remporte --version`. Remporte CLI est une dépendance externe. Si la commande est absente, propose `$remporte:init` dans Codex ou `/remporte:init` dans Claude Code pour suivre l'installation. Ne promets pas que l'installation du plugin installe le CLI.

## 1. Le DCE

Demande où se trouve le DCE téléchargé (zip de la plateforme ou dossier décompressé) s'il n'est pas déjà indiqué dans la conversation.

Travaille depuis l'espace de travail de l'entreprise (le dossier qui contient
`ressources/` et `DCEs/`) : `remporte init "<DCE>"` y crée
`DCEs/<nom du DCE>/`. Si aucun espace n'existe, propose `$remporte:init` dans Codex ou `/remporte:init` dans Claude Code.

Exécute les commandes suivantes depuis le dossier de réponse. Depuis un autre dossier, utilise `--dossier "<chemin du dossier de réponse>"` seulement si l'aide de la commande propose cette option. Pour `remporte guide <étape>`, place-toi dans le dossier de réponse ; cette commande ne prend pas `--dossier`.

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

| Étape | Claude Code | Codex / ChatGPT Work |
|---|---|---|
| Index et analyse | sous-agent `remporte:lecteur-dce` | skill `remporte:lecture-dce`, procédure [lecture du DCE](../../references/lecture-dce.md) |
| Go/No-Go | toi, avec l'utilisateur | `remporte guide go-no-go`, à partir de l'analyse et de `remporte fiche` |
| Plan | toi | `remporte guide plan` |
| Rédaction | sous-agent `remporte:redacteur-section` | skill `remporte:redaction-section`, procédure [rédaction d'une section](../../references/redaction-section.md) |
| Relecture | sous-agent `remporte:relecteur` | skill `remporte:relecture-ao`, procédure [relecture](../../references/relecture-ao.md) |
| Export | toi | `remporte exporter` |

Donne à chaque lecteur le chemin du dossier ; il écrit `00-index.md` et `02-analyse.md`. Pour la rédaction, donne une section par agent et lance-les par lots de trois ou quatre si les outils disponibles le permettent, les plus pondérées d'abord. Coche le plan après réception de chaque section. Le relecteur écrit `05-relecture.md` ; tu appliques ensuite ses corrections.

Si un agent spécialisé est indisponible, transmets la procédure correspondante et le chemin du dossier à un sous-agent générique si l’environnement en propose un. Sinon, exécute toi-même cette étape avec `remporte guide <étape>`, dans le même ordre. Pour la rédaction et la relecture, applique le même recours. Pendant la relecture, ne modifie aucune section.

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
