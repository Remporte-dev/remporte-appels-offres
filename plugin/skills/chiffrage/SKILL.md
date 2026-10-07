---
name: chiffrage
description: Remplir le bordereau de prix d'un marché public (BPU, DPGF, DQE) dans le fichier de l'acheteur : reporter les prix de l'utilisateur sans toucher à la trame ni aux formules, puis contrôler totaux et cohérence avec l'acte d'engagement.
---

# Bordereau de prix

Vérifie que tu peux lancer des commandes et lire/écrire les fichiers du dossier choisi. Il faut les deux capacités. Si l'une manque, explique que cette tâche demande un environnement avec accès aux commandes et aux fichiers, comme Codex, Claude Code/Cowork ou ChatGPT Work disposant de cet accès. Ne poursuis pas sans ces capacités.

Suis `remporte guide chiffrage`. Les prix viennent de l'utilisateur : demande
sa grille ou ses prix, tu ne fixes aucun prix toi-même. Copie dans
`reponse/`, aucune ligne vide, trame et formules intactes, totaux recalculés,
total identique à celui de l'acte d'engagement. Rends le fichier et la liste
des points à vérifier.

Exécute les commandes depuis le dossier de réponse (celui qui contient `.remporte/`).
Depuis un autre dossier, utilise `--dossier "<chemin>"` seulement si l'aide de la commande
propose cette option ; `remporte guide <étape>` ne la prend pas. Pas encore de dossier : `$remporte:nouvel-ao` dans Codex ou `/remporte:nouvel-ao` dans Claude Code.
N'invente jamais une information sur l'entreprise : `remporte fiche`,
`remporte base chercher`, ou `[à compléter : …]`.
