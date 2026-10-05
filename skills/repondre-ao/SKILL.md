---
name: repondre-ao
description: Répondre à un appel d'offres public (DCE, RC, CCTP, mémoire technique) avec le CLI remporte. À utiliser dès que l'utilisateur veut analyser un DCE, décider s'il répond, bâtir le plan ou rédiger le mémoire technique d'un marché public.
---

# Répondre à un appel d'offres

Le CLI `remporte` lit le DCE et porte la méthode. Installation, si la
commande est absente : `uv tool install git+https://github.com/Remporte-dev/remporte`.

1. Si aucun dossier de réponse n'existe encore :
   `remporte init <dossier ou zip du DCE>`.
2. Dans le dossier de réponse, lance `remporte etat`, puis
   `remporte guide <étape>` pour l'étape indiquée, et suis-le.
3. Recommence jusqu'à l'export.

N'invente jamais une information sur l'entreprise : cherche-la avec
`remporte base chercher`, demande-la à l'utilisateur, ou laisse
`[à compléter : …]`.
