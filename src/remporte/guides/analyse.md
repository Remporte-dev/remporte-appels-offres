# Étape « analyse » : lire le DCE, trier les lots, analyser les lots retenus

> Puissance de modèle conseillée : standard (`remporte guide modeles`).

Lis d'abord, ne pose aucune question avant. Si un sous-agent lecteur est
disponible, il fait l'index et le tri, puis l'analyse de chaque lot retenu
(un sous-agent par lot) ; tu gardes l'annonce et le choix des lots.

## 1. Index et tri

1. `00-index.md` : une entrée par pièce de `01-pieces.md`, dans son ordre
   (type et chemin, lots concernés ou « commun », contenu en deux lignes,
   articles ou pages à retenir). Le RC en premier : il dit comment le marché
   est alloti. Le lot d'une pièce se lit dans son contenu, jamais dans son
   seul nom de fichier.
2. `memoire/lots.json`, exactement dans cette forme :

   ```json
   {
     "schema_version": 1,
     "allotissement": "lots",
     "lots": [
       {"id": "02", "intitule": "Électricité courants forts",
        "pieces": ["dce/LOT 02/CCTP lot 02.pdf"],
        "parties_communes": [],
        "recommandation": {"avis": "repondre",
                           "raison": "Électricité générale : le cœur du métier de l'entreprise."}}
     ],
     "pieces_communes": ["dce/RC.pdf", "dce/CCAP.pdf"],
     "pieces_illisibles": [],
     "types_pieces": {"dce/RC.pdf": "RC", "dce/CCAP.pdf": "CCAP",
                      "dce/LOT 02/CCTP lot 02.pdf": "CCTP"},
     "choix": null
   }
   ```

   - `allotissement` : `lots`, ou `unique` pour un marché non alloti, qui a
     alors un seul lot d'`id` `"unique"`.
   - `id` : le numéro du lot tel que le RC l'écrit ; `intitule` : son objet.
   - `recommandation.avis` : `repondre`, `a_discuter` ou `ne_pas_repondre`,
     au regard du métier de l'entreprise (fiche) ; `raison` en une phrase.
     C'est un avis : l'utilisateur décide.
   - `parties_communes` : les autres lots dont celui-ci partage des
     prestations, sinon `[]`.
   - Chemins : ceux de `01-pieces.md`, précédés de `dce/`. Chaque pièce
     lisible est rangée au moins une fois : dans un lot (une pièce propre à
     deux lots va dans les deux), dans `pieces_communes`, ou, si l'inventaire
     la dit illisible, dans `pieces_illisibles`.
   - `types_pieces` : le type de chaque pièce lisible, parmi `RC`, `CCAP`,
     `CCTP`, `DPGF`, `BPU`, `plan`, `autre`.
   - `choix` reste `null` : seul l'utilisateur choisit (étape 2).
   - Tu peux ajouter d'autres clés (date de remise relevée, par exemple) :
     elles sont conservées.
3. `remporte lots enregistrer` valide le tri ; corrige jusqu'à ce qu'il passe.

## 2. Annonce et choix des lots

`remporte lots rapport --ouvrir`, puis annonce en quelques lignes : acheteur,
objet, lots et avis, date limite de remise, visite, pièces illisibles. Propose
une date interne trois jours ouvrés avant la remise ; si le DCE ne donne pas
la date de remise, demande-la. Fais choisir les lots, même s'il n'y en a
qu'un, sans choisir à la place de l'utilisateur. Enregistre son choix :
`remporte lots choisir --lots "<lots>" --par "<nom>"`. La commande crée
`analyse/lot-<id>.md` et `analyse/lot-<id>.json` pour chaque lot retenu.

## 3. Analyse d'un lot retenu

Ordre de lecture :

1. **Le RC en entier** (`remporte lire rc`) : critères et sous-critères **avec
   leur pondération exacte**, contenu attendu du mémoire (points, pages,
   format, cadre imposé), pièces de candidature et d'offre, date et heure
   limites, plateforme, visite, date limite des questions, variantes, PSE.
2. **Le CRT** ou cadre de mémoire, s'il existe (`remporte cadre`).
3. **Le CCTP du lot** : jamais d'un bloc. `remporte lire cctp` rend son
   sommaire ; lis les pages utiles (`--page N`) ou cherche
   (`remporte chercher "<terme>"`). Relève les exigences qui appellent une
   réponse explicite (moyens, délais, méthodes imposées, livrables).
4. **Le CCAP** : pénalités, paiement, avance, retenue de garantie,
   assurances, révision des prix, durée et reconduction.
5. **AE, BPU, DPGF, DQE du lot** : leur forme, et leurs écarts avec le CCTP.
6. Les autres pièces du lot, puis les pièces communes utiles.

Remplis `analyse/lot-<id>.md`, dans l'ordre de ses rubriques : En bref,
Identité, Ce que l'acheteur attend vraiment, Critères et pondérations, Pièces
à remettre et formes imposées, Incohérences entre pièces, Pièces illisibles
ou absentes, Documents de référence et versions, Avis.

- Chaque ligne porte sa source : [RC art. 7.2], [CCTP §3.4], [CCAP art. 12].
- Les pondérations se recopient telles quelles. « Par ordre décroissant
  d'importance » sans pourcentage s'écrit ainsi.
- Une information absente du DCE s'écrit « non précisé dans le DCE ». Ne
  comble jamais un vide par une habitude du secteur.
- Chaque incohérence est numérotée `I-1`, `I-2`… : les deux prescriptions,
  puis l'hypothèse retenue.
- « Avis » : ce qui peut faire écarter l'offre avant d'être lue (pièce
  manquante, signature, format, limite de pages), les clauses dures du
  CCAP, et ce que la fiche entreprise ne couvre pas ou couvre mal.
- RC absent du DCE : dis-le en tête d'« En bref », demande-le à
  l'utilisateur, et prends en attendant les critères dans le CRT, l'avis de
  publicité ou le CCAP ; les pondérations restent `[à compléter : pondérations du RC]`.

Dans `analyse/lot-<id>.json`, la liste `questions_acheteur` : une question par
écart qui change le prix ou la recevabilité, et une seule liste par lot.

```json
{"questions_acheteur": [
  {"id": "I-1",
   "contexte": "Le CCTP art. 4.2 demande 40 prises au R+1, la DPGF ligne 3.1 en compte 32.",
   "question": "Pouvez-vous confirmer le nombre de prises attendu au R+1 : 40 selon le CCTP ou 32 selon la DPGF ?",
   "sources": ["CCTP art. 4.2", "DPGF ligne 3.1"],
   "impact_prix": "Huit prises de plus ou de moins sur le lot."}
]}
```

- `id` : le numéro de l'incohérence de l'analyse (`I-1`, `I-2`…), une fois.
- `contexte` : l'écart en une ligne ; `question` : phrase complète adressée à
  l'acheteur, prête à envoyer, terminée par « ? » ; `sources` : les passages
  du DCE ; `impact_prix` : ce que la réponse change au prix ou à la
  recevabilité.
- Ces textes partent chez l'acheteur : aucun nom de fichier, de dossier ni de
  commande. Les autres clés du fichier sont libres et conservées.

## 4. Présenter

`remporte lots rapport --ouvrir`, puis, pour chaque lot retenu : l'essentiel
et les questions à l'acheteur, chacune précédée de son contexte en une ligne,
avec la date limite des questions. Demande s'il manque quelque chose et
conviens des validations : go/no-go, plan et fin, ou chaque étape.
Quand `remporte etat` donne tous les lots retenus prêts, passe au go/no-go.
