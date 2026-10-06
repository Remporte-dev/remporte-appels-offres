# La candidature : DC1, DC2, DC4

> Puissance de modèle conseillée : standard (`remporte guide modeles`).

La candidature dit si l'entreprise est recevable ; elle est examinée avant
l'offre. Une pièce manquante peut suffire à écarter le dossier.

1. Vérifie dans `02-analyse.md` ce que le RC demande : DC1 et DC2, ou DUME,
   attestations, références, chiffres d'affaires, assurances.
2. `remporte candidature preparer` crée `candidature/valeurs.json` : un champ
   par rubrique des formulaires officiels, valeur vide.
3. Remplis les valeurs avec `remporte base chercher` et `02-analyse.md`
   (acheteur, objet, lot). **N'invente rien** : un champ sans source reste
   vide et part dans la liste à demander à l'utilisateur. Les cases à cocher
   prennent une des options proposées.
4. `remporte candidature remplir` produit `candidature/DC1.docx`, `DC2.docx`,
   et `DC4.docx` si une part est sous-traitée. Relis-les et liste les champs
   restés vides.
5. Rappelle à l'utilisateur ce qui ne se génère pas : attestations fiscales et
   sociales, extrait K-bis, attestation d'assurance, signature.
