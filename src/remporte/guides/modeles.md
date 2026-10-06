# Quel modèle pour quelle tâche

Toutes les étapes ne demandent pas le même niveau de raisonnement. Utiliser
le modèle le plus capable partout épuise vite un abonnement ; un modèle léger
sur le go/no-go ou la rédaction donne une réponse faible.

| Tâche | Puissance conseillée | Pourquoi |
|---|---|---|
| Inventaire, conversion, recherche (`init`, `pieces`, `chercher`, `cadre`, `exporter`, `html`) | aucune : le CLI le fait | déterministe, ne consomme rien |
| Relever des faits dans un gros CCTP ou des annexes | **légère**, idéalement en sous-agent d'exploration | lecture volumineuse, peu de jugement |
| Analyse du RC et des critères (`analyse`) | **standard** | précision sur les pondérations et les pièces |
| Go/No-Go | **la plus capable** | décision qui engage l'entreprise |
| Plan du mémoire | **standard**, **la plus capable** s'il y a un CRT long | fidélité à la trame imposée |
| Rédaction des sections les plus pondérées | **la plus capable** | c'est là que se jouent les points |
| Rédaction des autres sections, annexes, CV | **standard** | |
| Relecture avec la grille de l'acheteur | **la plus capable**, de préférence un autre modèle ou un sous-agent neuf | un regard qui n'a pas écrit le texte voit mieux ses failles |
| Remplir un fichier imposé, la candidature | **standard** | report fidèle, peu d'invention |
| Mettre en page un document (`remporte html`) | aucune : écris du markdown, le CLI met en page | |

## Si ton agent sait lancer des sous-agents

- **Exploration** : confie à un sous-agent léger la lecture d'une pièce longue
  avec une question précise (« relève toutes les exigences de délais du CCTP,
  avec leur article »). Il rend une liste courte ; toi, tu gardes ton contexte
  pour décider et rédiger.
- **Rédaction en parallèle** : une section par sous-agent, chacun avec la
  ligne du plan, les passages du DCE et de la base qui la concernent.
- **Relecture** : un sous-agent qui n'a rien rédigé, à qui tu donnes la grille
  de notation et le mémoire exporté.

Sans sous-agents, garde le même ordre et lis les gros documents par
recherche ciblée (`remporte chercher`) plutôt qu'en entier.
