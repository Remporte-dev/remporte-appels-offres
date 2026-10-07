---
name: cadre-reponse
description: Répondre dans le cadre de réponse technique (CRT) imposé par l'acheteur d'un marché public : reprendre sa structure à l'identique, traiter chaque exigence numérotée, vérifier la couverture et reporter la réponse dans son fichier Word.
---

# Cadre de réponse technique

Vérifie que tu peux lancer des commandes et lire/écrire les fichiers du dossier choisi. Il faut les deux capacités. Si l'une manque, explique que cette tâche demande un environnement avec accès aux commandes et aux fichiers, comme Codex, Claude Code/Cowork ou ChatGPT Work disposant de cet accès. Ne poursuis pas sans ces capacités.

Suis `remporte guide cadre-reponse` :

1. `remporte cadre` : titres et exigences numérotées du CRT.
2. Plan à l'identique du CRT, puis rédaction (`remporte guide redaction`), une
   sous-partie par exigence.
3. `remporte cadre --couverture` doit être vide avant de livrer.
4. Report dans une copie du fichier de l'acheteur, sans toucher à sa trame
   (`remporte guide excel`).
5. `remporte exporter` : la matrice de conformité, à relire avec l'utilisateur.

Travaille dans le dossier de réponse (celui qui contient `.remporte/`), ou ajoute
`--dossier "<chemin>"` aux commandes. Pas encore de dossier : `$remporte:nouvel-ao` dans Codex ou `/remporte:nouvel-ao` dans Claude Code.
N'invente jamais une information sur l'entreprise : `remporte fiche`,
`remporte base chercher`, ou `[à compléter : …]`.
