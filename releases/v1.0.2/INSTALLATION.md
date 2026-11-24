# Installer Remporte dans son agent

La version 1.0.2 utilise la même méthode pour toutes les plateformes. Les archives sont produites depuis `plugin/skills/` et `plugin/references/`. Les différences portent sur le format d'installation et l'accès aux fichiers.

Sur toutes les plateformes, l'utilisateur ne tape aucune commande Remporte : il donne le
chemin de son DCE à l'agent et lui demande, en français, « Aide-moi à répondre à cet appel
d'offres ». Une seule compétence sert de porte d'entrée, `repondre-ao` : elle lit le DCE,
fait choisir les lots, puis conduit l'analyse, le go/no-go, le chiffrage, le mémoire si vous
le retenez, les autres pièces et la remise. La compétence `init` met Remporte en route ;
l'agent la propose de lui-même quand l'outil ou la fiche entreprise manque. Les commandes
`remporte` restent les outils de l'agent.

Dans les archives de compétences autonomes, chaque nom prend le préfixe `remporte-` : la
porte d'entrée s'appelle `remporte-repondre-ao` et la mise en route `remporte-init`. Les
plateformes qui demandent d'appeler une compétence par son nom utilisent ces deux noms.

| Plateforme | Format livré | Pour démarrer |
|---|---|---|
| Claude Code | plugin Claude avec quatre agents et douze compétences | demande naturelle ; par son nom : `/remporte:repondre-ao`, `/remporte:init` |
| Codex | plugin OpenAI (douze compétences) et catalogue local | demande naturelle ; par son nom : `$remporte:repondre-ao`, `$remporte:init` |
| ChatGPT Work | plugin OpenAI ou paquet cloud avec CLI | environnement avec commandes et fichiers, puis demande naturelle |
| Gemini CLI | extension `gemini-extension.json`, `GEMINI.md`, douze compétences | demande naturelle, ou « Utilise la compétence remporte-repondre-ao » |
| Hermes Agent (Nous) | douze compétences Agent Skills autonomes | `/remporte-repondre-ao`, `/remporte-init` |
| OpenClaw | douze compétences Agent Skills autonomes | demande naturelle, ou la compétence `remporte-repondre-ao` par son nom |
| Pi | douze compétences Agent Skills autonomes | `/skill:remporte-repondre-ao`, `/skill:remporte-init` |
| Muse (muse.ai, Meta) | paquet cloud : CLI, compétences, demande de démarrage | déposer le paquet dans Muse et lui faire lire `DEMARRAGE.md` |
| Autres agents | archive Agent Skills standard | mécanisme de compétences documenté par l'agent, ou lecture directe de `remporte-repondre-ao` |

Les quatre sous-agents (`lecteur-dce`, `redacteur-section`, `relecteur`,
`controleur-coherence`) ne sont livrés que dans le plugin Claude. Ailleurs, la porte
d'entrée confie ces étapes à un sous-agent générique quand la plateforme en propose un, ou
l'agent les fait lui-même dans le même ordre.

Les commandes et les documents doivent être accessibles dans l'environnement de l'agent. L'installation des compétences seule n'installe pas le CLI. Chaque compétence portable contient ses références : on peut la copier séparément.

## Préparer le poste et les documents

Installez et connectez votre agent à un modèle avec sa procédure officielle. Les compétences Remporte ne créent pas cette connexion : sans abonnement ou clé utilisable dans cet agent, elles sont visibles mais ne peuvent pas effectuer l’analyse.

