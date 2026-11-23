# Étape « relecture » : se mettre à la place de l'acheteur

> Puissance de modèle conseillée : la plus capable, de préférence un regard neuf (autre modèle ou sous-agent) (`remporte guide modeles`).

Fichier à remplir : `05-relecture.md`.

**Qui corrige.** Les étapes ci-dessous disent « corrige », « complète »,
« ajoute ». Si tu relis un mémoire que tu n'as pas rédigé, tu ne modifies
aucune section : écris chaque correction dans `05-relecture.md` (section,
passage, texte à mettre), et l'agent principal l'applique puis remplit
« Corrections faites ». Si tu relis ton propre texte, remplis d'abord le
fichier, puis corrige.

1. **Note le mémoire avec la grille de l'acheteur.** Pour chaque critère et
   sous-critère du RC : quelles sections y répondent, quelles preuves elles
   apportent, et un verdict franc (« couvert », « faible », « absent »). Un
   verdict faible ou absent → corrige la section.
2. **Si le CRT numérote ses exigences**, lance `remporte cadre --couverture`
   et complète les sections jusqu'à ce que toutes soient citées.
3. **Repasse le CCTP** : liste les exigences qui ne trouvent aucune réponse
   dans le mémoire, puis ajoute-les à la bonne section.
4. **Chasse les généralités** : toute phrase qui ne nomme rien de ce marché
   est réécrite ou supprimée.
5. **Contrôle le style** : passe chaque section à la liste « Contrôle avant
   de rendre » de `remporte guide style`. Note dans « Style » la section, la
   phrase relevée et sa réécriture, puis corrige. Une réécriture n'ajoute
   aucun fait : ce qui manque s'écrit `[à compléter : …]`.
6. **Vérifie la cohérence** : mêmes effectifs, délais, noms et chiffres d'une
   section à l'autre ; mêmes engagements que ceux qui figureront dans l'AE et
   le bordereau de prix.
7. **Rassemble les manques** : liste tous les `[à compléter : …]` restants
   (`remporte chercher` ne les trouve pas : relis les sections), groupés par
   personne à qui les demander.
8. **Contrôle des pièces** : reprends la liste des pièces à remettre de
   `02-analyse.md`, pièce par pièce, avec l'état (prête, à signer, à obtenir).
   Vérifie le nombre de pages maximal et le format imposé.
9. Note dans « Corrections faites » ce que tu as modifié.

Puis `remporte guide export`.
