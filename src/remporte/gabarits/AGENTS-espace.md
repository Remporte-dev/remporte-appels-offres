# Espace de réponse aux appels d'offres

Ce dossier est l'espace de travail de l'entreprise pour répondre aux marchés
publics, avec le CLI `remporte`.

- `ressources/` : les documents de l'entreprise (références, CV,
  certifications, anciens mémoires) et `fiche-entreprise.md`, que tout agent
  lit avant de travailler (`remporte fiche`). Après un ajout de documents :
  `remporte base indexer`.
- `DCEs/` : un dossier par appel d'offres. `remporte init <DCE.zip>` le crée ;
  dans ce dossier, `remporte etat` dit où en est la réponse et
  `remporte guide <étape>` donne la méthode.

Avec le plugin Claude Code : `/remporte:init` pour la mise en route,
`/remporte:nouvel-ao` pour chaque appel d'offres.

N'invente jamais une information sur l'entreprise : fiche, base, ou
`[à compléter : …]`.