Installez [uv](https://docs.astral.sh/uv/getting-started/installation/) si nécessaire, puis lancez dans le terminal :

```bash
uv tool install --upgrade remporte
remporte espace ~/Remporte
cd ~/Remporte
```

Ajoutez vos documents d’entreprise dans `ressources/` et complétez `ressources/fiche-entreprise.md`, créée par la commande précédente. Depuis `~/Remporte`, lancez `remporte base indexer`. Rouvrez ensuite votre agent dans cet espace. Les nouveaux DCE y sont rangés dans `DCEs/` et retrouvent la base de l’entreprise.

Téléchargez l’archive de votre plateforme dans [la release Remporte](https://github.com/Remporte-dev/remporte-appels-offres/releases/latest). Pour la version 1.0.2 : `remporte-gemini-1.0.2.zip`, `remporte-hermes-1.0.2.zip`, `remporte-openclaw-1.0.2.zip` ou `remporte-pi-1.0.2.zip`. Décompressez-la dans un nouveau dossier avant de suivre les instructions ci-dessous.

## Claude Code et Codex

Claude Code : dans sa conversation, ajoutez le catalogue et installez le plugin.

```text
/plugin marketplace add Remporte-dev/remporte-appels-offres
/plugin install remporte@remporte
```

Rouvrez Claude Code dans `~/Remporte`, puis demandez « Aide-moi à répondre à cet appel d'offres : /chemin/vers/DCE.zip ». À la première utilisation, l'agent propose la mise en route. Pour appeler les compétences par leur nom : `/remporte:repondre-ao` et `/remporte:init`.

Codex : dans le terminal, installez le plugin natif.

```bash
codex plugin marketplace add Remporte-dev/remporte-appels-offres
codex plugin add remporte@remporte
```

Rouvrez Codex dans `~/Remporte`. Dans sa conversation, demandez « Aide-moi à répondre à cet appel d'offres : /chemin/vers/DCE.zip ». Pour appeler les compétences par leur nom : `$remporte:repondre-ao` et `$remporte:init`. Ces mentions de compétences ne sont pas des commandes à exécuter dans le terminal.

## Mettre à jour une installation existante

La commande `uv tool install --upgrade remporte` installe ou met à jour le CLI en rafraîchissant le cache de versions.

Pour Claude Code, dans le terminal :

```bash
claude plugin marketplace update remporte
claude plugin update remporte@remporte --scope user
```

Si le plugin était installé pour un projet seulement, lancez la mise à jour depuis ce projet avec son périmètre `project` ou `local` plutôt que `user`.

Pour Codex, rafraîchissez d’abord le catalogue, puis réinstallez le plugin :

```bash
codex plugin marketplace upgrade remporte
codex plugin remove remporte@remporte
codex plugin add remporte@remporte
```

Rouvrez l’agent après la mise à jour. Les dossiers d’entreprise et de réponse restent dans votre espace de travail. Pour les compétences portables, sauvegardez les anciens dossiers `remporte-*` avant de les retirer du dossier de compétences et d’installer la nouvelle archive : le script d’installation refuse de les écraser. L’ancienne compétence `remporte-nouvel-ao` n’existe plus : `remporte-repondre-ao` la remplace, retirez son dossier s’il est encore présent.

## Gemini CLI

Décompressez l'archive Gemini dans un nouveau dossier `remporte`, puis installez ce dossier : le manifeste `gemini-extension.json` est à sa racine.

```bash
gemini extensions install /chemin/vers/remporte
```

Redémarrez Gemini, vérifiez que l'extension est active, puis demandez « Aide-moi à répondre à cet appel d'offres : /chemin/vers/DCE.zip ». Si Gemini ne sélectionne pas la compétence de lui-même, nommez-la : « Utilise la compétence remporte-repondre-ao avec ce DCE ». Pour la mise en route : « Utilise la compétence remporte-init pour préparer mon entreprise ». Le CLI crée aussi un `GEMINI.md` qui importe le contexte commun `AGENTS.md`, dans l'espace de travail et dans chaque réponse.

Cette extension contient des compétences et du contexte. Elle ne déclare pas de serveur MCP. L'installation depuis l'URL Git du dépôt principal n'est pas proposée : le manifeste Gemini est dans l'archive dédiée.

## Hermes, OpenClaw et Pi

Décompressez l'archive dédiée. Depuis son dossier `remporte/`, affichez d'abord les destinations :

```bash
python3 install_skills.py --source ./skills --destination ~/.hermes/skills
# OpenClaw : --destination ~/.openclaw/skills
# Pi : --destination ~/.pi/agent/skills
```

Ajoutez `--apply` pour installer. Le script refuse les compétences déjà présentes et les liens symboliques. Il ne modifie pas les réglages de l'agent. Pour un profil ou un dossier de travail spécifique, indiquez son dossier de compétences documenté à la place de ces destinations par défaut. Rechargez les compétences ou ouvrez une nouvelle session. Vérifiez leur présence avec `hermes skills list --source local`, `openclaw skills list` ou le catalogue de compétences de Pi. Si l’agent indique qu’aucun modèle n’est connecté, terminez sa connexion avant de demander une analyse.

Avec Hermes, appelez la porte d'entrée par son nom : `/remporte-repondre-ao`, suivi de « Aide-moi à répondre à cet appel d'offres » et du chemin du DCE. `/remporte-init` lance la mise en route. Avec OpenClaw, vérifiez leur découverte avec `openclaw skills check`, puis demandez « Aide-moi à répondre à cet appel d'offres » ou nommez la compétence `remporte-repondre-ao`. Avec Pi : `/skill:remporte-repondre-ao`, et `/skill:remporte-init` pour la mise en route.

Pour OpenClaw, choisissez comme espace de travail le dossier Remporte qui contient à la fois `ressources/` et `DCEs/`. Si vous ouvrez seulement un sous-dossier de réponse, l’accès aux documents d’entreprise peut être bloqué par la limite de cet espace. Exemple depuis le terminal, une fois le modèle connecté :

```bash
openclaw agent exec --cwd "$HOME/Remporte" \
  "Utilise remporte-repondre-ao : aide-moi à répondre à cet appel d'offres, /chemin/vers/DCE.zip"
```

Adaptez ce chemin si votre espace Remporte porte un autre nom. Avec Pi, vous pouvez aussi charger explicitement les compétences sans installation globale :

```bash
pi --skill /chemin/vers/remporte/skills
```

## Muse et ChatGPT Work dans le cloud

Le paquet cloud inclut le CLI Python de la même version, les compétences et `DEMARRAGE.md`. Transférez l'archive dans l'environnement de l'agent, puis demandez-lui :

> Décompresse le paquet Remporte dans un nouveau dossier et lis son fichier DEMARRAGE.md. Vérifie les accès aux commandes et aux fichiers avant de commencer. Accompagne-moi pour la mise en route, puis pour répondre à mon DCE.

`DEMARRAGE.md` renvoie l'agent vers la mise en route (`remporte-init`), puis vers la porte d'entrée (`remporte-repondre-ao`). L'agent vérifie la présence du CLI et propose, si nécessaire, l'installation du fichier `.whl` fourni. Cette installation peut télécharger ses dépendances Python. Les autorisations réseau et d'installation de la plateforme restent applicables. Fournissez les documents d'entreprise et le DCE dans ce même environnement ; un chemin du Mac ne leur donne pas accès au fichier.

Les compétences peuvent être lues directement. Le paquet ne présume pas d'un dossier système de compétences propre à Muse. Un connecteur Muse référencé dans son annuaire est un autre mode de distribution, avec une API ou un serveur MCP et une procédure de soumission. Aucun connecteur distant n'est déployé par ces scripts.

Une conversation ChatGPT dépourvue d'accès aux commandes ne peut pas exécuter ce CLI. Utilisez un environnement Work qui dispose de cet accès ou Codex.

## Construire les archives

Depuis le dépôt :

```bash
uv run python scripts/package_plugin.py --platform claude --output dist/remporte-claude.zip
uv run python scripts/package_plugin.py --platform openai --output dist/remporte-openai.zip
uv run python scripts/package_skills.py --platform gemini --output dist/remporte-gemini.zip
uv run python scripts/package_skills.py --platform hermes --output dist/remporte-hermes.zip
uv run python scripts/package_skills.py --platform openclaw --output dist/remporte-openclaw.zip
uv run python scripts/package_skills.py --platform pi --output dist/remporte-pi.zip
uv run python scripts/package_skills.py --platform portable --output dist/remporte-portable.zip
uv build --wheel --out-dir dist/cli
uv run python scripts/package_cloud.py --platform muse --wheel dist/cli/remporte-1.0.2-py3-none-any.whl --output dist/remporte-muse.zip
uv run python scripts/package_cloud.py --platform chatgpt-work --wheel dist/cli/remporte-1.0.2-py3-none-any.whl --output dist/remporte-chatgpt-work.zip
```

Les archives Gemini, Hermes, OpenClaw, Pi et portable contiennent les douze compétences, chacune avec ses procédures dans `references/`. L'archive OpenAI ne contient pas les sous-agents, qui sont propres à Claude Code. Les scripts refusent d'écraser une archive existante. Les paquets cloud refusent un CLI d'une autre version. Les archives n'installent rien dans un compte ni dans les dossiers de l'utilisateur lors de leur construction.

## Vérifications et limites

Les tests contrôlent les formats, les noms des compétences, les références après copie isolée, les conflits d’installation et la cohérence entre CLI et compétences. L’installation du CLI et des plugins Claude Code et Codex est vérifiée à chaque modification sur macOS, Linux et Windows. Le parcours par lot (tri, choix et analyse des lots, dossier de remise par lot) est couvert par les tests du CLI ; il n’a pas encore été déroulé de bout en bout dans chacun des agents. Gemini CLI, Hermes, OpenClaw, Muse et ChatGPT Work n’ont pas été essayés en session réelle sur ce parcours.

Sources des formats : [Gemini extensions](https://geminicli.com/docs/extensions/reference/), [contexte Gemini](https://geminicli.com/docs/cli/gemini-md/), [Hermes Skills](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills/), [OpenClaw Skills](https://docs.openclaw.ai/tools/skills), [Muse et son environnement cloud](https://research.meta.ai/blog/security-and-safety-for-ai-agents-our-approach-with-muse), [connecteurs Muse](https://muse.ai/platform/docs), [Pi Skills](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/skills.md).
