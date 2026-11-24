# Répondre dans un fichier imposé (Excel ou Word)

> Puissance de modèle conseillée : standard (`remporte guide modeles`).

Quand l'acheteur fournit un questionnaire, un cadre de réponse ou une annexe
technique à compléter, **la réponse se donne dans son fichier**, pas dans un
document à part.

1. Ne modifie ni la structure, ni les onglets, ni les formules, ni les
   colonnes de l'acheteur. Remplis seulement les cellules ou les zones prévues
   pour le candidat.
2. Travaille sur une copie dans le dossier de remise (`remporte livraison
   dossier`, avec `--lot <id>` pour un lot) ; l'original reste dans `dce/`.
   Un `.doc` ou un `.xls` se convertit d'abord :
   `remporte convertir "dce/<fichier>" --lot <id>` écrit la copie au format
   actuel (`.docx`, `.xlsx`) dans ce dossier, sans jamais écraser un fichier.
3. Utilise l'outil tableur ou traitement de texte dont tu disposes. Si tu
   n'en as aucun capable d'écrire ce format sans l'abîmer, ne bricole pas le
   fichier : rédige les réponses dans un markdown, une ligne par case à
   remplir avec sa référence (onglet, ligne, colonne), et dis à l'utilisateur
   qu'il faudra les reporter.
4. Le contenu vient du mémoire (`sections/`) et de la base : mêmes chiffres,
   mêmes engagements, mêmes noms. Une réponse plus courte ne doit pas
   contredire la version longue.
5. Relis le fichier rempli case par case avant de le déclarer prêt.

**Ancien format (`.doc`, `.xls`).** `remporte convertir` dit la méthode
employée :
- **LibreOffice** (installé sur le poste) : conversion fidèle, formules et
  mise en page comprises ;
- **conversion simplifiée** : le tableur garde ses valeurs mais **perd ses
  formules**, le document Word garde son texte mais perd sa mise en page.
  Dis-le à l'utilisateur ; dans un bordereau, recalcule chaque total et
  remets les formules de l'acheteur avant de livrer, ou propose-lui
  d'installer LibreOffice et de relancer la conversion.
N'installe jamais d'outil de toi-même pour lire ou convertir une pièce. Si le
RC exige de rendre le fichier dans son format d'origine, dis à l'utilisateur
de réenregistrer le fichier rempli en `.xls` ou `.doc` depuis son logiciel.

`remporte exporter` produit aussi `export/matrice-conformite.xlsx` : utile
pour suivre quelles exigences sont traitées et où.

Les **bordereaux de prix** (BPU, DPGF, DQE) ont leur guide :
`remporte guide chiffrage`.
