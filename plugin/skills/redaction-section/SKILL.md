---
name: redaction-section
description: Rédiger une section du mémoire technique Remporte à partir du plan, du DCE et des preuves de l'entreprise.
---

Vérifie l'accès aux commandes ainsi qu'aux fichiers à lire et écrire. Si une capacité manque, explique que cette tâche demande un environnement avec accès aux commandes et aux fichiers, comme Codex, Claude Code/Cowork ou ChatGPT Work disposant de cet accès. Arrête cette étape si ces accès manquent.

Lance `remporte --version`. Si l'outil est absent, propose la mise en route (`$remporte:init` dans Codex, `/remporte:init` dans Claude Code) et attends la fin de l'installation avant de poursuivre.

Applique la procédure commune de [rédaction d'une section](../../references/redaction-section.md). Si l'agent spécialisé `redacteur-section` est indisponible, transmets cette procédure, le dossier et la section à un sous-agent générique si l'environnement en propose un. Sinon, rédige la section toi-même.
