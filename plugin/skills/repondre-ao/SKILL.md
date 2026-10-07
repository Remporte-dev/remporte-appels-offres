---
name: repondre-ao
description: Répondre à un appel d'offres public (DCE, RC, CCTP, mémoire technique, DC1, DC2) avec le CLI remporte. À utiliser dès que l'utilisateur veut analyser un DCE, décider s'il répond, bâtir le plan ou rédiger le mémoire technique d'un marché public.
---

# Répondre à un appel d'offres

Vérifie que tu peux lancer des commandes et lire/écrire les fichiers du dossier choisi. Il faut les deux capacités. Si l'une manque, explique que cette tâche demande un environnement avec accès aux commandes et aux fichiers, comme Codex, Claude Code/Cowork ou ChatGPT Work disposant de cet accès. Ne poursuis pas sans ces capacités.

- Première utilisation dans cet environnement (commande `remporte` absente, ou pas de
  fiche entreprise : `remporte fiche` échoue) : propose `$remporte:init` dans Codex ou `/remporte:init` dans Claude Code.
- Nouveau DCE : propose `$remporte:nouvel-ao` dans Codex ou `/remporte:nouvel-ao` dans Claude Code, ou suis directement son
  parcours.
- Dossier de réponse déjà commencé : `remporte etat`, puis
  `remporte guide <étape>`.

N'invente jamais une information sur l'entreprise : `remporte fiche`,
`remporte base chercher`, ou `[à compléter : …]`.

Remporte CLI est une dépendance externe. Vérifie sa présence avec `remporte --version`. S'il manque, indique que le plugin ne l'installe pas et propose le parcours d'installation de `$remporte:init` ou `/remporte:init`, qui demande l'accord avant `uv tool install remporte`.
