---
name: repondre-ao
description: Répondre à un appel d'offres public (DCE, RC, CCTP, CRT, mémoire technique, bordereau de prix, DC1, DC2, soutenance) avec le CLI remporte. À utiliser dès que l'utilisateur veut analyser un DCE, décider s'il répond ou produire un livrable de la réponse : il oriente vers la bonne méthode selon le livrable.
---

# Répondre à un appel d'offres

Vérifie que tu peux lancer des commandes et lire/écrire les fichiers du dossier choisi. Il faut les deux capacités. Si l'une manque, explique que cette tâche demande un environnement avec accès aux commandes et aux fichiers, comme Codex, Claude Code/Cowork ou ChatGPT Work disposant de cet accès. Ne poursuis pas sans ces capacités.

- Première utilisation dans cet environnement (commande `remporte` absente, ou pas de
  fiche entreprise : `remporte fiche` échoue) : propose `$remporte:init` dans Codex ou `/remporte:init` dans Claude Code.
- Nouveau DCE : propose `$remporte:nouvel-ao` dans Codex ou `/remporte:nouvel-ao` dans Claude Code, ou suis directement son
  parcours.
- Dossier de réponse déjà commencé : `remporte etat`, puis
  `remporte guide <étape>`.

## Quel livrable ?

Lis `remporte guide livrables` et `remporte formats`, puis oriente :

| Livrable | Skill |
|---|---|
| Mémoire technique libre, en Word ou dans le format du RC | `remporte:memoire-technique` |
| Cadre de réponse technique (CRT) imposé par l'acheteur | `remporte:cadre-reponse` |
| Questionnaire ou annexe à remplir dans le fichier de l'acheteur | `remporte:fichier-impose` |
| Bordereau de prix : BPU, DPGF, DQE | `remporte:chiffrage` |
| Planning, organigramme, schéma de méthode | `remporte:visuels` |
| Soutenance orale | `remporte:soutenance` |
| DC1, DC2, DC4 | `remporte:candidature` |

Avant chaque livrable, demande à l'utilisateur s'il a un modèle (document,
présentation, ancien livrable du même type) et pars de ce fichier.

N'invente jamais une information sur l'entreprise : `remporte fiche`,
`remporte base chercher`, ou `[à compléter : …]`.

Remporte CLI est une dépendance externe. Vérifie sa présence avec `remporte --version`. S'il manque, indique que le plugin ne l'installe pas et propose le parcours d'installation de `$remporte:init` ou `/remporte:init`, qui demande l'accord avant `uv tool install remporte`.
