# Remporte : répondre aux appels d'offres publics avec Claude

Plugin gratuit et open source pour répondre à un marché public français avec Claude : lecture
du DCE, analyse, go/no-go, plan du mémoire technique, rédaction, contrôle de conformité,
relecture, formulaires DC1/DC2/DC4 et exports Word, HTML et Excel.

Il fonctionne dans **Claude Code** et dans **Cowork**, sur votre ordinateur : il lit vos
fichiers et lance l'outil `remporte`. Il ne fonctionne pas dans une conversation sur claude.ai,
faute de terminal.

## Exemples

- `/remporte:init` : vérifie l'installation, crée votre espace de travail et construit la fiche
  entreprise à partir de vos documents (références, CV, certifications).
- `/remporte:nouvel-ao ~/Téléchargements/DCE-voirie.zip` : crée le dossier de réponse, lit le
  DCE, prépare l'analyse, le go/no-go et le plan du mémoire, avec un arrêt de validation à
  chaque étape.
- « Vérifie que chaque exigence du cadre de réponse est traitée dans le mémoire » : liste les
  exigences numérotées qu'aucune section ne traite encore.
- « Remplis le DC1 et le DC2 pour ce marché » : remplit les formulaires officiels à partir de
  la fiche entreprise.

## Ce que le plugin exécute

- **L'outil `remporte`**, un programme en ligne de commande open source, sur votre poste. Le
  plugin le lance pour lire les pièces du DCE, chercher dans vos documents, contrôler la
  couverture des exigences et produire les exports.
- **Son installation**, une seule fois : si l'outil est absent, `/remporte:init` propose
  `uv tool install remporte` (paquet publié sur PyPI) et attend votre accord avant de le lancer.
- **Rien d'autre.** Ni le plugin ni l'outil ne font d'appel réseau, ne créent de compte ni ne
  mesurent leur usage. Vos DCE et vos documents restent dans les dossiers que vous choisissez.

Le plugin fournit trois skills (`init`, `nouvel-ao`, `repondre-ao`) et trois sous-agents
(`lecteur-dce`, `redacteur-section`, `relecteur`). Il ne contient ni hook ni serveur MCP.

## Remporte, le logiciel en ligne

Ce plugin fonctionne entièrement seul, sans compte. Remporte existe aussi sous forme de
logiciel en ligne, distinct du plugin, qui ajoute :

- une base de connaissance de l'entreprise, partagée par l'équipe ;
- la mise en forme du mémoire dans le modèle Word de l'entreprise ;
- des plans de mémoire prêts à adapter ;
- le remplissage des bordereaux de prix (BPU, DPGF, DQE) dans les fichiers de l'acheteur.

Présentation : https://remporte.fr/outils/agent-ia/

## En savoir plus

- Documentation complète et code source : https://github.com/Remporte-dev/remporte-appels-offres
- Politique de confidentialité : https://remporte.fr/politique-confidentialite/#outil-agent-ia
- Licence : MIT

Édité par Remporte (Flowt).
