# Journal — ce qui a été fait

Ce document tient l'avancement et, pour chaque étape, **ce qu'elle a corrigé de
ce que la conception avait supposé**. C'est le seul endroit où l'état du projet
se met à jour.

---

## Où on en est

Les étapes 0 à 3 sont faites, la 4 est engagée. **L'API et l'interface ne sont
pas commencées.**

Le déséquilibre est net et vaut d'être dit : quatre étapes de mesure et de
caractérisation des données, zéro ligne d'application. Les étapes 5 et 6
n'attendent pourtant que d'être écrites — la table provisoire de l'étape 4
existe exactement pour ça.

| | Étape | Dépend de | État |
|---|---|---|---|
| 0 | Nettoyage du prototype, packaging, `.gitignore` | — | **fait** |
| 1 | Récupération et série homogène, sans classe de ciel | 0 | **fait** |
| 2 | Confirmation du modèle parmi les cinq éligibles | 1 | **fait** |
| 3 | Calage des seuils de nébulosité et classe de ciel | 1 | **fait** |
| 4 | Grille de calibration France et correction de nébulosité | 2 | *en cours, 23 nœuds sur 594* |
| 5 | API, validation des entrées et bloc de transformation | 3, 4 | à faire |
| 6 | Interface : accueil, résultats, bande journalière | 5 | à faire |
| 7 | Élargissement mondial de la grille | 4 | à faire |

L'ordre est imposé par les dépendances, non par le contenu : celui-ci se décide
au moment d'aborder l'étape, à la lumière de ce que la précédente a révélé. La
confirmation du modèle venait en deuxième pour deux raisons — l'étape 1
produisait l'outil qui permettait de la mener, et changer de modèle après avoir
généré la grille aurait imposé de la refaire entièrement.

---

## Étape 0 — Nettoyage

Suppression du prototype Flask/JavaScript qui occupait `src/meteo_app/` et
`notebooks/`. Il contredisait la conception sur tous les points structurants :
modèle climatique dépourvu de nébulosité, endpoint d'archive par défaut, logique
de découpage dupliquée entre JavaScript et Python, géocodage par Nominatim. Il
reste récupérable par l'historique Git.

Mise en place du paquet `weather_simulator`, du packaging et des tests hors
réseau.

---

## Étape 1 — Série homogène

Le cœur du projet : `sources/` récupère et assemble la série de 1950 à 2050.

**Ce qu'elle a corrigé.** La conception prévoyait deux segments ; il y en a
**trois**. Les réanalyses accusent 5 à 6 jours de retard, et sans un segment
ECMWF IFS pour les combler, toute requête touchant aujourd'hui se terminerait
par un trou d'une semaine.

Les pièges de l'API y ont été identifiés et traités : nuls silencieux sous
HTTP 200, bloc horaire accepté puis non renvoyé côté Climate, noms de retour
variables selon le nombre de modèles demandés, `timezone=auto` obligatoire des
deux côtés d'une couture.

→ [`donnees.md`](donnees.md)

---

## Étape 2 — Confirmation du modèle

Dix sites, 1979-2014, quinze mesures. `MRI_AGCM3_2_S` retenu.

**Ce qu'elle a corrigé.** Les deux critères annoncés — biais et RMSE sur les
températures extrêmes — ont dû être abandonnés **tous les deux** : le biais est
fixé d'avance par la correction d'Open-Meteo, et les modèles ne rejouent pas les
mêmes journées que la réanalyse. Restait la comparaison de populations de
journées, seule chose qu'une correction linéaire mensuelle laisse intacte.

Le modèle n'est pas retenu pour sa moyenne — les quatre autres sont
indiscernables entre eux, au niveau du hasard — mais pour **l'absence de site où
il s'effondre**.

Deux découvertes incidentes : `FGOALS_f3_H` et `HiRAM_SIT_HR` ne servent jamais
`wind_speed_10m_max`, ce que l'audit de couverture initial ne pouvait pas voir ;
et aucun des cinq ne sert la neige complètement.

→ [`science.md`](science.md), `scripts/model_selection/`

---

## Étape 3 — Seuils de la classe de ciel

Les seuils de 30 % et 70 % sont confirmés.

**Ce qu'elle a corrigé.** Deux étalons qui paraissaient évidents se sont révélés
faux. `sunshine_duration` donne 3 311 heures de soleil par an à Brest pour
environ 1 700 réelles — un facteur 1,3 à 2,0. Le `weather_code` est le maximum
des 24 codes horaires, donc bascule sur une seule heure, et il est de surcroît
circulaire : c'est une fonction de la nébulosité, la variable même dont on
cherchait les seuils.

Ce qui tranche est le rayonnement reçu au sol. Trois paliers nets, dans le même
ordre aux dix sites : environ **90 %, 80 % et 60 %** de la lumière d'un ciel
clair.

Découverte au passage : une part du biais de nébulosité est **fabriquée par la
correction d'Open-Meteo**, non héritée du modèle. À Pontarlier, le modèle brut
est à +0,5 point d'ERA5 et le corrigé à −8,8.

→ [`regles.md`](regles.md), `scripts/sky_thresholds/`

---

## Étape 4 — Grille de calibration *(en cours)*

Méthode arrêtée — transposition de quantiles préservant la tendance. Table,
interpolation et table provisoire écrites. Pas de 0,5° confirmé par la mesure
contre 1°, qui aurait coûté quatre fois moins.

**Ce qu'elle a corrigé.** Le pas de collecte initial, par latitude croissante,
passait ses premières heures sur le plateau ibérique ; il est désormais ordonné
par population desservie. Et le constat « champ de biais lisse » du script 15
n'est pas général : le versant méditerranéen le contredit, avec 5,52 points sur
un seul degré à la montée vers les Cévennes.

**Reste à faire : la collecte.** 23 nœuds sur 594. C'est le débit d'Open-Meteo
qui commande — de l'ordre de trente nœuds par heure, soit une quinzaine d'heures
encore.

→ [`application.md`](application.md), `scripts/calibration_grid/`

---

## Ce qui reste calé sur une base mince

Aucune décision scientifique n'est en attente, mais deux points méritent d'être
réexaminés le moment venu :

- **le seuil de neige de 1,5 °C**, établi sur deux sites et une seule saison ;
- **l'ensemble des mesures du projet**, qui reposent sur dix sites.
