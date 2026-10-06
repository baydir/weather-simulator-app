# Application — architecture, affichage, grille

Comment le site est bâti et ce qu'il montre. Les règles qu'il applique →
[`regles.md`](regles.md) ; ce qu'il refuse de promettre → [`projet.md`](projet.md).

Ce document décrit l'état actuel. Le chemin qui y a mené est dans
[`journal.md`](journal.md) ; les chiffres de mesure sont attachés au script qui
les imprime.

---

## Nature du site

Un site grand public volontairement restreint : **une page d'accueil portant le
formulaire, une page de résultats**, accompagnées d’une page documentaire statique.

Le formulaire demande un lieu et une période, **et la période de deux façons** :
une plage de dates, ou une saison et une année → [Deux façons de poser la même
question](#deux-façons-de-poser-la-même-question). La seconde ne produit rien que
la première ne produise : elle écrit les mêmes deux dates, dans la même URL.

L'accueil invite à explorer le climat d'une ville. La recherche conduit à des
journées météo et à des courbes de température, puis le visiteur ajoute les
années qu'il souhaite comparer. Le parcours vise le grand public ; les détails
techniques restent dans la documentation et le contrat serveur.

Objectif de conception : simple d'abord, extensible ensuite. Chaque brique est
pensée pour être remplacée sans que les autres bougent.

---

## Répartition entre client et serveur

**Les données sont récupérées par le navigateur**, géocodage compris. Le motif
n'est pas le volume — une plage de 90 jours pèse 4 Ko — mais le fait que **les
limites d'Open-Meteo s'appliquent par adresse IP** : un serveur qui interrogerait
les API concentrerait toute l'affluence sur une seule adresse et atteindrait la
limite immédiatement.

Le géocodage passe par l'API dédiée d'Open-Meteo, non par Nominatim, dont les
conditions d'usage proscrivent les usages intensifs.

**Le navigateur dérive ce dont le serveur ne détient pas de version** : mise en
forme, repères de lecture, ordonnancement, cache. Toute grandeur affichée, et
toute règle dont dépend une grandeur affichée, est calculée en Python, côté
serveur. Le critère n'est pas la difficulté de la tâche, c'est le double
exemplaire → [`CLAUDE.md`](../CLAUDE.md), règle 3.

Le navigateur poste les données brutes ; le serveur valide les entrées, applique
la correction de nébulosité, le bloc de transformation et la classe de ciel, et
renvoie le JSON journalier. Sans état et sans base de données, il monte en charge
par simple multiplication des instances, derrière un frontend statique servi par
CDN.

### Une recherche se fait en deux appels

**Décider quoi demander, le serveur en détient une version** — `/api/days` rejoue
le plan pour vérifier que les payloads reçus correspondent bien à la recherche.
Le refaire dans le navigateur serait un second exemplaire de ce découpage ; et la
coupure se fait à la date du jour prise sur l'horloge du serveur, quand celle du
navigateur est celle du visiteur.

Le serveur décide donc et remet des **URL déjà construites**, requête encodée
comprise ; le navigateur appelle `fetch` sur chacune.

| Appel | Entrée | Sortie |
|---|---|---|
| `POST /api/plan` | lieu et plage | `today`, et la liste `{id, url}` des requêtes à exécuter |
| `POST /api/days` | les mêmes, `today` renvoyé tel quel, les payloads bruts | la série journalière classée |
| `GET /api/config` | — | gabarit de géocodage, bornes de couverture, plage maximale, bornes de l'échelle de température |

`today` circule du premier appel au second pour que les deux moitiés s'accordent
sur l'endroit où l'observé s'arrête, et il est **vérifié à un jour près** de
l'horloge du serveur — au passage de minuit, la coupure s'est déplacée. Il est
**rendu à la page** avec la série, le menu des années à comparer devant savoir
lesquelles sont entièrement passées.

`/api/config` existe pour que les constantes partagées soient **servies et non
recopiées** : la borne de 92 jours s'applique dans l'interface comme dans l'API,
et les huit bornes de l'échelle de température graduent l'axe du graphe. Ce qui
voyage est l'échelle, jamais les teintes — elles restent dans la feuille de style,
comme le pictogramme reste hors du contrat.

Les trois appels sont sans état : la montée en charge par multiplication des
instances reste entière.

**La requête IFS est demandée en chevauchement.** La borne entre les deux passés
se lit dans la réponse des réanalyses, et n'est donc pas connue au moment de
construire le plan. Plutôt qu'un second aller-retour, ou qu'une latence codée en
dur que [`donnees.md`](donnees.md) proscrit, IFS est demandé sur toute la portion
de la plage postérieure à 2017, et **la réanalyse l'emporte à l'assemblage partout
où elle a servi**. Le coût est une requête de plus, de 92 jours au plus, sur toute
plage touchant 2017.

---

## Organisation du code

```
src/weather_simulator/
    sources/       requêtes, lecture des payloads, assemblage des quatre segments
    domain/        enregistrement journalier, seuils, classe de ciel
    transform/     bloc de transformation, neutre par défaut
    api/           endpoints, validation, plan de requêtes, contrat JSON
    calibration/   table de coefficients et interpolation
web/
    pages/         home.html, results.html, documentation.html — HTML statique,
                   aucun gabarit
    static/css/    style.css, une feuille bâtie sur des variables
    static/js/     fetch.js, i18n.js, present.js, bounds.js, band.js, chart.js,
                   series.js, season.js, compare.js, csv.js, dom.js, prompt.js,
                   home.js, results.js
```

Dans `api/`, `plan.py` porte **à la fois la façon de demander chaque segment et
la façon de le relire**. Les deux tiennent dans le même objet à dessein : un plan
et une lecture en désaccord sur les variables qu'une requête portait échoueraient
de la manière la moins visible qui soit — une colonne silencieusement absente.

La séparation entre `domain` et `transform` est délibérée : `domain` porte les
règles arrêtées et n'a pas vocation à bouger, `transform` est le point de
maîtrise sur les données, appelé entre la correction et l'affichage, et ne
transforme rien par défaut.

`pages/` et non `templates/` : un CDN n'exécute pas de gabarit. Les pages sont
donc des fichiers, et l'API les sert par un montage **conditionnel** — `web/`
absent, elle démarre quand même.

**La frontière entre modules du navigateur sépare ce qui se vérifie sans
navigateur de ce qui n'existe que dans la page.** `present.js` (formatage et
arrondis), `bounds.js` (les refus du formulaire), `band.js` (la construction de
la bande), `chart.js` (la géométrie du graphe), `series.js`, `season.js`,
`compare.js` et `csv.js` (le fichier emporté) tournent sous `node --test` ;
`home.js` et `results.js` ne portent que le câblage. C'est la même frontière qui
garde une migration possible.

