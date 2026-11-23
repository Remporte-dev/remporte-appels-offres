# Procédure de relecture d'une étape

Tu relis une étape que tu n'as pas produite, avant que la suivante ne parte. L'agent principal te donne le dossier de réponse et l'étape à relire. Tu ne modifies rien : tu écris `relectures/<étape>.md` (crée le dossier s'il manque), et l'agent principal applique les corrections.

Pour chaque point vérifié, donne un verdict (« bon », « à corriger » ou « bloquant »), la source (pièce, article, page, onglet ou ligne) et la correction précise. Vérifie dans le DCE avec `remporte chercher`, en repérant les pièces dans `01-pieces.md` et `00-index.md`, plutôt que de faire confiance au fichier relu.

| Étape | Ce que tu vérifies |
|---|---|
| analyse (`02-analyse.md`) | Critères et pondérations recopiés exactement du RC. Toutes les pièces exigées au RC, candidature et offre. Date et heure de remise, visite obligatoire, variantes, prestations supplémentaires ou options, durée de validité. Chaque ligne porte sa source. |
| plan (`04-plan.md`) | Chaque critère et sous-critère du RC a sa section. Le volume suit la pondération. La trame imposée par l'acheteur est suivie dans son ordre et sa numérotation. La limite de pages tient (`remporte formats`). |
| pièces (bordereau de prix, AE, DC1, DC2, DC4, cadre ou fichier imposé) | Trame de l'acheteur intacte : aucune ligne, colonne, onglet ou formule ajouté, supprimé ou réécrit. Identité, SIRET, signataire et chiffres conformes à `remporte fiche`. Lot et intitulé exacts. Montant de l'AE égal au total du bordereau. Chaque prix vient de l'entreprise ; un prix vide ou à zéro est signalé, jamais rempli. Sous-traitants déclarés. Pièces à signer listées. |
| mémoire (une section ou le mémoire entier) | Chaque engagement a sa preuve dans la base ou un `[à compléter : …]`. La section répond au critère servi dans `04-plan.md`. Les phrases que retient la liste « Contrôle avant de rendre » de `remporte guide style`, chacune avec sa réécriture. |
| autre livrable | Conformité au gabarit de l'acheteur et à ce que demandait l'agent principal. |

Il te manque une information pour juger un point : ne pose pas de question, écris `[à compléter : …]` dans ton rapport et continue.

Termine le fichier par une ligne de verdict : « l'étape peut continuer » ou « bloquant : … ».

## Compte rendu

Indique le fichier écrit, le verdict, le nombre de points à corriger et les trois plus graves.
