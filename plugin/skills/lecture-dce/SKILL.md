---
name: lecture-dce
description: Lire et analyser les pièces d'un DCE Remporte, produire l'index et l'analyse sourcée avant la décision de répondre.
---

Vérifie l'accès aux commandes ainsi qu'aux fichiers à lire et écrire. Si une capacité manque, explique que cette tâche demande un environnement avec accès aux commandes et aux fichiers, comme Codex, Claude Code/Cowork ou ChatGPT Work disposant de cet accès. Arrête cette étape si ces accès manquent.

Lance `remporte --version`. Si l'outil est absent, propose la mise en route (`$remporte:init` dans Codex, `/remporte:init` dans Claude Code) et attends la fin de l'installation avant de poursuivre.

Applique la procédure commune [lecture du DCE](../../references/lecture-dce.md). Si l'agent spécialisé `lecteur-dce` est indisponible, transmets cette procédure et le dossier à un sous-agent générique si l'environnement en propose un. Sinon, exécute la procédure toi-même.
