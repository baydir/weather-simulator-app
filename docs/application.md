# Application — architecture, affichage, grille

Comment le site est bâti et ce qu'il montre. Les règles qu'il applique →
[`regles.md`](regles.md) ; ce qu'il refuse de promettre → [`projet.md`](projet.md).

Ce document décrit l'état actuel. Le chemin qui y a mené est dans
[`journal.md`](journal.md) ; les chiffres de mesure sont attachés au script qui
les imprime.

---

## Nature du site

Un site grand public volontairement restreint : **une page d'accueil portant le
formulaire, une page de résultats**. Des pages explicatives viendront plus tard,
statiques et peu interactives.

Le formulaire demande un lieu et une période, **et la période de deux façons** :
une plage de dates, ou une saison et une année → [Deux façons de poser la même
question](#deux-façons-de-poser-la-même-question). La seconde ne produit rien que
la première ne produise : elle écrit les mêmes deux dates, dans la même URL.

L'accueil n'annonce pas le site par son nom. Il pose une question qui tourne —
« Pourrais-je faire pousser des tomates à Montpellier en 2050 ? » — et met la
promesse dessous. Un nom dit comment la chose s'appelle et rien de ce à quoi elle
sert ; le nom reste dans le titre de l'onglet, qui est l'endroit où un nom se lit
vraiment.

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

Les questions de l'accueil sont tenues **par deux tests** : `prompt.test.js`
vérifie que chacune pose bien une question et que la promesse garde son verbe —
« Simulez », l'un des trois termes que la règle 1 retient ; `present.test.js`
porte la liste des mots proscrits et signale la fautive sous
`home.questions.<rang>`. Ni l'un ni l'autre ne rattrape « Quel temps fera-t-il à
Nice en 2050 ? », qui ne contient aucun mot interdit et promet pourtant la
journée.

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
cumul de précipitations et la vitesse de vent maximale. **Sous la bande, les
mêmes journées dessinées** → [Le graphe sous la bande](#le-graphe-sous-la-bande).

**Deux choses sont mises en avant : l'allure du ciel et les deux
températures** — le pictogramme d'abord, les degrés dessous, en corps supérieur
au reste. Une carte lue d'un coup d'œil, parcourue par dizaines, a besoin d'un
point d'entrée pour le regard. Les précipitations et le vent suivent, **à poids
égal entre eux**.

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

### Ce que l'interface ne calcule pas

Aucune moyenne de période, aucun comptage de journées de pluie, aucun extrême de
la plage. Ce sont des agrégations, et une agrégation faite à l'affichage relève
de la même validation que l'arrondi ci-dessus. **L'interface montre les journées,
et rien au-dessus d'elles.**

La règle porte sur la bande comme sur le graphe. Une courbe est **une marque par
journée** et n'agrège rien : ce qu'elle ajoute est la forme de la période, que
l'œil compose et que l'interface ne calcule pas.

**Le cumul des précipitations est la seule exception, arbitrée le 14 août 2026.**
Trois traits l'y autorisent, dont aucun ne se transporte à une moyenne ni à un
comptage. Il **parcourt** la période au lieu de la résumer, une valeur par
journée à sa date. Il ne **s'écrit** jamais : seule sa graduation porte des
nombres, et le total ne se lit que comme une hauteur. Et il se **dit calculé** —
aucun point, là où chaque lecture en porte un, et une coupure sur une journée
manquante plutôt qu'un trait par-dessus. Il occupe **un panneau à lui** → [Le
graphe sous la bande](#le-graphe-sous-la-bande).

Un test refuse par défaut tout texte du graphe qui ne soit ni un titre, ni une
graduation, ni un repère de lecture, **ni le nom de l'année comparée** — celle-ci
nomme une marque, comme l'étiquette de couture nomme un passage, et n'est ni un
total, ni une moyenne, ni un comptage, ni un extrême. Élargir cette liste est un
acte, et le test vérifie que rien d'autre n'est passé avec.

Ce qu'une ligne de synthèse aurait dit — « tant de journées à 30 °C d'un côté et
de l'autre » — reste écarté alors même que la comparaison au climat ancien est
faite : le graphe rend inutile ce à quoi elle devait suppléer.

**Le cadrage des trois axes est la seule autre chose que le graphe décide**, et
les trois relèvent de la validation qu'exige la règle 4 → [Les trois
axes](#les-trois-axes).

**Tout écran affichant une journée simulée porte un avertissement explicite et
visible** → [`projet.md`](projet.md). Une recherche qui ne dépasse pas la
prévision n'en porte pas : l'avertissement y serait faux. La bascule se lit sur
`has_simulated`, jamais sur un comptage de journées.

---

## L'accueil

L'accueil porte un couchant, **écrit en dégradé CSS** à partir de onze couleurs
échantillonnées dans la photographie de référence. La photographie n'ayant aucun
détail — c'est un lavis —, le dégradé la reproduit pour zéro octet et reste net à
n'importe quelle densité d'écran.

**Il est ancré au document, non à la fenêtre**, et ce point n'est pas cosmétique :
fixé à la fenêtre, la couleur sous un élément donné dépendrait de la hauteur
d'écran du lecteur. **Aucun voile n'est posé dessus** — un assombrissement achète
du contraste en salissant la photographie. La lisibilité se paie en encre :
l'encre secondaire est éclaircie sur cette page, et l'avertissement passe en brun
brûlé, seul texte à tomber sur la bande claire quelle que soit la fenêtre. Les
étiquettes du formulaire prennent l'encre pleine, leur hiérarchie restant portée
par leur forme — onze pixels, capitales, interlettrage.

**Plancher de contraste : 4,6:1**, porté par les champs de date. Les tables
complètes, la méthode et les tailles de fenêtre →
[`scripts/ink_contrast.md`](../scripts/ink_contrast.md).

La chaleur qui monte de la bande basse est **une bande translucide qui passe sur
le lavis**, non un filtre de déplacement : sans détail à déformer, l'opération
chère et la gratuite convergent, et la seconde tient 121 images par seconde. Le
miroitement s'arrête entièrement sous `prefers-reduced-motion`, comme la rotation
de la question.

### Le formulaire sur le ciel

Sur un dégradé le fond est une variable, et rien de ce formulaire n'est dans une
boîte.

**Le bouton d'envoi ne porte pas de fond opaque** : un brun brûlé à 45 %, que le
ciel traverse, et un filet d'ivoire à 22 %. **Le filet est une ombre interne et
non une bordure** — une bordure ajouterait deux pixels de hauteur, et sur cette
page un bouton plus haut pousse l'avertissement sur une autre zone du dégradé. Le
survol **fonce** le fond au lieu de l'éclaircir, de sorte que le rapport monte en
approchant et ne descend jamais.

**La liste des lieux flotte au-dessus de la page au lieu de la pousser** : une
réponse passagère à ce qu'on est en train d'écrire ne doit coûter aucune hauteur,
sans quoi les champs que le lecteur vient de regarder glissent sous ses yeux dès
la deuxième lettre tapée. **Elle est opaque, et c'est la seule surface du site qui
le soit** — lire un nom de commune au travers de « 12/08/2026 » est pire que de ne
pas afficher la liste du tout. Elle prend `#27030a`, le dernier arrêt du dégradé,
**servi et non recopié** dans une variable que les deux lisent, comme `--sky-head`
est à la fois le fond du `body` et le premier arrêt.

**Les champs de date rendent visible où l'on se trouve dans la date.** Le
navigateur marque le segment que la frappe suivante changera, avec une couleur
système que la page ne peut pas choisir : `::selection` est inerte, `accent-color`
aussi. Ce qui s'atteint, c'est ce qui entoure la marque — `color-scheme: light`
demande au système sa marque claire, et le champ prend un fond sombre **pendant
l'édition seulement**. Au repos, une date reste une ligne de texte sur un filet.

La contrepartie n'est pas réparable : la marque de segment et le calendrier natif
viennent du même réglage et ne se séparent pas, donc le calendrier s'ouvre en
clair. L'échange est assumé — le calendrier est un passage bref, le repérage dans
la date un geste constant.

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

**Les deux bandes sont dans la grammaire du bouton d'envoi, à un rang en
dessous** : même fond brun, plus léger — 24 % contre 45 — parce qu'à leur hauteur
il se compose sur du bleu et non sur le couchant, et plus basses que lui, 12 px
de rembourrage contre 20. Elles choisissent la question, lui la pose. Choisir une
bande l'approfondit jusqu'au fond du bouton et lui donne un filet d'encre pleine.

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

La page porte **le sol de la saison sur laquelle porte la recherche**. L'été vient
de `design/summer_result.svg` et la page a été dessinée sur lui ; les trois autres
en dérivent.

**La saison se compte, elle ne se lit pas à une extrémité.** Le navigateur
parcourt la plage jour par jour et retient celle qui en tient le plus. Trois
arbitrages complètent la règle :

- **Bornes astronomiques**, 21 décembre au 20 mars et ainsi de suite — les dates
  sur lesquelles le visiteur a été interrogé. Elles glissent d'un jour selon
  l'année dans le ciel et pas ici : un sol qui changerait de teinte le 20 mars une
  année et le 21 la suivante répondrait à une question que personne ne pose.
- **Saisons inversées sous l'équateur.** La latitude voyage dans l'URL à côté des
  dates, et janvier à Santiago est un été. Une latitude illisible retombe sur
  l'hémisphère nord — le calendrier, plutôt qu'une erreur.
- **À égalité parfaite, la saison où la plage se termine.** Une plage se lit vers
  l'avant.

**La saison demandée et la saison peinte se rejoignent, et ce n'est pas une
coïncidence** : `rangeOf` et `seasonOf` lisent la même table en sens inverse, y
compris sous l'équateur, où l'un traduit vers l'hémisphère nord et l'autre en
revient. Un test le vérifie plutôt que de l'espérer → [Organisation du
code](#organisation-du-code).

**Ce comptage se fait dans le navigateur, et la règle 3 n'y voit rien à redire** :
le serveur n'en détient aucune version, il n'y a donc pas de second exemplaire.
C'est de la mise en forme dérivée de deux dates déjà présentes dans l'URL, au même
titre que le repérage des mois dans la bande. La saison est posée sur le `body`
avant le premier rendu, et **avant les quatre allers-retours** : une recherche
refusée porte son sol comme une autre.

### Les quatre sols

**L'été est relevé, les trois autres sont dessinés.** Le dégradé de la maquette
est une image matricielle encastrée dans le fichier Inkscape : il a été décodé
puis échantillonné tous les dix pour cent, ce qui donne onze arrêts. Il n'existe
pas de maquette pour les trois autres, et leur inventer onze arrêts serait une
précision qui ne mesurerait rien — ils en portent **cinq**, choisis pour la teinte
du milieu. Cet arrêt central est tout le travail : blanc à marron interpolé en
sRVB passe par un beige sale, blanc à bleu par un gris mort.

```
été       0 % #fafdea   30 % #fe9e52   60 % #fd3a0c   90 % #810402
         10 % #f9deb1   40 % #ff7b30   70 % #fd2101  100 % #070000
         20 % #fbbe7f   50 % #fd5816   80 % #d60e01

hiver     0 % #f7fbfe   20 % #dbeaf7   40 % #b3d0e8   60 % #6f9dc9   80 % #2c5b90   100 % #0a1b33
printemps 0 % #f9fcef   20 % #eaf3c8   40 % #d8e894   60 % #c8d94a   80 % #5f8a22   100 % #0f2409
automne   0 % #fdf7ec   20 % #fae2bd   40 % #f3bb72   60 % #e08a35   80 % #a4501a   100 % #1e0c03
```

**La forme est celle de l'été sur les quatre** : clair jusqu'au milieu,
l'assombrissement concentré après 70 %. C'est ce qui porte la date nue au-dessus
d'une carte et ce qui permet à la provenance de rester pâle au pied. Le printemps
y perd sa lecture littérale — le vert-jaune occupe le milieu, le pied descend vers
un vert de sous-bois —, l'alternative étant un pied clair qui obligerait la
provenance à changer d'encre selon la saison.

**Cette page s'inverse en descendant, et c'est toute sa difficulté.** Le premier
écran est presque blanc et le dernier presque noir : aucune encre ne sert les deux
extrémités. L'encre est donc sombre par défaut, et **le seul bloc qui bascule au
clair est la provenance**, au pied de la page.

Six variables changent avec la saison, et six seulement : le dégradé, sa tête, et
les quatre encres qui se posent dessus.

| | encre | encre secondaire | filet | filet fort |
|---|---|---|---|---|
| hiver | `#0b1c30` | `#12293f` | `#5b87b5` | `#2f5b87` |
| printemps | `#17280c` | `#24380f` | `#7d9438` | `#4c6d1e` |
| été | `#21100a` | `#3d1608` | `#c9793f` | `#8f3f16` |
| automne | `#2a1206` | `#3d1c07` | `#bd7734` | `#8c4315` |

**L'encre secondaire y est presque aussi noire que l'encre principale** : sur
l'été, le ton qui *lit* comme secondaire tombe à 2,6:1 sur l'orange saturé du
milieu, où se posent le marqueur de mois et la ligne du scénario. Ce qui sépare
ces textes de ce qu'ils nomment, c'est leur forme — onze pixels, capitales,
interlettrage —, comme sur l'accueil.

**Rien d'autre ne bouge**, parce que rien d'autre ne touche au sol. Les cartes
restent blanches sur les quatre, et le graphe est dessiné sur le même papier ;
les deux températures se mesurent contre une carte, non contre un ciel. **La
carte cesse par ailleurs d'être la boîte** : la date se pose nue sur le dégradé,
et seul le corps en dessous est dessiné. Le rouge `#d40000` et le bleu `#0044aa`
de la maquette servent de repli sur une carte — une journée sans température n'a
pas de bande, donc pas de couleur d'échelle — et **de couleur propre aux deux
courbes du graphe**.

**La page tient au moins la fenêtre**, pour deux raisons superposées. Le calque du
ciel est calé sur le `body` : sans hauteur minimale il s'arrêterait où s'arrête le
contenu, laissant de la crème nue sous le dégradé. Et la provenance, qui s'écrit
en clair, ne le peut que là où le dégradé a viré au noir : tenue au pied par une
marge automatique, elle est **à 92-94 % du dégradé quelle que soit la fenêtre**.
Elle ne tient plus *dans* la fenêtre, en revanche, et c'est un arbitrage rendu :
le graphe est la seconde lecture de la recherche et non une note, donc la page
défile plutôt que de le replier.

**Plancher de contraste : 7,9:1**, porté par le dépliant de provenance au
printemps — le dernier texte de la page, donc le plus bas sur le dégradé. Les
quatre tables, les deux géométries et la méthode →
[`scripts/ink_contrast.md`](../scripts/ink_contrast.md).

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

## Le graphe sous la bande

**Une carte dit une journée, et jamais la forme de la période** — où la chaleur se
tient, quelle quinzaine est humide. C'est ce que le graphe ajoute, et ce qui règle
sa largeur : dessiné colonne par colonne sous les cartes, il serait aligné et
inutile. Il prend la largeur de la page et porte la plage entière.

**Trois panneaux partageant un axe de dates, jamais deux échelles verticales sur
un même tracé** — un lecteur prend le croisement d'une courbe et d'une barre pour
un fait météorologique. Les températures sont au-dessus, les précipitations
ensuite, leur cumul en bas, chacun dans un panneau à lui avec sa propre ligne de
base et son titre.

**Le troisième panneau est ce qui garde la règle entière** : posé sur les barres
avec un axe à droite, le cumul l'aurait levée. Il coûte de la hauteur de page et
ne demande rien en échange — plus rien ne croise rien.

**Chaque journée porte sa marque, et les segments sont droits.** La donnée est
l'agrégat journalier ; une courbe lissée inventerait un mardi après-midi dont la
série n'a aucune lecture. Une journée manquante coupe la courbe au lieu d'être
traversée, et une lecture isolée garde son point sans segment.

**Rien n'est rempli tant qu'il n'y a qu'une année**, de sorte qu'un aplat sur ce
panneau dise une seule chose — *ceci est l'année ancienne*. L'amplitude entre les
deux températures reste la place entre deux courbes toutes deux présentes, en
couleur, portant leurs points.

### Les trois axes

Ce sont, avec le cumul lui-même, les seules décisions du graphe, et toutes
relèvent de la validation.

**En température, l'axe se cale sur les bornes de l'échelle de couleur** : bas au
multiple de cinq sous la lecture la plus froide, haut au multiple au-dessus de la
plus chaude, plus une demi-bande d'air à chaque bout. **À l'intérieur de
l'échelle, chaque filet est une borne servie** — le même palier que les aplats des
cartes, de sorte qu'une hauteur ici et une couleur là-haut soient la même lecture.
**Au-delà de ses deux extrémités ouvertes, le réglage continue au même
intervalle** : tout ce qui est sous 5 °C est une seule bande et n'a aucune borne à
tracer, si bien qu'une période gelée recevrait sinon un panneau réglé une fois. La
continuation pose la ligne sur zéro, et symétriquement sur 45.

Un axe absolu fixe est écarté : il tiendrait la comparaison entre deux recherches,
au prix d'écraser une plage d'été dans un tiers du panneau.

**Une année comparée est cadrée avec celle qu'on regarde, dans une fenêtre
unique** — deux courbes sur deux échelles ne disent rien l'une de l'autre. Le
panneau des pluies, lui, ne voit pas l'année comparée : elle n'y est pas dessinée,
donc son plafond ne bouge pas.

**Le pied du panneau des températures est un cadre, pas un zéro.** La ligne de
base des pluies *est* la donnée : les barres s'y appuient, c'est zéro millimètre.
Celle des températures tombe sur le demi-palier où la fenêtre s'est calée —
7,5 °C sur un été, −12,5 sur une période gelée. Elle est tracée parce qu'un
panneau ouvert sur un côté se lit comme inachevé, et **elle ne porte aucun
nombre** : le plus bas chiffre écrit sur l'axe reste la première borne servie à
l'intérieur de la fenêtre, un filet au-dessus.

**En précipitations, l'axe prend la journée la plus arrosée de la période, avec un
plancher de 10 mm.** Le plancher n'est pas un confort : sans lui, une plage dont
la journée la plus humide fait 0,3 mm cadrerait l'axe sur 0,3 mm, et cette bruine
dessinerait la même barre qu'un orage de 40 mm ailleurs. Rien n'étant servi pour
graduer ce panneau, l'intervalle se choisit sur la hauteur qu'il a : le plus petit
pas rond laissant au plus quatre intervalles — 5 et 10 sur une période calme, 10
et 20 sur une période humide.

**En cumul, l'axe prend le total de la période**, sous le même plancher de 10 mm
et gradué par la même règle — **une seule fonction, appelée une fois par panneau
de millimètres**, filets, nombres et pied compris ; recopiée, elle aurait été
cinq lignes évidentes tenues à deux endroits. Si l'échelle des pas va jusqu'à
500, c'est que le total d'une saison est d'un ordre de grandeur au-dessus de sa
journée la plus arrosée : la queue de la liste n'est atteinte que par le total,
la tête que par les journées.

**Un panneau garde sa graduation quand il n'a rien à tracer** — filets et aucune
courbe, comme le panneau des pluies en reçoit sans barre. Un dessin dont la forme
suivrait les trous de la série changerait pour une raison que le lecteur ne voit
pas.

**La marge de gauche vaut 68 unités**, mesurée sur le « 100,0 mm » du cumul, qui
est désormais le plus large nombre du dessin.

**Aucun nombre portant sur la période n'est écrit.** Les plafonds dépendent du
maximum et du total, mais ni l'un ni l'autre n'est affiché → [Ce que l'interface
ne calcule pas](#ce-que-linterface-ne-calcule-pas).

### Où l'on est dans la période

**Un nom de mois dit quel mois, et rien de l'endroit où l'on est dedans** — sur
quatre-vingt-douze jours, un mois fait trois cents unités de large. Le 1ᵉʳ, le 10
et le 20 portent donc un trait court et leur nombre. Trois par mois est le plus
petit compte qui suffise : neuf jours au plus serré, ce qui laisse partout la
place de deux chiffres.

**Une marque se pose sur une journée que la série porte**, lue sur sa propre date.
Aucune journée n'est inventée pour porter un nombre rond : une plage ouvrant le 21
n'a ni 1ᵉʳ, ni 10, ni 20 dans ce mois-là et n'en reçoit aucun. Les deux rangées
parcourent les journées pour cette raison, et non le calendrier.

**Chaque panneau est daté à son propre pied**, par une seule fonction appelée une
fois par panneau — le panneau des températures fait à lui seul 245 unités, et
dater un point du panneau du bas obligerait à remonter l'œil par-dessus deux
autres. Ce sont les mêmes journées aux mêmes abscisses, un axe lu trois fois et
non trois axes, et un test vérifie que les colonnes coïncident.

**Les mois ne sont nommés que sous le panneau du bas**, où les nombres les
surmontent, dans l'ordre où une date française se dit. Le nombre est centré sur sa
colonne, là où se trouve le point de la journée ; le nom de mois garde le bord
gauche, parce qu'il nomme un basculement et non une journée.

**Chaque écart entre deux panneaux tient la rangée du haut** : titre du bas à
douze unités au-dessus de son panneau, rangée de dates à quatorze sous le sien.
Il faut une ligne de texte entière entre les deux — un titre posé juste sous un
axe appartient à l'axe —, ce que le test exige au lieu de la seule absence de
chevauchement, **et dans les deux écarts** — le second casserait en silence.

### Ce que le graphe emprunte

**Il est dessiné sur le papier des cartes**, et ses marques prennent les couleurs
déjà nommées par la feuille. Il n'ajoute donc **aucune variable saisonnière** :
les six qui tournent restent six. C'est aussi ce qui impose le papier plutôt que
le sol : posée sur le dégradé, une courbe rouge tomberait vers les deux tiers sur
le rouge de l'été, où elle cesse d'exister.

**Il porte la même couture que la bande, au même jour** — une verticale traversant
les trois panneaux, sous la même étiquette. Où elle tombe est une règle partagée
par un seul module, `series.js`, et non recopiée dans chacune des deux vues.

**Son équivalent accessible est la bande elle-même**, qui porte déjà chaque valeur
en toutes lettres. Le dessin est annoncé par un nom qui renvoie à elle, et ne
réénonce aucun nombre : une infobulle serait un second exemplaire de la carte. La
bande ne montrant qu'une année, l'équivalent des courbes grises est ailleurs →
[Comparer à une autre année](#comparer-à-une-autre-année).

**Le cumul n'en demande pas un autre** : il est calculé sur des millimètres que
la bande écrit tous, et ce qu'il ajoute est une forme, comme les courbes en
ajoutent une. Le nom du dessin gagne une phrase disant que le panneau existe ; le
total n'est écrit nulle part, pour aucun lecteur.

**Sous 58 rem, il défile latéralement au lieu de rétrécir.** Le dessin est un
`viewBox` unique et se met à l'échelle en entier, sa typographie comprise : à la
largeur d'un téléphone, les nombres de l'axe sortiraient à quatre pixels. Il n'y a
pas de point de rupture à choisir — le minimum est l'endroit où onze unités valent
onze pixels — et c'est la réponse que la bande donne déjà au même problème.

---

## Comparer à une autre année

**« 39 °C » ne dit quelque chose qu'à qui sait ce qu'était un 14 juillet
auparavant** : la pédagogie est dans l'écart, pas dans la valeur. Un bouton sous le
graphe pose une autre année sur les mêmes panneaux, où la superposition *est*
la comparaison.

**Aucun code serveur.** Les mêmes dates dans une autre année repassent par
`/api/plan` et `/api/days`, qui les découpent, les corrigent et les classent avec
les mêmes fonctions — [`CLAUDE.md`](../CLAUDE.md) règle 2 obtenue en ne calculant
rien de neuf.

**Deux requêtes, et pas de grille.** Une plage entièrement passée coûte les deux
requêtes d'archive et n'appelle aucun coefficient →
[`donnees.md`](donnees.md). La comparaison marche donc **partout dans le monde**,
et elle y est même exacte là où la projection ne l'est pas : l'année comparée est
observée, elle ne passe pas par la correction. **Une requête par année, au
plus** : ce qui est revenu est gardé en mémoire. Un échec ne touche pas la page —
il s'écrit dans le bloc, les journées demandées étant déjà à l'écran.

### Le choix de l'année

**Une année choisie d'intuition se trompe de l'ordre de grandeur du signal.**
`scripts/model_selection/reference_year.py` note chaque année en écarts-types de
sa période, sur cinq sites français : **1980 est à −2,00 σ en été** et montrerait
environ deux fois le réchauffement qu'il y a, **2003 à +3,25 σ** montrerait un
refroidissement, et une année prise dans les années 2000 dépense un degré du
signal avant de commencer — les sites français se réchauffent de 0,92 °C entre
1979-1988 et 1999-2008.

**La plus ordinaire de la période la plus ancienne exploitable est 1991**
(+0,49 σ en été, −0,46 en hiver, +0,03 sur l'année, sur 1979-1994) ; sur
1979-2008 ce serait 2004. **Le menu s'ouvre sur 1991 et laisse choisir** de 1950 à
la dernière année entièrement
passée — arbitrage du porteur du projet. Le lecteur garde la main ; ce que le
défaut achète, c'est que personne n'atterrisse sur 1980 sans le vouloir.

**La dernière année offerte se déduit du `today` du serveur**, remonté par
`/api/plan` jusqu'à la page : une comparaison atteignant la prévision ne serait
pas une autre année de météo, mais la même trajectoire en gris. Une journée qui
n'est pas `observed` est écartée en plus de cela.

**Deux exigences d'honnêteté, faute de quoi la fonction induit en erreur.** Le
libellé dit que l'année a été *choisie pour être ordinaire* — la période affichée,
elle, n'a pas été sélectionnée et peut porter une canicule ; comparer un tirage
libre à un tirage choisi pour sa sagesse laisserait croire que le passé n'avait
pas d'extrêmes. Et la sélection portant sur la seule température, **la pluie de
l'année retenue est quelconque**. Elle est dessinée malgré tout, par arbitrage
du porteur du projet, sur les deux panneaux de pluie ; la note dit ce que la
sélection n'a pas regardé, faute de quoi le gris se lirait comme une normale
de pluie.

### Ce que le dessin en fait

**L'année comparée est une bande, pas deux courbes de plus.** Ses deux lectures
sont tracées en gris fin, l'écart entre elles rempli, et **aucun point** : le
point est la marque de l'année demandée. Elle cesse ainsi d'être deux tracés à
suivre pour devenir le sol contre lequel les deux courbes saturées se lisent — la
question étant si la journée tient dans ce qui était ordinaire ou en sort.

**Sur les deux panneaux de pluie, le gris est posé par-dessus et non dessous.**
Deux barres partent de la même ligne de base : la plus courte est *dans* la
plus haute et non à côté, si bien qu'une barre grise placée dessous
n'apparaîtrait que les jours où le passé était le plus humide, soit la moitié
de la comparaison. Posée dessus et translucide, les deux hauteurs se lisent et
le recouvrement fait une troisième teinte. Le cumul, lui, repasse dessous comme
les températures : deux courbes fines se croisent sans se cacher. **Un seul
plafond cadre les deux années** dans chacun des deux panneaux, pour la raison
qui vaut déjà pour la fenêtre des températures : cadrées chacune sur son propre
maximum, la plus forte barre d'une année sèche viendrait à la hauteur de la
plus forte d'une année humide, et le panneau montrerait son cadrage plutôt que
la météo.

**Le gris est un jeton posé à côté des deux températures**, mesuré à 3,44:1 sur le
papier du graphe — un trait suivi à l'œil en demande 3. La force du remplissage
vit dans un second jeton, le témoin de la légende étant en HTML et un `span` ne
pouvant pas emprunter un `fill` de SVG.

**L'année est écrite sur le dessin**, dans la marge au-dessus de chacun des
trois panneaux — la seule bande où aucune marque ne peut tomber —, et ses
chiffres prennent l'encre douce de la graduation. Chaque libellé porte
l'échantillon de sa propre marque : la bande sur les températures, une barre
sur les précipitations, un trait sur le cumul. Ils sont dessinés avec les
classes des marques elles-mêmes, un témoin tenu à jour à la main étant le
double exemplaire que la règle 3 interdit. C'est la seule chose que le graphe
écrive en plus des titres, graduations et repères → [Ce que l'interface ne
calcule pas](#ce-que-linterface-ne-calcule-pas).

**Le bloc de comparaison est sur le papier du graphe**, seul sol qui ne bouge pas :
posé sur le dégradé il mesurerait 1,1:1, et le basculer en encre pâle comme la
provenance ne marche pas — celle-ci est tenue au pied par une marge automatique
quand ce bloc suit la fin du graphe. Les deux notes d'honnêteté en dépendent : un
avertissement illisible équivaut à un avertissement absent. Il est en outre **hors
du cadre défilant** — un contrôle à l'intérieur de `.chart-panel` quitterait
l'écran avec le dessin sous 58 rem.

**L'équivalent accessible des courbes grises est une page de résultats, à un lien
de distance.** La bande n'écrit qu'une année, et c'est le seul vrai trou de la
fonction. L'année comparée étant une recherche ordinaire de ce site, un lien
« Voir 1991 en détail » ouvre sa propre page, avec sa bande, ses cartes et chaque
nombre en toutes lettres. Il est posé avant même que les données arrivent : il
reste vrai qu'elles arrivent ou non.

---

## Emporter les journées

**Un bouton discret sous le graphe écrit à l'écran ce que la page a déjà en
mémoire**, en CSV : une ligne par journée, la série affichée, et l'année
comparée avec elle lorsqu'elle est sur le panneau. Aucun code serveur, aucune
requête de plus — le fichier est une seconde écriture de ce qui est déjà arrivé.

**`origine` et `source` sont des colonnes, sur chaque ligne.** C'est la règle 1
appliquée à un fichier plutôt qu'à un écran : un fichier survit à la page qui
l'a produit, et une température sans origine à côté d'elle se lit des années
plus tard comme une mesure. Sur la ligne et non en tête de fichier, la marque ne
peut pas être séparée du nombre qu'elle qualifie, et elle survit à un tri, à un
filtre et à un copier-coller vers une autre feuille. Les trois mots sont ceux du
site : *observé*, *prévision*, *simulation*.

**Rien n'est calculé.** Chaque colonne est un champ servi par l'API. Le cumul
des précipitations reste sur le graphe : c'est la seule agrégation admise ici,
et l'emporter dans un fichier élargirait cette exception sans arbitrage → [Ce
que l'interface ne calcule pas](#ce-que-linterface-ne-calcule-pas). Un tableur
le refait d'une formule sur la colonne des précipitations.

**Point-virgule, virgule décimale, marque d'ordre d'octets.** Un tableur
français ouvre le fichier d'un double-clic ; `read_csv` demande alors `sep=";",
decimal=",", encoding="utf-8-sig"`. La convention inverse déplacerait la gêne
sur le visiteur, à qui le bouton s'adresse. Le nom du fichier porte le lieu et
la plage — `meteo-brest-2046-07-01-2046-07-31.csv` — parce que deux exports d'un
même après-midi sont deux recherches différentes, et que `donnees (1).csv` ne se
distingue plus de rien une semaine après.

**Le bouton est hors du bloc de comparaison** : il offre ce qui est dessiné que
l'autre année le soit ou non, et plié dans ce bloc il se cacherait derrière un
contrôle que le visiteur n'ouvre peut-être jamais. Il tombe dans le bas sombre
du dégradé et bascule donc en encre pâle avec la provenance sous lui — mesuré à
6,7:1 au pire → [`ink_contrast.md`](../scripts/ink_contrast.md).

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
