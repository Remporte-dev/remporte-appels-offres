# Quel livrable, quelle méthode

Le parcours recommandé est : analyse des lots retenus, go/no-go, chiffrage,
décision du mémoire, puis plan, rédaction et relecture si l'utilisateur retient
le mémoire, puis les autres pièces et l'export. Le mémoire n'est pas
obligatoire : une fois le prix arrêté, rappelle si le RC l'exige et son poids
dans la notation, puis demande à l'utilisateur s'il veut le produire.

Une réponse à un appel d'offres ne se limite pas au mémoire technique. Avant de
produire quoi que ce soit, identifie chaque livrable attendu avec
`remporte formats` et « Pièces à remettre et formes imposées » de
`analyse/lot-<id>.md` pour chaque lot retenu, puis demande à l'utilisateur ce
que le DCE ne dit pas (soutenance, présentation pour la direction, visuels
qu'il a l'habitude de joindre).

## L'arbre de décision

1. **L'acheteur impose son fichier ?** On répond dans son fichier : sa trame
   et rien d'autre.
   - Cadre de réponse technique (CRT) en Word : `remporte guide cadre-reponse`.
   - Questionnaire ou annexe technique en Excel ou en Word :
     `remporte guide excel`.
   - Bordereau de prix (BPU, DPGF, DQE) : `remporte guide chiffrage`.
   - Formulaires DC1, DC2, DC4 : `remporte guide candidature`.
2. **Mémoire technique libre retenu par l'utilisateur** (pas de cadre imposé) :
   `remporte guide plan`, puis `redaction`, `relecture` et `export`. Le
   mémoire se produit en Word, ou dans le format que demande le RC.
3. **Contenu plus riche qu'un texte** (planning, organigramme, synoptique,
   méthodologie en schéma), à insérer dans le mémoire ou à joindre :
   `remporte guide visuels`.
4. **Soutenance orale** : `remporte guide soutenance`.
5. **Lecture interne** (direction, équipe) : `remporte exporter` produit
   l'analyse et la feuille de route en HTML, à lire sans suivre la
   conversation.

## Pour chaque livrable

- **Demande d'abord à l'utilisateur s'il a un modèle** : modèle de document
  ou de présentation de l'entreprise, ancien livrable du même type. S'il en a
  un, pars de ce fichier et reprends sa mise en page ; range-le dans
  `references-client/`.
- **Produis le fichier avec tes propres outils** (traitement de texte,
  présentation, tableur), dans le format attendu, dans `reponse/` : c'est le
  dossier de ce qui part chez l'acheteur, et rien d'autre. Si tu n'as aucun
  outil capable d'écrire ce format sans l'abîmer, dis-le à l'utilisateur et
  livre le contenu en markdown, prêt à reporter.
- **Une seule source de vérité** : `sections/`, `remporte fiche` et
  `remporte base chercher`. Un chiffre, un nom ou un engagement est identique
  dans tous les livrables ; la relecture le vérifie.
- **Un livrable terminé s'ouvre aussitôt** devant l'utilisateur : lien
  cliquable vers son chemin absolu, seul sur sa ligne, et ouverture dans son
  logiciel quand la session tourne sur son ordinateur (règle détaillée dans
  `AGENTS.md` du dossier).
- **Une demande de changement se fait dans le fichier existant** : relis
  d'abord ce que l'utilisateur y a modifié, corrige sans refaire le fichier,
  et demande son accord avant de le régénérer.
