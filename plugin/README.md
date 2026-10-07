# Remporte : répondre aux appels d'offres publics avec un agent IA

Plugin gratuit et open source pour répondre à un marché public français : lecture du DCE,
analyse, décision go/no-go, plan du mémoire technique, rédaction, contrôle de conformité,
relecture, formulaires DC1/DC2/DC4 et exports Word, HTML et Excel.

Les instructions servent à Claude Code, Cowork, Codex et ChatGPT Work lorsque l'environnement
donne accès aux commandes et aux fichiers concernés. Il faut pouvoir lancer des commandes et
lire/écrire les fichiers. Dans un environnement cloud, les fichiers sont ceux accessibles dans
cet environnement et ne sont pas forcément présents sur votre ordinateur.

## Exemples

- Claude Code : `/remporte:init` prépare l'espace et la fiche entreprise. Codex peut invoquer
  `$remporte:init`.
- Claude Code : `/remporte:nouvel-ao ~/Téléchargements/DCE-voirie.zip` lance le parcours du DCE,
  avec les arrêts de validation. Codex peut invoquer `$remporte:nouvel-ao` ou répondre à une demande
  naturelle.
- « Vérifie que chaque exigence du cadre de réponse est traitée dans le mémoire » : liste les
  exigences numérotées qui ne sont pas encore couvertes.
- « Remplis le DC1 et le DC2 pour ce marché » : remplit les formulaires officiels à partir de la
  fiche entreprise.

## Dépendance et fichiers

`remporte` est un outil en ligne de commande externe au plugin. Vérifiez sa présence avec
`remporte --version`. S'il manque, `$remporte:init` ou `/remporte:init` propose `uv tool install remporte`
après accord. Installer le plugin n'installe pas le CLI.

Les DCE et les documents sont lus depuis les fichiers accessibles à l'environnement choisi.
En local, ils peuvent se trouver sur votre poste. En cloud, ils se trouvent dans l'environnement
cloud et ne sont pas forcément présents sur votre poste. Le raisonnement passe par le fournisseur
de l'agent et suit ses conditions de traitement. Détails : [politique de confidentialité](https://remporte.fr/politique-confidentialite/#outil-agent-ia).

## Contenu

Le plugin fournit six skills : `init`, `nouvel-ao`, `repondre-ao`, `lecture-dce`,
`redaction-section`, `relecture-ao`. Il fournit aussi trois sous-agents Claude : `lecteur-dce`,
`redacteur-section`, `relecteur`. Les procédures métier partagées se trouvent dans
[references/](references/lecture-dce.md). Le plugin ne contient ni hook ni serveur MCP.

## Remporte, le logiciel en ligne

Ce plugin fonctionne avec le CLI et sans compte Remporte. Remporte existe aussi sous forme de
logiciel en ligne, distinct du plugin, qui ajoute une base de connaissance d'entreprise partagée,
la mise en forme du mémoire dans le modèle Word de l'entreprise, des plans prêts à adapter et le
remplissage des bordereaux de prix.

Présentation : https://remporte.fr/outils/agent-ia/

## En savoir plus

- Documentation complète et code source : https://github.com/Remporte-dev/remporte-appels-offres
- Licence : MIT

Édité par Remporte (Flowt).
