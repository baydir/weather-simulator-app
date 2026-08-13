# Idées — envisagé, non retenu

Ce qui a été examiné puis écarté, et ce qui reste ouvert. **Rien ici n'est
décidé.** Consigné pour que les constats de mesure ne se perdent pas et qu'on ne
refasse pas deux fois le même raisonnement.

Tout ce qui touche aux données ou à la méthode relève de la validation
scientifique → [`CLAUDE.md`](../CLAUDE.md).

---

## Points restés ouverts

**Trois classes de ciel sec sont peut-être une de trop.** La nébulosité moyenne
journalière est une variable ambiguë — deux journées à 90 % peuvent recevoir de
29 % à 79 % de la lumière d'un ciel clair. Deux classes, ensoleillé et nuageux,
seraient plus défendables, au prix de la finesse d'affichage.
→ [`regles.md`](regles.md)

**Les rafales.** `wind_gusts_10m_max` existe comme variable propre et **les trois
segments la servent**. Elle n'est pas retenue : une rafale est par nature un
phénomène sous-maille, hors de portée d'un modèle à 20 km. La servir donnerait
un chiffre juste de forme et faiblement fondé. Son adoption relèverait de la
validation scientifique.

---

## Classe de ciel apprise sur des observations réelles

**L'étape 3 a montré qu'aucun étalon interne à Open-Meteo ne convient** :
`sunshine_duration` est faux d'un facteur 1,3 à 2,0, et le `weather_code` est un
maximum horaire circulaire. Mais de vraies observations existent en dehors : les
relevés synoptiques de surface donnent la nébulosité totale **en octas, mesurée
plusieurs fois par jour** — Météo-France en open data pour la France, la NOAA
mondialement. C'est une observation, non une dérivation.

Un modèle ajusté sur cette cible, prenant en entrée les agrégats journaliers
disponibles sur les quatre segments, ferait mieux qu'un seuil unique. **La mesure
le montre déjà** : ajouter la seule **amplitude thermique** — un grand écart
entre minimale et maximale signe un ciel dégagé, le sol chauffant le jour et
rayonnant la nuit sans couverture — fait passer la variance expliquée de 0,50 à
0,64 à Strasbourg, de 0,30 à 0,52 à Bamako. Cette variable est servie par les
trois sources.

**Le plafond reste le même** : les entrées étant journalières côté futur, aucun
apprentissage ne récupère la structure interne d'une journée. Le gain porte sur
la discrimination *entre* journées de même nébulosité, jamais *à l'intérieur*
d'une journée.

**C'est un travail en soi**, de l'ampleur de l'étape 2 : seconde source avec sa
licence et son contrôle qualité, appariement station-maille — une station est un
point, ERA5 une maille de 25 km —, définition conventionnelle de « l'allure
dominante » à partir de relevés horaires, et un modèle ajusté devenant un
artefact embarqué, moins lisible qu'un arbre de décision sur des pages qui
doivent expliquer la méthode.

---

## Autres pistes

- **Enveloppe d'incertitude** fondée sur l'écart entre les cinq modèles
  éligibles, sans renoncer à l'affichage d'une trajectoire unique.
- **Comparaison aux projections régionalisées DRIAS** de Météo-France, mieux
  évaluées sur la France, et à la trajectoire de référence TRACC.
- **Ouverture à d'autres scénarios d'émissions**, ce qui suppose de changer de
  source : l'API Climate n'en expose qu'un.

---

## La comparaison à l'ancien climat

**Non retenu pour la première version.** Consigné parce que le dispositif s'y
prête déjà et que plusieurs constats de mesure risqueraient sinon d'être perdus.

L'application affiche « 14 juillet 2046 : 21 °C / 39 °C ». C'est plus parlant
qu'une anomalie globale, mais **39 °C ne dit quelque chose qu'à qui sait ce
qu'était un 14 juillet auparavant** — or c'est précisément ce que le lecteur
vient chercher. La pédagogie est dans l'écart, pas dans la valeur.

**Le principe envisagé.** Dès que la plage comporte un segment futur, un bouton
affiche sous la bande initiale les **mêmes dates du calendrier** d'une année
ancienne, dans le même format. Déclenchement : la règle qui gouverne déjà le
refus hors grille, pour n'en avoir qu'une à retenir. **Année de référence codée
en dur, par grande région** — une table figée lue en mémoire, aucun calcul à la
requête. Le découpage régional n'est pas une commodité : **une année ne peut pas
être ordinaire partout**, 1980 ayant été le plus froid des trente étés en France
et le vingt-deuxième sur trente à Reykjavik.

**Trois constats conditionnent le choix de l'année**
(`scripts/model_selection/reference_year.py`, cinq sites français, écarts en
écarts-types de la période) :

- **Une année choisie d'intuition se trompe lourdement.** 1980 est à −2,00 en
  été et −2,14 sur l'année : le plus froid des trente à Marseille, Strasbourg,
  Pontarlier et Chamonix. La comparaison y ajouterait un écart artificiel
  d'environ 2 °C, soit l'ordre de grandeur du réchauffement qu'elle prétend
  montrer. Symétriquement, 2003 est à +3,25 en été.
- **L'année doit être ordinaire sur plusieurs saisons à la fois.** Une moyenne
  annuelle centrée peut recouvrir un été chaud compensé par un hiver doux. Sur
  1979-1994, la plus ordinaire est **1991** (+0,49 été, −0,46 hiver, +0,03
  année) ; sur 1979-2008, **2004** (+0,08 / −0,06 / −0,03).
- **Une référence tardive dépense le signal avant de commencer.** Entre 1979-1988
  et 1999-2008, les sites français se réchauffent de **+0,92 °C** : une année
  prise dans les années 2000 escamote près d'un degré de ce qu'il s'agit de
  montrer.

À privilégier : **la plus ordinaire de la période la plus ancienne
exploitable** — ERA5 avant 1979 étant l'extension arrière préliminaire.

**Deux exigences d'honnêteté**, faute de quoi la fonctionnalité induit en
erreur :

- Le libellé doit dire que l'année a été **choisie pour être ordinaire** —
  « 1991, une année sans particularité » et non « 1991 ». Le tirage futur, lui,
  n'est pas sélectionné : il peut porter une canicule. Comparer un tirage libre à
  un tirage choisi pour sa sagesse laisserait croire que le passé n'avait pas
  d'extrêmes, alors que c'est la sélection qui les a écartés.
- La sélection portant sur la seule température, **la pluie de l'année retenue
  est quelconque**. Mieux vaut l'assumer que le découvrir.

Enfin, deux bandes de quatre-vingt-dix cartes ne se comparent pas à l'œil : une
ligne de synthèse au-dessus — journées à 30 °C ou plus de part et d'autre —
porte ce que les bandes ne peuvent pas porter.