Quatre modules portent une règle plutôt qu'un rendu, et chacun tient un
invariant qu'un test referme :

| Module | Ce qu'il tient | L'invariant testé |
|---|---|---|
| `series.js` | où la bande et le graphe marquent une couture | une seule fonction pour les deux vues |
| `season.js` | la table des bornes de saison, lue dans les deux sens | demander une saison puis la relire rend la même saison, sur les quatre et les deux hémisphères |
| `compare.js` | l'arithmétique de calendrier de l'année comparée | le 29 février ne glisse pas au mois suivant ; une plage décalée vers une bissextile est rognée par la fin plutôt que de dépasser 92 jours |
| `prompt.js` | la rotation de la question d'accueil | `next` est de l'arithmétique et se teste ; `rotate` est une minuterie et ne se teste pas |

Une propriété de la table des saisons est à savoir avant d'y toucher : **toutes
les bornes tombent sur le 21**, et `rangeOf` s'y appuie pour prendre la veille de
la suivante — le 20 du même mois, sans arithmétique de date ni fuseau à lire. Une
borne déplacée au 1ᵉʳ rendrait un jour zéro, en silence ; un test l'interdit.

Le titre de l'accueil est fixe. `prompt.js` et ses tests restent disponibles,
mais la rotation des questions n'est plus utilisée dans le parcours principal.
Les textes visibles restent centralisés dans `i18n.js`.

---

## Affichage

Une bande journalière, une carte par jour, défilant horizontalement lorsqu'elle
excède la largeur de l'écran. **Plage bornée à 92 jours**, soit une saison —
contrainte appliquée à la fois dans l'interface et dans l'API, jamais dans le
seul navigateur.

**Le nombre est mesuré, non arrondi.** Aux bornes astronomiques que l'interface
propose — le 21 —, l'hiver fait 90 jours, l'automne 91, le printemps et l'été 92.
La valeur ne s'écrit qu'à un endroit, `MAX_DAYS`, et voyage par `/api/config`
jusqu'au libellé du refus.

