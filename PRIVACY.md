# Données et confidentialité

Ce document décrit ce que deviennent vos données quand vous utilisez le CLI `remporte` et ses
extensions publiées dans ce dépôt : plugin Claude Code, plugin Codex, extension Gemini CLI,
paquets Muse, Hermes et OpenClaw, archive portable. Il vaut pour le paquet PyPI `remporte`.

## En bref

- **Sans clé API Remporte, le plugin et le CLI ne font aucun appel réseau.** Aucune
  télémétrie, aucune mesure d'utilisation, aucun compte.
- **Avec une clé API Remporte, ils ne font qu'une chose sur le réseau : récupérer les données
  de votre entreprise** que vous avez vous-même déposées dans l'application Remporte. Ils
  n'envoient ni vos fichiers, ni le DCE.
- **Ils mettent des outils à la disposition de votre agent IA** : des commandes et des
  instructions qui s'exécutent dans l'environnement où vous les lancez.
- **Le traitement de vos documents par l'IA est fait par votre agent**, selon votre contrat
  avec son éditeur.
- **Les données confiées à l'application Remporte relèvent de cette application** et de sa
  politique de confidentialité.

## Ce que fait l'outil

- Il lit les fichiers que vous lui indiquez : les pièces du DCE et les documents de votre
  entreprise.
- Il écrit ses résultats dans l'espace de travail que vous avez choisi : `ressources/` pour
  la fiche entreprise et les documents de l'entreprise, `DCEs/` pour un dossier par
  consultation (analyse, plan, sections du mémoire, pages HTML, matrice de conformité).
- Il construit sur votre poste un index de recherche de ces documents, dans
  `ressources/.index/` de l'espace de travail, ou dans `~/.remporte/base/` hors d'un espace.
- À l'installation, le script `install_skills.py` copie les skills dans le dossier de
  l'agent que vous lui indiquez, et seulement avec l'option `--apply`.
- Il ne lit rien et n'écrit rien ailleurs.

Le plugin ne contient ni hook, ni serveur MCP, ni programme qui se lance tout seul : il ne
fait rien tant que votre agent n'appelle pas une de ses commandes.

## Ce qui sort de votre environnement

- **Sans clé API : rien, du fait du plugin ou du CLI.**
- **Avec une clé API** (fournie par l'équipe Remporte à votre entreprise), quand votre agent
  a besoin d'une de vos ressources Remporte (base de connaissances, fiche entreprise, charte),
  le CLI interroge `https://app.remporte.fr/api/cli/v1`. Il envoie la clé et la question de
  l'agent, qui peut reprendre des éléments du marché en cours (nature de la prestation,
  acheteur), et reçoit uniquement les données de votre entreprise. Aucun fichier de votre
  poste et aucune pièce du DCE ne sont envoyés.
- **À l'installation**, votre agent télécharge le CLI depuis PyPI (`uv tool install remporte`),
  après votre accord, et le plugin depuis GitHub. Ces téléchargements suivent les conditions
  de PyPI et de GitHub.

## Votre agent IA

Les documents que votre agent lit sont traités par le modèle qu'il utilise (Claude, GPT,
Gemini ou un autre), dans les conditions de son éditeur et de votre abonnement. Remporte ne
reçoit pas ces échanges et n'y a pas accès. Pour savoir où vont ces données, combien de temps
elles sont conservées et si elles servent à entraîner des modèles, reportez-vous aux
conditions de votre fournisseur.

## L'application Remporte

Les données que votre entreprise dépose dans l'application Remporte (base de connaissances,
références, fiche entreprise, charte) sont traitées par l'application, selon le contrat de
votre entreprise et la politique de confidentialité de Remporte, conformément au RGPD.
L'application et son API sont hébergées en France. Politique de confidentialité :
https://remporte.fr/politique-confidentialite/. C'est l'application qui décide qui accède à ces
données, ce qui est conservé et pendant combien de temps. La clé API ne donne accès qu'aux
données de votre entreprise ; elle se révoque sur simple demande à l'équipe Remporte.
Gardez-la secrète, comme un mot de passe.

## Contact

- Questions sur vos données, signalement d'un problème de sécurité : contact@remporte.fr
- Bugs et aide à l'utilisation :
  [issues GitHub](https://github.com/Remporte-dev/remporte-appels-offres/issues)

Éditeur : Flowt (Remporte).

---

## English summary

- **Without a Remporte API key, the plugin and the `remporte` CLI make no network calls**: no
  telemetry, no usage analytics, no account.
- **With a Remporte API key**, their only network activity is to fetch your company's own data
  that you uploaded to the Remporte application (knowledge base, company profile, style guide),
  from `https://app.remporte.fr/api/cli/v1`. They send the key and the agent's question, which
  may mention elements of the current tender (type of work, buyer), never your local files or
  the tender documents.
- They provide tools to your AI agent: commands and instructions that run where you launch
  them. They read the files you point them to and write only to your chosen workspace
  (`ressources/`, `DCEs/`, a local search index in `ressources/.index/` or `~/.remporte/base/`).
- No hooks, no MCP server, nothing runs on its own.
- Installation downloads the CLI from PyPI and the plugin from GitHub, with your consent.
- Your documents are processed by your own AI agent under its provider's terms; Remporte has no
  access to those exchanges.
- Data stored in the Remporte application, and API key access to it, are governed by that
  application (hosted in France, GDPR) and its privacy policy: https://remporte.fr/politique-confidentialite/
- Contact: contact@remporte.fr (data and security), GitHub issues (support).
