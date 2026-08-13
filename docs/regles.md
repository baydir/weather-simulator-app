# Règles — ce qu'on dérive des données

Les seules grandeurs que l'application calcule elle-même : **la classe de ciel**
et **la correction de nébulosité**. Tout le reste est affiché tel que servi.

D'où viennent les données → [`donnees.md`](donnees.md) ; ce qu'elles valent →
[`science.md`](science.md). Chiffres établis par `scripts/sky_thresholds/`.

---

## Pourquoi l'aspect du ciel doit être reconstruit

Le `weather_code` d'Open-Meteo n'est pas un produit de réanalyse : c'est une
variable dérivée, calculée heure par heure à partir de la nébulosité, des
précipitations et de la neige, puis agrégée **par maximum** — la journée prend
le code de son pire moment.

Deux obstacles interdisent de le réutiliser. Il est nul côté Climate. Et
l'API Climate ne livrant que des agrégats journaliers, la règle d'Open-Meteo
appliquée à ceux-ci **ne reproduit son propre résultat que dans 15 % des cas** :
deux millimètres tombés en deux heures et les mêmes étalés sur vingt-quatre ne
donnent pas le même code, et l'information qui les sépare n'existe pas côté
futur.

Réduite à trois familles — sec, pluie, neige — la concordance remonte à 90,7 %.
C'est ce signal grossier, et lui seul, qui survit au passage au pas journalier.

---

## La classe de ciel

Cinq classes, **le même arbre de décision sur les quatre segments**, à partir
des seuls agrégats journaliers :

| | Condition | Classe |
|---|---|---|
| 1 | précipitations ≥ 1 mm **et** température moyenne < 1,5 °C | **Neige** |
| 2 | sinon, précipitations ≥ 1 mm | **Pluie** |
| 3 | sinon, nébulosité ≥ 70 % | **Couvert** |
| 4 | sinon, nébulosité ≥ 30 % | **Nuageux** |
| 5 | sinon | **Dégagé** |

Les deux premières règles partagent la même porte à 1 mm : parmi les jours
humides, la température décide de la phase.

**Le cumul de neige n'entre pas dans la règle**, alors qu'il en était la base
initiale. Le modèle climatique le sert par plages manquantes, et la lecture
« pas de neige en été » ne survit pas au passage de l'équateur. Le passé, lui,
le sert fidèlement — mais s'en servir d'un seul côté déplacerait la couture au
lieu de la supprimer.

**Aucune gradation d'intensité n'est proposée** : les cumuls journaliers ne
portent pas l'information nécessaire. Une bruine et un orage de quarante
millimètres reçoivent la même classe. Appauvrissement assumé.

### Le seuil de neige, 1,5 °C

Calé sur 35 hivers à Strasbourg et Briançon, **contre la profondeur réellement
tombée** — et non contre le `weather_code`, qui bascule sur une seule heure de
neige, surestime la neige de 16 points à Strasbourg et sature à Briançon, où
999 jours humides sur 1000 portent un code de neige.

Concordance obtenue : environ 90 % en plaine, 82 % à 1300 m. **La règle
sous-appelle la neige en montagne par construction** — au-dessus de 1300 m elle
tient au sol même les jours dont la moyenne dépasse 2 °C, parce qu'elle tombe la
nuit ou plus haut que la station. Aucun seuil unique ne convient aux deux sites.

**Provisoire** : deux sites et une seule saison sont une base mince.

---

## Les seuils de nébulosité, 30 % et 70 %

Confirmés à l'étape 3. L'établir a d'abord consisté à **écarter deux étalons qui
paraissaient évidents** :

- **`sunshine_duration` est inexploitable** — 3 311 heures de soleil par an à
  Brest pour environ 1 700 réelles, 3 103 à Strasbourg pour 1 690. L'erreur suit
  la nébulosité du site, ce qui trahit le mécanisme : le seuil de 120 W/m² est
  appliqué à des moyennes horaires, et l'heure compte entière dès que sa moyenne
  le franchit, là où un héliographe compte les minutes.
- **Le `weather_code` ne vaut pas mieux** — une seule heure à 80 % de nébulosité
  couvre la journée entière : il déclare Marseille couverte un jour sec sur
  deux. Et il est **circulaire**, étant une fonction déterministe de la
  nébulosité, la variable même dont on cherche les seuils.