Chaque journée porte un pictogramme, les températures minimale et maximale, le
cumul de précipitations et la vitesse de vent maximale — et, sur les seules
journées qui franchissent un seuil, un bandeau de chaleur humide. Les courbes
montrent ces mêmes températures → [Les températures à comparer](#les-températures-à-comparer).

**Deux choses sont mises en avant : l'allure du ciel et les deux
températures** — le pictogramme d'abord, les degrés dessous, en corps supérieur
au reste. Une carte lue d'un coup d'œil, parcourue par dizaines, a besoin d'un
point d'entrée pour le regard. Les précipitations et le vent suivent, **à poids
égal entre eux**.

**Le mois est dit deux fois, et de deux façons.** En chiffres sur la ligne de
date, à chaque carte — « lundi 01/08 » — et **écrit en toutes lettres au seul
changement de mois**, la ligne du dessus restant vide ailleurs pour que les
cartes gardent une hauteur.

Le partage est le remède à une gêne réelle : la bande défile horizontalement, et
un lecteur qui dépasse la bascule perdait le mois sans rien pour l'y ramener.
**Deux réponses ont été essayées avant celle-là**, et ce qu'elles ont coûté
explique la forme retenue.

- *Un nom tous les sept jours* échoue là où la gêne est la plus forte : une
  fenêtre étroite montre deux cartes à la fois, donc cinq libellés sur sept
  seraient hors de l'écran.
- *Le nom sur chaque carte* règle la gêne et **coûte au repère qu'il devait
  servir** : « AOÛT » au milieu d'une suite de « JUILLET » ne marque plus rien,
  là où le même mot seul contre trente lignes vides se voyait de loin.

Deux chiffres sur la date disent le mois où que le lecteur se soit arrêté, sans
dépenser un mot, et laissent le nom à la seule carte qui a quelque chose à
annoncer. Longueur vérifiée aux deux largeurs : « dimanche 30/08 » tient dans sa
carte à 1440 px comme à 360.

**La maximale au-dessus, la minimale en dessous**, empilées et non côte à côte.
L'ordre de lecture suit l'œil : un lecteur d'écran entend la maximale en premier,
et `tests/js/band.test.js` fige cet ordre. Le signe degré accompagne chacune des
deux. Les deux textes qui écrivent la paire dans l'autre sens —
[`projet.md`](projet.md) et le README, « 21 °C / 39 °C » — énoncent une plage en
prose, pas une carte.

**Aucune des quatre mesures ne porte de libellé à l'écran, toutes en portent un
dans le document.** Deux nombres près d'un signe degré n'en demandent pas, et
« 4,8 mm » comme « 31 km/h » se lisent sur leur unité. Un lecteur d'écran n'a ni
position ni unité sur quoi s'appuyer : le `dt` reste donc dans le document, hors
champ. Cela vaut aussi pour la classe de ciel écrite, qui double le pictogramme,
et **d'autant plus pour les deux températures** — à 22 °C, une maximale et une
minimale portent le même aplat, et seule la position les sépare à l'écran.

**Le vent moyen n'est pas affiché** — cinq mesures sur une carte lue d'un coup
d'œil sont plus qu'elle n'en porte. La grandeur reste dans le contrat JSON.

**Le vent maximal ne doit pas être libellé « rafale ».** `wind_speed_10m_max` est
le plus fort vent *établi* de la journée ; une rafale vaut couramment le double —
36,8 km/h contre 14,4 km/h à Pontarlier en juin 2024. Le libellé retenu est
« vent maximal ». **Ni « vent » seul** : la carte se lirait comme une moyenne, et
le chiffre serait faux d'un tiers.

| Classe | Contrat JSON | Pictogramme |
|---|---|---|
| Dégagé | `clear` | ☀️ |
| Nuageux | `cloudy` | ⛅ |
| Couvert | `overcast` | ☁️ |
| Pluie | `rain` | 🌧️ |
| Neige | `snow` | 🌨️ |

**Une sixième valeur circule : l'absence de classe.** Une journée dont il manque
une variable nécessaire ne reçoit pas de classe, et le contrat porte `null`
plutôt qu'une valeur inventée. L'interface prévoit cette carte-là.

Les émojis conviennent à une première version : disponibles partout, sans
ressource à charger. **Le contrat JSON transporte donc la classe, jamais le
pictogramme** — un passage à des icônes dessinées ne toucherait que l'affichage.

### Les arrondis d'affichage

Arrondir à l'écran est une décision de traitement de données, que
[`CLAUDE.md`](../CLAUDE.md) range sous validation obligatoire — au même titre
qu'une agrégation. Elle est prise, et la voici :

| Grandeur | Affiché |
|---|---|
| Températures | entier — `21 °C` |
| Température humide | entier — `28 °C`, une température comme les autres |
| Vents | entier — `8 km/h` |
| Précipitations | **une décimale** — `0,4 mm` |
| Nébulosité | non affichée |

**Le dixième sur les millimètres est le seul qui ne soit pas cosmétique.** La
porte à 1 mm sépare les journées sèches des humides et commande deux des cinq
classes de ciel → [`regles.md`](regles.md). Afficher « 0 mm » sur une journée
portant le pictogramme de la pluie serait une contradiction visible à l'écran, là
où « 0,4 » et « 1,2 » se distinguent. Cette règle vaut partout où un millimètre
s'écrit, cartes et graphe compris : deux règles d'arrondi pour une seule grandeur
seraient une divergence de plus.

### Le bandeau de chaleur humide

**Il ne paraît que sur les journées qui franchissent un seuil**, et les deux
seuils sont dans [`regles.md`](regles.md) avec ce qui les a placés. La grandeur
est sans objet le reste du temps : l'afficher partout mettrait un nombre sans
portée sur quatre-vingt-neuf cartes sur quatre-vingt-dix.

**La ligne est réservée sur toutes les cartes de la bande, ou sur aucune.** Les
cartes sont étirées à la plus haute, si bien qu'une ligne apparaissant sur la
seule journée chaude d'une plage déplacerait la bande sous l'œil du lecteur.
C'est la réponse que la ligne de mois donne déjà au même problème : rendue vide
là où le mois n'a pas tourné. Ce qui évite au bandeau d'en coûter le prix se
décide un
rang plus haut — une plage qui ne porte aucun niveau ne réserve rien du tout, et
c'est le cas de toute recherche française. La réponse porte donc
`humid_heat_peak`, sur le modèle de `has_simulated` : le serveur a déjà parcouru
les journées, le navigateur ne les reparcourt pas.

**Le mot d'abord, le nombre dessous.** Une température humide n'a pas d'échelle
pour un lecteur — 31 °C est mortel et se lit comme une douceur — et la carte
porte déjà deux températures en corps supérieur, si bien qu'un troisième nombre
nu se lirait comme une troisième température de l'air. Deux choses l'évitent : le
mot arrive d'abord et nomme ce qui suit, et le nombre est composé comme une
mesure, dans le corps de « 0,4 mm » et non dans celui des maximales. Arbitrage du
porteur du projet, le 7 septembre 2026 ; l'ordre et le corps sont ce qui reste de
l'arbitrage antérieur, lequel gardait le nombre hors de la carte.

**Deux niveaux, dits par le mot et par le poids, jamais par un second
pictogramme.** Une tête de mort sur une journée datée annoncerait une mort le
16 août 2043, ce que la règle 1 interdit ; et ce serait l'élément le plus emporté
en copie d'écran, hors de l'avertissement qui l'entoure.

**Une phrase sous la bande dit ce que la marque signifie**, et paraît avec elle.
Elle décrit l'air et non le lecteur, ce qui la met hors d'atteinte de la règle 1
sur une journée simulée, et elle n'énonce aucun seuil de survie : ce serait une
affirmation médicale sur une date déterminée.

**Le contraste du bandeau n'est pas dans la table publiée**, et ce n'est pas un
oubli : l'élément n'existe pas sur la page que `scripts/ink_contrast.py` mesure,
et y amener le script changerait la géométrie de référence, donc toutes les
lignes déjà publiées. Mesuré à part, l'encre `--warm` sur le papier de la carte
donne 4,88 à 6,00:1 selon le thème et l'origine de la journée, au-dessus du
plancher de 4,5.

### Ce que l'interface ne calcule pas

Aucune moyenne de période, aucun comptage de journées de pluie, aucun extrême de
la plage. Ce sont des agrégations, et une agrégation faite à l'affichage relève
de la même validation que l'arrondi ci-dessus. Les compteurs autorisés ci-dessous
sont calculés par le serveur, jamais par l'interface.

La règle porte sur la bande comme sur le graphe. Une courbe est **une marque par
journée** et n'agrège rien : ce qu'elle ajoute est la forme de la période, que
l'œil compose et que l'interface ne calcule pas.

Le module historique conserve le cumul des précipitations, autorisé le
14 août 2026 : un cumul par journée, coupé aux données manquantes, tracé sans
valeur totale écrite. Ce panneau n'est plus affiché dans le parcours principal.
La fenêtre verticale des températures réutilise les mêmes graduations et
la même fonction de cadrage que le graphe historique.

**Tout écran affichant une journée simulée porte un avertissement explicite et
visible** → [`projet.md`](projet.md). Une recherche qui ne dépasse pas la
prévision n'en porte pas : l'avertissement y serait faux. La bascule se lit sur
`has_simulated`, jamais sur un comptage de journées.

---

## L'accueil

Un fond clair et un formulaire sur une surface blanche remplacent le ciel
animé. Le titre « Votre ville, au fil du climat. » reste fixe. La première étape
est le choix explicite d'une ville dans les résultats du géocodage ; la seconde
est une plage de dates ou une saison et son année. La météo actuelle comme
porte d'entrée reste une piste → [`idees.md`](idees.md).

Les styles du parcours sont limités à `body.explorer`. La page documentaire
conserve sa présentation. Les mesures de contraste de l'ancien habillage ne
constituent pas une validation de ce nouvel écran.

### Deux façons de poser la même question

Le formulaire demande une période de deux manières, **exclusives et
basculables** : une plage de dates, ou une saison assortie d'une année. La seconde
existe parce que la question que ce site pose porte le plus souvent sur une
saison — « un été à Montpellier en 2050 » — et que la première oblige à savoir
que l'été ouvre le 21 juin.

**La page s'ouvre sans aucun des deux, et c'est un troisième état de plein
droit.** L'accueil montre un lieu et deux bandes ; le panneau ne se déplie qu'une
fois l'une pressée, et **le bouton d'envoi est replié avec eux** — étaler une
plage que personne n'a demandée revient à répondre avant d'avoir posé la
question. La touche Entrée reste un chemin d'envoi qu'aucun bouton caché ne
ferme, et le formulaire la refuse explicitement tant qu'aucune période n'a été
choisie.

**Le mode saison écrit dans les deux champs de date ; il ne les remplace pas.**
Ni le sélecteur de saison ni celui d'année ne porte d'attribut `name`, donc aucun
des deux n'est soumis, et l'URL reste les mêmes cinq paramètres — `lieu`, `lat`,
`lon`, `debut`, `fin`. Une saison est un intervalle, et l'API n'a jamais rien
demandé d'autre. **La bascule est deux boutons, non un groupe de radios**, pour
la même raison en sens inverse : des radios ne se groupent qu'en partageant un
`name`, et un `name` est précisément ce qu'un formulaire GET met dans l'adresse.

**La saison est à gauche, et l'ordre est celui du balisage** — un lecteur d'écran
et un clavier doivent rencontrer les deux boutons dans l'ordre où un œil les
rencontre, ce qu'un réordonnancement en CSS ne donne pas. Les panneaux, eux,
gardent le leur : un seul est ouvert à la fois, donc leur ordre n'est jamais lu,
et celui qui s'affiche sans script doit rester celui que le balisage ne masque
pas.

Les deux modes utilisent des boutons clairs ; le mode actif porte un fond
bleu et un contour renforcé. Le bouton d'envoi, bleu plein, reste distinct.

**Le repli est écrit dans le script, pas dans le balisage.** La page est livrée
les deux panneaux ouverts et le bouton visible ; c'est `home.js` qui les ferme au
chargement. Un visiteur sans JavaScript retrouve ainsi le formulaire d'avant la
saison, plutôt qu'un formulaire sans période et sans moyen d'en révéler une.

**L'année est celle où la saison commence**, pour les quatre : « hiver 2029 » va
du 21 décembre 2029 au 20 mars 2030. L'usage français laisse le tour ambigu ; la
règle retenue est uniforme. La contrepartie est que l'hiver 2050 finirait hors
couverture — la liste des années est construite sur les bornes servies par
`/api/config`, et cette année-là n'y figure pas plutôt que d'être offerte pour
être refusée.

**Sous l'équateur, la saison demandée est celle du lieu.** « Été » à Santiago va
du 21 décembre au 20 mars — le même saut que fait le sol de la page de résultats,
pris en sens inverse, sans quoi une recherche intitulée « été » ouvrirait une page
peinte en hiver.

**Quitter le mode saison ne remet pas les dates par défaut.** La plage qu'une
saison vient de produire est bonne à ajuster à la main, et l'effacer jetterait ce
que le visiteur vient de demander.

---

## La page de résultats

Le lieu et la période apparaissent en tête. La comparaison occupe la première
section ; les cartes de la période initiale restent accessibles dessous. La
page utilise le même fond clair que l'accueil, indépendant de la saison.
Les palettes saisonnières et le repérage de saison restent dans le code,
mais ne déterminent plus le fond de ce parcours.

La provenance détaillée, l'export CSV et les panneaux de pluie ne sont plus
proposés dans le parcours principal. Leurs modules et les données serveur
restent disponibles ; les cartes conservent les mesures météo quotidiennes.
Les avertissements de simulation et les marques de chaleur humide restent
visibles là où les données les demandent.

### L'échelle de couleur des températures

Les deux nombres d'une carte portent un aplat coloré, et le nombre se lit dessus.
**L'échelle est absolue** : la couleur ne dépend que de la température, jamais de
la date ni du lieu. Aucune normale n'entre dans le calcul ; les normales ont servi
à **placer les bornes**, pas à comparer.

**Neuf bandes de cinq degrés**, de moins de 5 °C à 40 et au-delà :

| bande | couleur | aplat | encre |
|---|---|---|---|
| < 5 °C | bleu foncé | `#123a72` | blanc |
| 5 à 10 | bleu clair | `#5aa9de` | sombre |
| 10 à 15 | vert clair | `#8bc94a` | sombre |
| 15 à 20 | jaune | `#f2ce1b` | sombre |
| 20 à 25 | orange | `#f0902a` | sombre |
| 25 à 30 | rouge clair | `#e9634a` | sombre |
| 30 à 35 | rouge foncé | `#b01712` | blanc |
| 35 à 40 | rouge très foncé | `#6b0a0a` | blanc |
| ≥ 40 | noir | `#16100c` | blanc |

Pourquoi neuf bandes, pourquoi de 5 à 40, et ce que la période de référence
1981-2010 produit → [`scripts/temperature_scale/`](../scripts/temperature_scale/README.md).

**L'encre bascule avec le fond, et c'est ce qui rend le jaune possible.** Une
encre blanche unique obligerait chaque aplat à être assez sombre pour la porter,
et un jaune assez sombre pour du blanc *est* un ocre. Chaque bande nomme donc son
encre : blanc sur les quatre sombres, noir cassé sur les cinq claires. **Plancher
mesuré : 5,51:1**, porté par le rouge clair ; `scripts/ink_contrast.py` relit les
neuf paires depuis la feuille de style à chaque fois que l'une bouge.

**Où la couleur ne sépare plus.** Les trois dernières bandes sont rouges ou
noires : la teinte n'y distingue plus rien, seule la clarté le fait, et l'écart
entre le rouge très foncé et le noir vaut 1,50:1. Côte à côte c'est net ;
éloignées dans la bande, ces deux-là se lisent surtout par le nombre qu'elles
portent. Les six premières s'en sortent mieux parce qu'elles changent de teinte en
même temps que de clarté.

**L'aplat est la seule forme pleine du site**, là où la feuille pose que rien
n'est dans une boîte. L'exception se paie et se justifie : une teinte posée sur
une surface se distingue bien mieux de sa voisine que la même teinte sur les
traits fins d'un chiffre, et c'est la seule chose de la carte qui doive se lire
comme une **quantité** plutôt que comme un mot.

---

## Les températures à comparer

### Les compteurs de chaleur

Trois comptages sont validés par le porteur du projet : **maximale > 30 °C**,
**maximale > 35 °C**, **minimale ≥ 25 °C**. Ils portent sur les valeurs complètes,
avant tout arrondi d'affichage, et sur toutes les origines selon la même règle.
Le dernier concerne la minimale quotidienne ; ce n'est pas un relevé horaire
exclusivement nocturne. Les jours > 35 °C font aussi partie du compteur > 30 °C.

`domain/heat_counts.py` tient les définitions et le calcul uniques. Le pipeline
les applique après transformation, puis sert `heat_counts` : champ lu, seuil,
comparateur, compte, nombre de valeurs disponibles et nombre de journées
servies. Une valeur absente ou non finie est exclue ; aucune valeur disponible
produit un compte nul (`null`), distinct de zéro dépassement mesuré.

Chaque année montre les trois résultats et le nombre de journées renseignées
rapporté à la durée demandée. Aucune extrapolation ne complète une période
incomplète. Ces comptes décrivent les périodes choisies et ne sont pas, à eux
seuls, une mesure de tendance climatique. Une période simulée garde son
avertissement visible.

### Les calendriers

**Le calendrier est la première lecture.** Les années choisies sont placées
côte à côte, une case par journée. Une commande commune choisit les maximales
ou les minimales quotidiennes ; ces dernières servent de repère pour la nuit,
sans prétendre être une mesure exclusivement nocturne. Les couleurs viennent
directement de `temperature_max_band` ou `temperature_min_band`, jamais d’un
reclassement côté navigateur. La légende lit les bornes de `/api/config`.

Chaque mois conserve une grille de six semaines, avec des cases vides hors de
la période demandée. Une valeur manquante reste hachurée. Une case sélectionnée
énonce date, température et origine ; la couture vers la simulation est
repérée au même jour que dans la bande.

## Comparer à une autre année

Le visiteur ajoute explicitement les années à comparer à la période initiale.
**Aucune année de référence n'est sélectionnée automatiquement.** Le menu
propose les années dont la plage décalée tient dans les bornes de couverture
servies par l'API, passé et futur compris. `shiftRange` conserve son traitement
des années bissextiles et des périodes traversant le changement d'année.

Chaque année passe par le même `search`, donc `/api/plan` et `/api/days` :
aucune règle de traitement scientifique n'est ajoutée au navigateur. Une seule
requête de comparaison est lancée à la fois ; les réponses sont gardées en
mémoire pour la page. Un échec laisse les autres années visibles et permet de
redemander l'année. Retirer une année ne supprime pas sa réponse en mémoire.

Chaque panneau nomme les origines présentes dans sa réponse. Un avertissement
commun au-dessus des années apparaît dès qu'une réponse porte `has_simulated` ;
il n'est pas répété dans chaque panneau. Chaque courbe garde sa couture.
Les calendriers permettent de lire les températures et leur origine pour chaque
année comparée. La bande météo détaillée au bas de la page reste réservée à
la période initialement choisie.

Une note rappelle que l'écart entre deux années ne mesure pas, à lui seul, le
réchauffement climatique. L'évolution montrée est celle des journées des
années choisies, sans prétendre constituer une estimation statistique de
l'évolution du climat.

## Emporter les journées

Le module `csv.js` et ses tests sont conservés, mais l'export n'est pas proposé
dans cette première interface centrée sur l'exploration grand public.

---

## Le contrat JSON

Un tableau d'objets journaliers, stable et documenté, pour qu'un graphique, un
cumul ou une carte s'y branchent sans toucher au pipeline. Chaque journée porte
`date`, `origin`, `source`, les deux températures, `precipitation`, `cloud_cover`,
les deux vents, `sky`, et les deux bandes de l'échelle de couleur —
`temperature_min_band` et `temperature_max_band`.

**Il transporte la classe, jamais le dessin.** `sky` est un mot parmi cinq et
l'émoji vit du seul côté de l'affichage ; les deux bandes sont un entier de 0 à 8
et la teinte vit dans la feuille de style. Le partage est le même, et pour la même
raison : savoir dans quel palier tombe une température est une règle dont dépend
une grandeur affichée, donc elle revient au serveur ; de quelle couleur ce palier
se dessine ne regarde que la page, et repeindre la rampe ne doit toucher rien
d'autre.

**Ce qu'il ne transporte pas est aussi arrêté que ce qu'il transporte.** Ni
`temperature_mean`, demandée pour le seul critère de neige et que
[`donnees.md`](donnees.md) dit non affichée ; ni `snowfall`, conservée comme
témoin mais servie d'un seul côté de la couture ; ni le pictogramme, ni les
couleurs, ni aucune gradation d'intensité.

La réponse porte en outre **`has_simulated`** et les métadonnées de la grille. Le
premier dit si l'avertissement est dû. Il est servi plutôt que recalculé sur les
journées, parce que le serveur en détient une version — et c'est la donnée dont
dépend la règle 1, celle qui prime sur toutes les autres. Les secondes sont nulles
quand rien n'a été corrigé, ce qui est la réponse honnête pour une plage
entièrement passée.

**La nébulosité est arrondie au dixième à la sortie, et à la sortie seulement.**
L'interpolation des quatre nœuds laisse dix-sept décimales, qui revendiquent une
précision que la table n'a pas — elle stocke des dixièmes. L'arrondi intervient
**après** que la classe a été décidée : une journée à 29,97 % ne doit pas devenir
nuageuse parce qu'on l'a rangée.

Les refus sortent en français, prêts à afficher, sous un champ `message` unique
quelle que soit la cause.

---

## La grille de correction

La correction de nébulosité est **précalculée hors ligne** et embarquée comme
ressource serveur. À la requête, l'application repère les quatre nœuds entourant
le point, interpole et applique — **sans aucun appel externe**.

**Ce n'est pas une table de coefficients**, et c'est la conséquence directe de la
méthode : une correction quantile par quantile ne se résume pas à un nombre par
mois. Chaque nœud porte, pour chacun des douze mois, **trois vecteurs de
quantiles** — la réanalyse sur la période de calibration, le modèle sur cette même
période, le modèle sur la projection. Le premier écart est le biais, le second la
tendance à préserver. Trente-neuf niveaux par vecteur, arrondis au dixième de
point.

Réseau **mondial fixe au pas de 0,5°**, aux multiples exacts depuis −180° et −90°.
Non négociable : caler l'origine sur la France imposerait de tout recalculer au
premier élargissement. L'interpolation porte une **erreur propre, à déclarer avec
les autres** : 0,3 point de nébulosité en moyenne, 0,7 au maximum sur relief. Le
pas, le volume du réseau, le débit de la collecte et ce qui les établit →
[`scripts/calibration_grid/`](../scripts/calibration_grid/README.md).

### Hors de la zone couverte

**La recherche est servie, et la projection y est rendue telle que le modèle la
donne, sans correction.** C'est un régime dégradé, assumé comme tel, et
**provisoire** : il tient jusqu'à ce qu'une grille mondiale existe.

Ce que ce choix a remplacé. L'application refusait la recherche, au motif qu'un
futur non corrigé est un futur artificiellement ensoleillé. Le motif reste vrai,
et la mesure ne bouge pas : le modèle est en retrait de 8 à 11 points de
nébulosité, et trois des cinq classes de ciel dépendent de ce nombre. Ce qui a
changé, c'est l'alternative. Étendre la grille au monde a été chiffré : au pas de
0,5°, de l'ordre de cent mille nœuds, soit **deux à cinq ans** de quota au débit
observé ; même desserrée à 3°, la collecte demande vingt à soixante jours. Le
refus n'était donc pas une attente, c'était un refus définitif pour tout lieu hors
de France. **Une réponse imparfaite et signalée a été préférée à une absence de
réponse.**

**Ce que le régime dégradé coûte, dit franchement.** Le passé et la quinzaine à
venir sont des observations et restent justes partout. Seul le segment simulé est
brut. La bande **s'éclaircit donc visiblement** là où la prévision passe la main à
la simulation, et c'est exactement l'artefact de couture que le reste du
dispositif combat. Il est ici la contrepartie acceptée, non un oubli.

**Un décalage mensuel global a été envisagé et écarté.** Douze nombres tirés des
nœuds déjà collectés rattraperaient 59 % de l'écart au modèle brut, mesuré en
France. Ils ont été écartés parce que rien ne prouve que le biais du modèle se
transporte hors de France, et qu'une correction non validée présentée comme une
correction vaut moins qu'une absence de correction déclarée.

**Comment les deux régimes se distinguent, dans le contrat.** Le champ `grid` de
la réponse porte les métadonnées de la table quand elle a servi, et vaut `null`
quand rien n'a corrigé. `has_simulated` reste vrai dans les deux cas :
l'avertissement qu'exige la règle 1 de [`CLAUDE.md`](../CLAUDE.md) est piloté par
lui, jamais par la grille, et il s'affiche donc hors couverture comme ailleurs.

**Ce qui n'est plus jamais refusé, c'est un lieu.** Une recherche n'est écartée
que pour ce qu'elle demande : une plage trop longue, des dates hors de
1950-2050. Jamais pour l'endroit d'où elle est faite. Le refus hors grille
subsiste dans le code à l'état de filet : il ne peut être atteint que si la grille
déclare couvrir un point puis se découvre un nœud manquant, ce qui serait un
défaut et non un lieu.

### Métadonnées et table provisoire

La table porte ses propres métadonnées — modèle corrigé, maille, périodes de
calibration et de projection, date de génération, nombre de nœuds. Une table lue
sans savoir cela est une source d'erreur silencieuse, et c'est précisément la pièce
dont un successeur héritera sans avoir vu comment elle a été faite.

**Une table provisoire existe, et elle se dénonce.** La collecte se comptant en
heures de quota, une table à correction identité couvre toute la boîte française
pour que le reste de la chaîne s'écrive sans l'attendre. **Elle ne doit jamais être
servie** : une correction nulle affiche un futur artificiellement ensoleillé de 8 à
11 points, et trois des cinq classes en dépendent. Cinq verrous plutôt qu'un :

1. un drapeau `placeholder` dans les métadonnées, dont un test vérifie qu'il
   survit à l'écriture-relecture ;
2. une propriété exposée à l'appelant ;
3. un nom de fichier distinct ;
4. une exclusion du dépôt, par une règle `.gitignore` ancrée à la racine ;
5. **le refus de démarrer.**

Le dernier est le seul qu'aucun oubli ne contourne, les quatre autres supposant
qu'un appelant pense à les consulter. L'application lit la table une fois au
démarrage et s'arrête net si elle porte le drapeau.

---

## Préparé sans être construit

- **L'internationalisation** : tous les textes visibles sont extraits dans un
  dictionnaire dès le départ. Trivial maintenant, coûteux plus tard.
- **Les pages explicatives** : statiques, aucune infrastructure particulière.

---

## Choix techniques

**FastAPI** plutôt que Flask : validation des entrées par Pydantic, documentation
OpenAPI automatique, meilleur ajustement à une API JSON sans état.

**JavaScript natif en modules ES**, sans cadriciel. Deux pages ne le justifient
pas, et l'absence de chaîne de compilation garde le projet abordable. Les
frontières de modules sont posées de sorte qu'une migration reste possible.
