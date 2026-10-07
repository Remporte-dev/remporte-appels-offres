# Installer Remporte dans son agent

La version 0.6.1 utilise la même méthode pour toutes les plateformes. Les archives sont produites depuis `plugin/skills/` et `plugin/references/`. Les différences portent sur le format d'installation et l'accès aux fichiers.

| Plateforme | Format livré | Utilisation |
|---|---|---|
| Claude Code | plugin Claude avec trois agents et six compétences | `/remporte:init`, `/remporte:nouvel-ao` |
| Codex | plugin OpenAI et catalogue local | `$remporte:init`, `$remporte:nouvel-ao` |
| ChatGPT Work | plugin OpenAI ou paquet cloud avec CLI | environnement avec commandes et fichiers |
| Gemini CLI | extension `gemini-extension.json`, `GEMINI.md`, six compétences | demande naturelle, sélection de la compétence Remporte |
| Hermes Agent (Nous) | six compétences Agent Skills autonomes | `/remporte-init`, `/remporte-nouvel-ao` |
| OpenClaw | six compétences Agent Skills autonomes | demande naturelle, compétences découvertes dans le dossier choisi |
| Pi | six compétences Agent Skills autonomes | `/skill:remporte-init`, `/skill:remporte-nouvel-ao` |
| Muse (muse.ai, Meta) | paquet cloud : CLI, compétences, demande de démarrage | déposer le paquet dans Muse et lui faire lire `DEMARRAGE.md` |
| Autres agents | archive Agent Skills standard | mécanisme de compétences documenté par l'agent ou lecture directe |

Les commandes et les documents doivent être accessibles dans l'environnement de l'agent. L'installation des compétences seule n'installe pas le CLI. Chaque compétence portable contient ses références : on peut la copier séparément.

## Préparer le poste et les documents

Installez et connectez votre agent à un modèle avec sa procédure officielle. Les compétences Remporte ne créent pas cette connexion : sans abonnement ou clé utilisable dans cet agent, elles sont visibles mais ne peuvent pas effectuer l’analyse.