**Ce qui tranche est la lumière qui atteint réellement le sol.**
`shortwave_radiation_sum` est un champ primaire d'ERA5, ses cumuls annuels
concordent avec les valeurs publiées, et les trois sources le servent. Rapporté
à une estimation de ciel clair — géométrie FAO-56 plus un terme d'altitude, donc
calculable identiquement de 1950 à 2050 — il donne la part de lumière
disponible qu'une journée a reçue, comparable de Brest à Bamako.

Sur les jours secs, les trois classes reçoivent :

| Site | Dégagé | Nuageux | Couvert |
|---|---|---|---|
| Brest | 17 % → 93 % | 44 % → 80 % | 39 % → 61 % |
| Marseille | 50 % → 92 % | 35 % → 84 % | 15 % → 67 % |
| Strasbourg | 26 % → 89 % | 45 % → 74 % | 29 % → 54 % |
| Pontarlier | 29 % → 88 % | 43 % → 78 % | 27 % → 60 % |
| Reykjavik | 14 % → 92 % | 41 % → 82 % | 45 % → 59 % |

*(part des jours secs → lumière médiane reçue, en % du ciel clair)*

**Environ 90 %, 80 % et 60 %.** Trois paliers nets, dans le même ordre aux dix
sites testés. Aucun autre jeu de seuils ne fait mieux : monter la barre du
couvert à 80 ou 85 % abaisse la médiane mais élargit la dispersion d'autant.

Il faut dire ce que cette mesure ne fait pas. **Où finit « nuageux » et où
commence « couvert » reste une convention de langage sur un continuum.** La
mesure ne place pas la frontière ; elle dit ce qui tombe de part et d'autre.

---

## Ce que la moyenne journalière ne peut pas dire

À nébulosité égale, la lumière reçue s'étale considérablement. À Strasbourg,
deux journées portant 90 % de nébulosité moyenne reçoivent, du premier au
neuvième décile, de 29 % à 79 % de la lumière d'un ciel clair — **49 points
d'écart**. Ce sont deux journées opposées sous le même chiffre : celle qui fut
grise de bout en bout, et celle dont la matinée bouchée a cédé à un après-midi
radieux.

**Et l'ambiguïté croît avec la nébulosité** : 20 points d'étendue vers 30 %,
49 points vers 90 %. À 30 % de nuages il n'y a pas grand-chose à redistribuer
dans la journée ; à 90 %, il y a tout.

Aucun seuil n'y remédie, et aucun modèle non plus, l'information infra-journalière
n'existant pas côté futur.

**Il en découle que le pictogramme est l'élément le moins sûr de la carte.** Les
températures et les millimètres décrivent cette journée-là ; l'icône décrit une
espèce de journées.

Deux conséquences pratiques. **Près des pôles en hiver**, le ciel clair tend vers
zéro et le rapport perd son sens — 14,3 % des jours à Reykjavik ; la classe y
repose sur la seule nébulosité. Et **trois classes de ciel sec sont peut-être une
de trop** → [`idees.md`](idees.md).

---

## La correction de nébulosité

**C'est la seule correction appliquée.** Elle est nécessaire parce que la
nébulosité détermine trois des cinq classes et que le modèle la sous-estime de 5
à 11 points selon le site : appliquer les seuils bruts produirait un futur
artificiellement ensoleillé.

Calibrée sur la période de recouvrement, mois par mois et par lieu, par
**transposition de quantiles préservant la tendance** — *quantile delta
mapping*, Cannon, Sobie & Murdock (2015). Une journée future est située dans la
distribution *future* du modèle ; on mesure le déplacement que le modèle donne
lui-même à ce quantile entre son passé et son futur ; ce déplacement est reporté
sur la distribution de référence. Le biais s'en va, l'évolution reste.

**Pourquoi quantile par quantile plutôt qu'un décalage mensuel.** Le biais n'est
pas constant : mesuré décile par décile, il s'étend sur 4 à 20 points selon le
site, maximal sur les journées claires et s'annulant sur les couvertes — le
modèle ne pouvant dépasser 100 %, il converge par le haut et fabrique trop de
ciels dégagés par le bas. Un décalage unique laisserait les classes fausses
précisément là où se joue la frontière dégagé/nuageux.

