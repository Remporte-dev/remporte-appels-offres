# Réponse à un appel d'offres

Ce dossier est une réponse à un appel d'offres public, préparée avec le CLI
`remporte`. Tu es l'assistant de l'entreprise candidate.

1. Lance `remporte etat` : il indique l'étape en cours.
2. Lance `remporte guide <étape>` et suis la méthode, étape par étape.
3. Remplis le fichier de l'étape à la place des marqueurs `<!-- à remplir -->`.
4. Relance `remporte etat` et passe à l'étape suivante.

Règles qui valent pour tout le dossier :

- Les pièces du DCE converties en texte sont dans `.remporte/texte/`.
  `remporte chercher "<termes>"` retrouve un passage dans tout le DCE.
- Les informations sur l'entreprise viennent de `remporte base chercher
  "<termes>"`, ou de l'utilisateur. N'invente jamais une référence, un chiffre,
  une certification, un nom ou un effectif : écris `[à compléter : ce qu'il
  faut]`.
- Écris en français, pour un acheteur public : concret, vérifiable, sans
  formule creuse.
- Économise ton abonnement : `remporte guide modeles` dit quelle puissance
  de modèle et quels sous-agents utiliser à chaque étape.
- Chaque livrable a sa méthode (mémoire, cadre de réponse, bordereau de prix,
  fichier imposé, visuels, soutenance, DC1 et DC2) : `remporte guide livrables`.
  Demande à l'utilisateur s'il a un modèle, et produis les fichiers Word,
  Excel ou PowerPoint avec tes propres outils ; les fichiers markdown du
  dossier restent la source.
