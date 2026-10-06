# Répondre dans un fichier imposé (Excel ou Word)

> Puissance de modèle conseillée : standard (`remporte guide modeles`).

Quand l'acheteur fournit un questionnaire, un cadre de réponse ou une annexe
technique à compléter, **la réponse se donne dans son fichier**, pas dans un
document à part.

1. Ne modifie ni la structure, ni les onglets, ni les formules, ni les
   colonnes de l'acheteur. Remplis seulement les cellules ou les zones prévues
   pour le candidat.
2. Travaille sur une copie : `reponse/<nom du fichier>`, l'original reste
   dans `dce/`.
3. Utilise l'outil tableur ou traitement de texte dont tu disposes. Si tu
   n'en as aucun capable d'écrire ce format sans l'abîmer, ne bricole pas le
   fichier : rédige les réponses dans un markdown, une ligne par case à
   remplir avec sa référence (onglet, ligne, colonne), et dis à l'utilisateur
   qu'il faudra les reporter.
4. Le contenu vient du mémoire (`sections/`) et de la base : mêmes chiffres,
   mêmes engagements, mêmes noms. Une réponse plus courte ne doit pas
   contredire la version longue.
5. Relis le fichier rempli case par case avant de le déclarer prêt.

`remporte exporter` produit aussi `export/matrice-conformite.xlsx` : utile
pour suivre quelles exigences sont traitées et où.

Les **bordereaux de prix** (BPU, DPGF, DQE) et l'**acte d'engagement** ne se
remplissent pas ici : le report des prix dans le fichier de l'acheteur, sans
toucher à ses formules, est disponible avec Remporte (`remporte offre`).