**« Transposition naïve » recouvre deux procédés distincts.** À travers la
distribution *passée* du modèle, la tendance n'est pas supprimée mais
redimensionnée en silence par la pente locale — cinq points ressortent à 4,4. À
travers la distribution *future*, elle **disparaît entièrement**, la sortie
étant forcée de coïncider avec la référence. C'est ce second procédé qui est
écarté.

**La tendance à préserver est faible, et la méthode est retenue quand même.**
Entre 1985-2014 et 2021-2050, la nébulosité du modèle bouge de −0,4 à
−1,8 point, et le rayonnement de −1,0 à +1,2 % — deux variables cohérentes entre
elles, ce qui écarte l'artefact. Le biais à corriger vaut 8 à 11 points : la
correction le domine d'un facteur cinq à dix. Le choix ne tient donc pas à ce
que la méthode gagne ici, mais à ce qu'elle évite ailleurs : la mesure porte sur
cinq sites, quatre en France, et **la grille a vocation à couvrir le monde**, où
les zones subtropicales s'assèchent nettement sous RCP8.5. Une méthode retenue
au motif que la tendance est négligeable en France déformerait sans avertissement
un signal réel sous les tropiques.

La correction est légitime parce que **le biais est stable dans le temps**, et
l'on sait pourquoi : les coefficients d'Open-Meteo sont figés une fois pour
toutes → [`science.md`](science.md).

### Deux constats dont l'étape 4 doit partir

- **Une part du biais est fabriquée par Open-Meteo**, non héritée du modèle : à
  Pontarlier, le brut est à +0,5 point d'ERA5 et le corrigé à −8,8 ; à
  Singapour, −1,7 contre −27,2. Se rabattre sur le modèle brut n'est pourtant
  pas la solution — la correction *est* la descente d'échelle, et la désactiver
  rend le modèle aveugle au relief.
- **Le rayonnement du modèle, lui, n'est pas biaisé** : −0 à +1 % contre ERA5 à
  Brest, Marseille et Pontarlier, quand la nébulosité y est fausse de 9 à
  11 points. Il fournit donc un étalon pour caler la correction — ajuster la
  nébulosité de sorte que sa relation nuage-lumière rejoigne celle de la
  référence, plutôt que de transposer des quantiles à l'aveugle. Mesuré sur
  trois sites seulement, à élargir avant d'engager quoi que ce soit.

**Aucune autre correction n'est appliquée.** Ni les extrêmes de température ni la
durée des sécheresses ne sont retouchés, la mesure n'y ayant établi aucun
déficit.

---

## Où ces règles s'insèrent

Après l'assemblage des quatre segments décrit dans [`donnees.md`](donnees.md) :

1. Correction de nébulosité **sur le seul segment futur**. La prévision n'y a
   pas droit et ne doit pas y avoir droit : IFS est une observation portée en
   avant, pas un modèle climatique biaisé. Lui appliquer la correction
   inventerait un biais qu'elle n'a pas.
2. Classe de ciel appliquée **aux quatre segments, par la même fonction**.

Cette fonction unique, appelée quatre fois, n'est pas négociable : toute
duplication de cette logique rouvrirait la divergence que tout le dispositif
vise à interdire. Le nombre d'appels est passé de trois à quatre le jour où la
prévision est devenue un segment, sans qu'il y ait rien à modifier — c'est la
preuve de la règle plutôt qu'une exception à elle.

---

## Validation

- **Absence de marche aux deux coutures** : comparaison des niveaux et des
  variances de part et d'autre de chacune. `scripts/inspect_seam.py` les repère
  sans les supposer, en suivant le changement de source d'un jour au suivant.
- **Continuité** : ni trou ni doublon aux raccords, et un jour porte les mêmes
  champs renseignés quelle que soit la source qui l'a servi.
- **Vraisemblance des classes de ciel** — non contre leur seule fréquence, mais
  contre la lumière reçue : les trois classes sèches doivent rester séparées
  d'environ 90 %, 80 % et 60 % du rayonnement d'un ciel clair, comme sur la
  période historique.
- **Détection explicite des valeurs nulles** : le statut HTTP ne suffit pas.