Installez [uv](https://docs.astral.sh/uv/getting-started/installation/) si nécessaire, puis lancez dans le terminal :

```bash
uv tool install remporte
remporte espace ~/Remporte
cd ~/Remporte
```

Ajoutez vos documents d’entreprise dans `ressources/` et complétez `ressources/fiche-entreprise.md`, créée par la commande précédente. Depuis `~/Remporte`, lancez `remporte base indexer`. Rouvrez ensuite votre agent dans cet espace. Les nouveaux DCE y sont rangés dans `DCEs/` et retrouvent la base de l’entreprise.

Téléchargez l’archive de votre plateforme dans [la release Remporte](https://github.com/Remporte-dev/remporte-appels-offres/releases/latest). Pour la version 0.6.1 : `remporte-gemini-0.6.1.zip`, `remporte-hermes-0.6.1.zip`, `remporte-openclaw-0.6.1.zip` ou `remporte-pi-0.6.1.zip`. Décompressez-la dans un nouveau dossier avant de suivre les instructions ci-dessous.

## Claude Code et Codex

Claude Code : dans sa conversation, ajoutez le catalogue et installez le plugin.

```text
/plugin marketplace add Remporte-dev/remporte-appels-offres
/plugin install remporte@remporte
```

Rouvrez Claude Code dans `~/Remporte`, puis utilisez `/remporte:init` et `/remporte:nouvel-ao /chemin/vers/DCE.zip`.

Codex : dans le terminal, installez le plugin natif.

```bash
codex plugin marketplace add Remporte-dev/remporte-appels-offres
codex plugin add remporte@remporte
```

Rouvrez Codex dans `~/Remporte`. Dans sa conversation, utilisez `$remporte:init`, puis `$remporte:nouvel-ao /chemin/vers/DCE.zip`. Ces mentions de compétences ne sont pas des commandes à exécuter dans le terminal.

## Gemini CLI

Décompressez l'archive Gemini, puis installez le dossier `remporte/` qui contient le manifeste :

```bash
gemini extensions install /chemin/vers/remporte
```

Redémarrez Gemini, vérifiez que l'extension est active, puis demandez « Utilise la compétence remporte-init pour préparer mon entreprise ». Pour un DCE : « Utilise remporte-nouvel-ao avec ce dossier ». Le CLI crée aussi un `GEMINI.md` qui importe le contexte commun `AGENTS.md`, dans l'espace de travail et dans chaque réponse.

Cette extension contient des compétences et du contexte. Elle ne déclare pas de serveur MCP. L'installation depuis l'URL Git du dépôt principal n'est pas proposée : le manifeste Gemini est dans l'archive dédiée.

## Hermes, OpenClaw et Pi

Décompressez l'archive dédiée. Depuis son dossier `remporte/`, affichez d'abord les destinations :

```bash
python3 install_skills.py --source ./skills --destination ~/.hermes/skills
# OpenClaw : --destination ~/.openclaw/skills
# Pi : --destination ~/.pi/agent/skills
```

Ajoutez `--apply` pour installer. Le script refuse les compétences déjà présentes et les liens symboliques. Il ne modifie pas les réglages de l'agent. Pour un profil ou un dossier de travail spécifique, indiquez son dossier de compétences documenté à la place de ces destinations par défaut. Rechargez les compétences ou ouvrez une nouvelle session. Vérifiez leur présence avec `hermes skills list --source local`, `openclaw skills list` ou le catalogue de compétences de Pi. Si l’agent indique qu’aucun modèle n’est connecté, terminez sa connexion avant de demander une analyse.

Avec Hermes, utilisez `/remporte-init`, puis `/remporte-nouvel-ao <DCE>`. Avec OpenClaw, vérifiez leur découverte avec `openclaw skills check`, puis demandez la compétence par son nom. Avec Pi, vous pouvez aussi charger explicitement les compétences sans installation globale :

```bash
pi --skill /chemin/vers/remporte/skills
```

## Muse et ChatGPT Work dans le cloud

Le paquet cloud inclut le CLI Python de la même version, les compétences et `DEMARRAGE.md`. Transférez l'archive dans l'environnement de l'agent, puis demandez-lui :

> Décompresse le paquet Remporte dans un nouveau dossier et lis son fichier DEMARRAGE.md. Vérifie les accès aux commandes et aux fichiers avant de commencer. Accompagne-moi pour la mise en route, puis pour répondre à mon DCE.

L'agent vérifie la présence du CLI et propose, si nécessaire, l'installation du fichier `.whl` fourni. Cette installation peut télécharger ses dépendances Python. Les autorisations réseau et d'installation de la plateforme restent applicables. Fournissez les documents d'entreprise et le DCE dans ce même environnement ; un chemin du Mac ne leur donne pas accès au fichier.

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
uv run python scripts/package_cloud.py --platform muse --wheel dist/cli/remporte-0.6.1-py3-none-any.whl --output dist/remporte-muse.zip
uv run python scripts/package_cloud.py --platform chatgpt-work --wheel dist/cli/remporte-0.6.1-py3-none-any.whl --output dist/remporte-chatgpt-work.zip
```

Les scripts refusent d'écraser une archive existante. Les paquets cloud refusent un CLI d'une autre version. Les archives n'installent rien dans un compte ni dans les dossiers de l'utilisateur lors de leur construction.

## Vérifications et limites

Les tests contrôlent les formats, les six noms de compétences, les références après copie isolée, les conflits d'installation et la cohérence entre CLI et compétences. Le plugin Claude et le plugin Codex ont aussi été chargés par leurs outils locaux de lecture. L'exécution réelle dans Gemini, Hermes, OpenClaw, Muse et ChatGPT Work demande une session de ces plateformes ; une archive conforme n'est pas la preuve d'un parcours complet dans un compte utilisateur.

Sources des formats : [Gemini extensions](https://geminicli.com/docs/extensions/reference/), [contexte Gemini](https://geminicli.com/docs/cli/gemini-md/), [Hermes Skills](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills/), [OpenClaw Skills](https://docs.openclaw.ai/tools/skills), [Muse et son environnement cloud](https://research.meta.ai/blog/security-and-safety-for-ai-agents-our-approach-with-muse), [connecteurs Muse](https://muse.ai/platform/docs), [Pi Skills](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/skills.md).
