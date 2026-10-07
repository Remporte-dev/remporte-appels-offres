---
name: repondre-ao
description: Répondre à un appel d'offres public (DCE, RC, CCTP, mémoire technique, DC1, DC2) avec le CLI remporte. À utiliser dès que l'utilisateur veut analyser un DCE, décider s'il répond, bâtir le plan ou rédiger le mémoire technique d'un marché public.
---

# Répondre à un appel d'offres

Ce plugin fait tourner l'outil `remporte` sur l'ordinateur de l'utilisateur. Si tu ne peux pas lancer de commande (par exemple dans une conversation sur claude.ai), ne tente rien d'autre et réponds seulement :
« Ce plugin fonctionne dans Claude Code ou dans Cowork, sur votre ordinateur : il a besoin de lire vos fichiers et de lancer l'outil Remporte. Ouvrez-le là-bas pour continuer. »

- Première utilisation sur ce poste (commande `remporte` absente, ou pas de
  fiche entreprise : `remporte fiche` échoue) : propose `/remporte:init`.
- Nouveau DCE : propose `/remporte:nouvel-ao`, ou suis directement son
  parcours.
- Dossier de réponse déjà commencé : `remporte etat`, puis
  `remporte guide <étape>`.

N'invente jamais une information sur l'entreprise : `remporte fiche`,
`remporte base chercher`, ou `[à compléter : …]`.
