---
name: init
description: Mise en route de Remporte, une fois par environnement. Vérifie l'outil, indexe les documents de l'entreprise (références, CV, certifications, anciens mémoires) et contrôle qu'il ne manque rien d'essentiel pour répondre aux appels d'offres. À lancer quand l'utilisateur tape /remporte:init ou découvre l'outil.
disable-model-invocation: true
---

Pour Codex, cette compétence peut être appelée comme `$remporte:init` ou à la demande naturelle de mise en route. `/remporte:init` est un exemple de commande propre à Claude Code.

# Mise en route de Remporte

Tu accompagnes l'utilisateur pas à pas. Une étape à la fois : annonce-la en une
phrase, fais-la, montre le résultat, puis passe à la suivante. Parle en
français simple, sans jargon informatique.

## 0. Les commandes et les fichiers sont-ils accessibles ?

Vérifie que tu peux lancer une commande et lire/écrire les fichiers du dossier choisi. Il faut les deux capacités. Si l'une manque, explique que cette tâche demande un environnement avec accès aux commandes et aux fichiers, comme Codex, Claude Code/Cowork ou ChatGPT Work disposant de cet accès. Ne poursuis pas les opérations locales.

## 1. L'outil est-il installé ?

Lance `remporte --version` pour vérifier la dépendance externe Remporte CLI.

- S'il répond : passe à l'étape 2.
- Sinon : explique que Remporte CLI est une dépendance externe et propose son
  installation. Demande l'accord de l'utilisateur avant de lancer :
  `uv tool install remporte`.
  Ne promets pas que l'installation du plugin installe le CLI. Si `uv` est absent, donne-lui la page d'installation de uv
  (https://docs.astral.sh/uv/getting-started/installation/) et attends qu'il
  l'ait installé ; ne lance pas toi-même un script d'installation téléchargé.

## 2. L'espace de travail

Tout le travail vit dans un seul dossier, dans l'environnement choisi :
`ressources/` pour les documents de l'entreprise et la fiche, `DCEs/` pour un
sous-dossier par appel d'offres. Demande où le créer : par défaut
`~/Remporte`, ou un dossier partagé avec son équipe (Drive, SharePoint).
Lance `remporte espace "<chemin>"` et travaille ensuite depuis ce dossier.

## 3. Les documents de l'entreprise

Demande-lui de déposer dans `ressources/` (ou de te dire où ils sont pour
que tu les y copies) les documents qui servent à répondre aux appels
d'offres, et explique pourquoi : c'est là que l'agent puisera les références,
les CV et les chiffres, sans jamais rien inventer. Ce qui est utile :

- références de marchés réalisés (client, montant, année, contact) ;
- CV des personnes qu'on met en avant ;
- certifications, qualifications, assurances ;
- anciens mémoires techniques, gagnés de préférence ;
- plaquette, présentation de l'entreprise, chiffres d'affaires, effectifs.

Un seul dossier, avec des sous-dossiers si l'utilisateur veut. Word, PDF,
Excel et texte sont lus ; les PDF scannés ne le sont pas.

Puis lance `remporte base indexer` (depuis l'espace, sans argument) et
annonce le nombre de passages indexés.

## 4. La fiche entreprise

`ressources/fiche-entreprise.md` a été créée avec l'espace : tous les agents
la liront avant de travailler. Remplis-la à partir de la base : une
recherche `remporte base chercher` par information, puis présente à
l'utilisateur ce que tu as trouvé et ce qui manque, en tableau (trouvé /
absent) :

| Information | Sert à |
|---|---|
| Raison sociale, SIRET, adresse | DC1, DC2 |
| Chiffres d'affaires des trois derniers exercices | DC2, go/no-go |
| Effectifs | DC2, moyens humains |
| Au moins trois références avec montant et année | mémoire, go/no-go |
| CV des intervenants clés | moyens humains |
| Certifications et assurances | candidature |

Chaque valeur écrite dans la fiche cite son document source. Pour ce qui
manque, demande à l'utilisateur : il dicte l'information et tu l'écris dans la
fiche, ou il ajoute le document au dossier. Une valeur qu'il ne donne pas
reste `[à compléter : …]` : n'invente jamais. Montre-lui ensuite la fiche
(`remporte fiche`), puis réindexe (`remporte base indexer`) pour
qu'elle soit aussi trouvée par la recherche.

## 5. La suite

Termine en trois lignes :
- la base et la fiche sont prêtes ; on réindexe avec la même commande quand
  les documents changent, et on met la fiche à jour à chaque exercice clos ou
  nouvelle référence ;
- pour répondre à un appel d'offres : demandez `$remporte:nouvel-ao` dans Codex, ou utilisez `/remporte:nouvel-ao` dans Claude Code ;
- `remporte guide modeles` explique comment économiser son abonnement.
