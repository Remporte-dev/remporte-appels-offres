# Remporte : répondre aux appels d'offres publics avec un agent IA

Plugin gratuit et open source pour répondre à un marché public français : lecture du DCE,
analyse, décision go/no-go, plan du mémoire technique, rédaction, contrôle de conformité,
relecture, bordereaux de prix, formulaires DC1/DC2/DC4, documents de travail en HTML et
matrice de conformité Excel.

Les instructions servent à Claude Code, Cowork, Codex et ChatGPT Work lorsque l'environnement
donne accès aux commandes et aux fichiers concernés. Il faut pouvoir lancer des commandes et
lire/écrire les fichiers. Dans un environnement cloud, les fichiers sont ceux accessibles dans
cet environnement et ne sont pas forcément présents sur votre ordinateur.

## Exemples

- « Prépare Remporte pour mon entreprise » : prépare l'espace de travail et la fiche entreprise.
- « Analyse ce DCE : ~/Téléchargements/DCE-voirie.zip » : lit les pièces, présente les lots et la
  date de remise, puis analyse les lots que vous retenez, avec les questions à poser à l'acheteur.
- « Je prends le lot 3 » ou « reprends le dossier voirie » : poursuit la réponse là où elle en est.
- « Vérifie que chaque exigence du cadre de réponse est traitée dans le mémoire » : liste les
  exigences numérotées qui ne sont pas encore couvertes.
- « Remplis le DC1 et le DC2 pour ce marché » : remplit les formulaires officiels à partir de la
  fiche entreprise.

## Dépendance et fichiers

`remporte` est un outil en ligne de commande externe au plugin. Vérifiez sa présence avec
`remporte --version`. S'il manque, la mise en route propose de l'installer
après accord. Installer le plugin n'installe pas le CLI.

Les DCE et les documents sont lus depuis les fichiers accessibles à l'environnement choisi.
En local, ils peuvent se trouver sur votre poste. En cloud, ils se trouvent dans l'environnement
cloud et ne sont pas forcément présents sur votre poste. Le raisonnement passe par le fournisseur
de l'agent et suit ses conditions de traitement. Sans clé API Remporte, le plugin et le CLI ne font aucun
appel réseau ; avec une clé, ils récupèrent seulement les données de votre entreprise déposées
dans l'application Remporte : [données et confidentialité](https://github.com/Remporte-dev/remporte-appels-offres/blob/main/PRIVACY.md).

## Contenu

Le plugin fournit douze skills : `init`, `repondre-ao` (la porte d'entrée : nouveau DCE ou
reprise d'un dossier), `lecture-dce`, `redaction-section`, `relecture-ao`,
`memoire-technique`, `cadre-reponse`, `fichier-impose`, `chiffrage`, `visuels`, `soutenance` et
`candidature`. Il fournit aussi quatre sous-agents Claude : `lecteur-dce`,
`redacteur-section`, `relecteur` (mémoire ou étape) et `controleur-coherence` (montants,
délais, moyens et engagements recoupés entre toutes les pièces). Les procédures métier partagées se trouvent dans
[references/](references/lecture-dce.md). Le plugin ne contient ni hook ni serveur MCP.

## Clé API Remporte

Le plugin fonctionne avec le CLI, sans compte Remporte. Une clé API Remporte donne en plus à
votre agent accès aux données que votre entreprise a déposées dans l'application Remporte :
base de connaissances, fiche entreprise, charte. Créer votre clé :
https://remporte.fr/outils/agent-ia/#cle-api

## En savoir plus

- Documentation complète et code source : https://github.com/Remporte-dev/remporte-appels-offres
- Licence : MIT

Édité par Remporte (Flowt).
