# Étape « export » : produire les fichiers à remettre

Le parcours recommandé est : go/no-go, chiffrage, décision du mémoire, puis
plan, rédaction et relecture si le mémoire est retenu, et export. Si
l'utilisateur a décidé de ne pas produire de mémoire, ces trois étapes sont
sautées : produis les autres pièces de l'offre.

Tout ce qui part chez l'acheteur se range dans `reponse/`, et rien d'autre.
Quand le marché est alloti, chaque lot retenu a son dossier, même s'il n'y en a
qu'un : `remporte livraison dossier --lot <id>` le crée et donne son chemin
(`reponse/Lot <id> - <intitulé>/`). Toutes les pièces du lot s'y rangent, DC1
et DC2 compris.

1. **Les livrables bureautiques, c'est toi qui les produis**, avec tes propres
   outils (traitement de texte, présentation, tableur), dans le format que
   demandent l'acheteur et l'utilisateur : document Word, présentation
   PowerPoint, PDF…
   - **Demande d'abord à l'utilisateur s'il a un modèle** : modèle de document
     ou de présentation de l'entreprise, ancien mémoire ou ancienne
     présentation à imiter. S'il en a un, pars de ce fichier et reprends sa
     mise en page, ses styles et son logo ; range-le dans `references-client/`.
   - Si l'acheteur impose un cadre de réponse (Word ou Excel), la réponse va
     **dans son fichier**, qui garde sa trame et rien d'autre
     (`remporte guide excel`).
   - Le mémoire reprend les sections de `sections/` dans l'ordre de
     `04-plan.md`, chaque section sous son titre du plan. Retire les notes de
     travail (lignes en citation `> …`) et le titre `# NN — …` qui ouvre
     chaque fichier : le titre du plan le remplace.
   - Respecte les limites de `remporte formats` (pages, police, interligne).
     Si la limite de pages est dépassée, réduis le mémoire avant la remise.
   - Nomme chaque fichier comme l'acheteur le demande au RC ; à défaut, par la
     pièce et le nom de l'entreprise (`Memoire-technique-<entreprise>.docx`).
   - Une présentation (soutenance, synthèse pour la direction) suit
     `remporte guide soutenance`.
2. **À la reprise, pars du fichier existant.** Ouvre-le et repère les
   retouches de l'utilisateur. Applique les corrections dans ce fichier, avec
   le suivi des modifications pour un Word. Si une correction touche une autre
   pièce ou une section, reporte-la aussi et indique les fichiers mis à jour.
   Demande son accord avant de régénérer un fichier.
3. Montre chaque fichier terminé à l'utilisateur (règle de `AGENTS.md`), puis
   donne la liste des `[à compléter : …]` restants.
4. **Enchaîne sur les autres pièces de l'offre**, sans attendre qu'il le
   demande. Reprends « Pièces à remettre et formes imposées » de
   `analyse/lot-<id>.md` pour chaque lot retenu et présente chaque pièce avec
   son état : faite (dans `reponse/`), à produire par toi, à fournir par lui.
   Pose d'abord en un seul message les questions communes (modèles, prix,
   signataire, sous-traitants). Le guide de chaque pièce :
   - bordereau de prix (BPU, DPGF, DQE) : `remporte guide chiffrage` ;
   - fichiers imposés et cadre de réponse : `remporte guide excel` ;
   - DC1, DC2, DC4 : `remporte guide candidature` ;
   - acte d'engagement : à remplir dans le fichier de l'acheteur, comme un
     fichier imposé ;
   - soutenance s'il y en a une : `remporte guide soutenance`.
   Celles que tu ne peux pas produire (attestations fiscales et sociales,
   K-bis, assurance, signature électronique) vont dans la liste à réunir par
   l'utilisateur.
5. **Le récapitulatif final** : les fichiers de `reponse/`, chacun en lien
   cliquable ; ce qu'il doit encore fournir, signer ou remplir ; la date
   limite de remise, rappelée. Pour la direction ou l'équipe,
   `remporte exporter` produit dans `export/` l'analyse et la feuille de route
   en HTML, à garder sous les yeux jusqu'au dépôt.
