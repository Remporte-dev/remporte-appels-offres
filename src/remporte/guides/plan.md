# Étape « plan » — la trame du mémoire

Fichier à remplir : `04-plan.md`.

## Si le DCE contient un cadre de réponse (CRT)

Lance `remporte cadre`. Le plan reprend **ses titres, sa numérotation et son
ordre à l'identique**, sans en ajouter ni en fusionner. Un acheteur qui note
avec une grille cherche ses rubriques à leur place.

Si `remporte cadre` indique « origine : liste », le CRT numérote ses
exigences (« PP 001 », « PP 002 »…) et **l'acheteur note chacune d'elles**.
Regroupe-les par chapitre en sections, et indique dans chaque ligne du plan
les identifiants qu'elle traite (`- [ ] 03 — 5.1 Initialisation (PP 013 à
PP 019)`). Aucune exigence ne doit rester sans section.

## Sinon

Construis la trame à partir des critères et sous-critères du RC, dans leur
ordre, puis du contenu du mémoire demandé par le RC. Un sous-critère noté =
au moins une section qui y répond explicitement, dont le titre reprend ses
mots.

## Règles

- Une ligne par section : `- [ ] 01 — Compréhension du besoin`. Numéros sur
  deux chiffres, dans l'ordre du mémoire.
- Tableau de correspondance : chaque section en face du critère qu'elle sert,
  de son poids, et d'un volume visé proportionnel au poids et compatible avec
  la limite de pages du RC (compte environ 500 mots par page).
- Pas de section « Présentation de l'entreprise » longue si elle n'est pas
  notée : l'acheteur la lit dans la candidature. Une demi-page suffit.
- Ajoute en fin de plan les annexes demandées (CV, références, attestations,
  planning), sans les rédiger maintenant.

Puis crée un fichier vide par section dans `sections/` (`NN-titre.md`, titre
en minuscules, mots séparés par des tirets) et passe à
`remporte guide redaction`.
