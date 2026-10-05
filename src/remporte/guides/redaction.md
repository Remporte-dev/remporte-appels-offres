# Étape « redaction » — écrire chaque section

Une section à la fois, dans l'ordre du plan. Pour chacune :

1. **Relis ce qui est noté** : la ligne du tableau de correspondance de
   `04-plan.md` et le passage du RC ou du CRT correspondant.
2. **Rassemble la matière** :
   - les exigences du CCTP concernées : `remporte chercher "<termes>"` ;
   - ce que l'entreprise sait faire et a déjà fait :
     `remporte base chercher "<termes>"` (références, moyens, méthodes,
     certifications, CV, anciens mémoires).
3. **Écris** dans `sections/NN-titre.md`, en commençant par `# NN — Titre`.
   Tes notes de travail (critère servi, sources lues) vont en citation `> …` :
   elles restent dans le fichier mais ne partent pas dans le mémoire exporté.

## Ce qui fait une bonne section

- **Elle répond à la question posée, avec les mots de l'acheteur.** La
  première phrase dit ce que l'entreprise propose pour ce point précis.
- **Elle est propre à ce marché.** Nomme le site, l'acheteur, le périmètre,
  les volumes, les contraintes du CCTP. Une phrase qui pourrait figurer dans
  n'importe quel mémoire ne rapporte aucun point.
- **Chaque engagement est vérifiable** : qui, quoi, quand, combien, avec quel
  moyen, contrôlé comment. « Un chef de projet dédié, joignable de 8 h à 18 h,
  qui intervient sous 4 h » plutôt que « une équipe réactive ».
- **Chaque affirmation sur l'entreprise a une preuve** issue de la base :
  référence comparable, chiffre, certification, CV. Sans preuve dans la base,
  écris `[à compléter : référence d'un marché similaire, avec montant et
  contact]` au lieu d'inventer. Une invention découverte coûte le marché.
- **Elle couvre toutes les exigences du CCTP qui la concernent**, en les
  citant si besoin [CCTP §4.2].
- **Elle répond à chaque exigence numérotée du CRT qu'elle porte**, sous un
  intertitre qui reprend son identifiant : `### PP 013 — Dispositif
  d'initialisation`. C'est ce que contrôle `remporte cadre --couverture`.
- **Une preuve ne s'étire pas** : écris ce que dit la base, pas davantage. Si
  la base dit « 18 sprints », n'ajoute pas « sans aucun changement d'équipe ».
- **Elle se lit vite** : intertitres, listes, un tableau quand on compare ou
  qu'on planifie. Pas de formules creuses (« fort de notre expérience »,
  « au cœur de nos valeurs », « solution innovante »).
- **Elle respecte le volume visé** du plan. Une exigence notée mérite au
  moins un paragraphe concret ; trois lignes ne rapportent pas de points.

Quand une section est écrite, coche-la dans `04-plan.md` (`- [x]`) et passe à
la suivante. À la fin : `remporte guide relecture`.
