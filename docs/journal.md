# Journal — ce qui a été fait

Ce document tient l'avancement et, pour chaque étape, **ce qu'elle a corrigé de
ce que la conception avait supposé**. C'est le seul endroit où l'état du projet
se met à jour.

---

## Où on en est

Les étapes 0 à 3, la 5, la 6 et la 7 sont faites, la 4 est engagée. **Le site
fonctionne.** Le passé est servi partout, la quinzaine à venir aussi depuis
l'étape 7 ; la collecte de l'étape 4 étant inachevée, seul le futur au-delà de la
prévision reste borné à ce que la grille a refermé.

L'étape 9 est née de la chaleur humide, ajoutée hors numérotation : elle a fait
apparaître une seconde entrée du modèle climatique dont le biais n'est pas
mesuré, l'humidité, là où l'étape 4 s'occupe de la nébulosité. Le besoin est
identique, il est simplement pris un cran plus tôt — la formule est réglée, c'est
l'entrée qui ne l'est pas.

L'ordre effectif s'écarte de l'ordre annoncé : l'étape 5 a été menée avant que la
collecte de l'étape 4 soit finie. Elle le pouvait sans la table provisoire, la
collecte ayant déjà refermé trois mailles autour de Paris — de quoi éprouver la
chaîne complète sur une correction authentique.

| | Étape | Dépend de | État |
|---|---|---|---|
| 0 | Nettoyage du prototype, packaging, `.gitignore` | — | **fait** |
| 1 | Récupération et série homogène, sans classe de ciel | 0 | **fait** |
| 2 | Confirmation du modèle parmi les cinq éligibles | 1 | **fait** |
| 3 | Calage des seuils de nébulosité et classe de ciel | 1 | **fait** |
| 4 | Grille de calibration France et correction de nébulosité | 2 | *en cours, 438 nœuds sur 594* |
| 5 | API, validation des entrées et bloc de transformation | 3, 4 | **fait** |
| 6 | Interface : accueil, résultats, bande journalière | 5 | **fait** |
| 7 | La quinzaine à venir, servie par ECMWF IFS | 1, 6 | **fait** |
| 8 | Élargissement mondial de la grille | 4 | à faire |
| 9 | Calibration de l'humidité du modèle | 1 | à faire |

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

**Le débit a été mal lu, et deux fois.** On l'avait estimé à trente nœuds par
heure, soit une quinzaine d'heures pour la France — chiffre tiré d'une fenêtre de
trente-six minutes prise sur un quota frais. Le plafond est en réalité
**journalier**, Open-Meteo le disant lui-même par un `HTTP 429 : Daily API
request limit exceeded`, et il laisse passer cinquante à cent trente nœuds par
jour. La France demande donc de l'ordre de la semaine. La leçon est de méthode :
les nœuds arrivant par salves, un rythme mesuré à l'intérieur d'une salve n'est
pas un débit.

**Un défaut d'indexation a coûté cinq nœuds sur 219.** `build.py` rangeait chaque
nœud sur la coordonnée renvoyée par Open-Meteo — le centre de sa maille, parfois
à un quart de degré du point demandé — puis l'arrondissait au réseau. Or Python
arrondit un demi vers le pair : `round(49,25 × 2) / 2` vaut 49,0 et non 49,5. Le
nœud demandé à 49,5 disparaissait, et celui de 49,0 recevait en silence une
correction mesurée vingt-huit kilomètres plus au nord. La clé se lit désormais
dans le nom du fichier, qui porte le point demandé. Neuf mailles y étaient
suspendues, dont toute la Normandie.

**Reste à faire : la collecte.** 438 nœuds sur 594, 365 mailles refermées — 37
des 39 villes de la liste de priorité. Ne manque plus que la Corse, Bastia et
Ajaccio.

**Et une leçon d'exploitation, payée deux fois.** La collecte remplit le cache ;
`build.py` en fait la table ; l'application la lit au démarrage. Chacun de ces
trois pas peut être en retard sur le précédent sans que rien ne le signale, et le
symptôme — une ville refusée alors que ses quatre nœuds sont sur le disque — se
lit comme un défaut de couverture, pas comme un décalage. Pontarlier a été
collecté, puis refusé pendant deux jours faute de reconstruction.

Le second retard est de la même famille : `pkill -f run_until_done` ne tue que le
script enveloppe, et le collecteur Python lui survit. On se retrouve alors sans
relance automatique mais avec le quota qui continue de partir, et sans le journal
pour le dire. Le motif qui coupe les deux est
`pkill -f 'run_until_done|calibration_grid/collect.py'`.

Le chiffre a triplé en trois jours sans que rien change au débit : c'est le
plafond journalier, décrit plus haut, qui commande — il suffit de relancer.

→ [`application.md`](application.md), `scripts/calibration_grid/`

---

## Étape 5 — API

Trois endpoints sans état, la validation des entrées, le contrat JSON et le bloc
de transformation, laissé neutre. Éprouvée de bout en bout sur données réelles :
une plage à cheval sur aujourd'hui rend 41 jours — 15 de réanalyse, 6 d'IFS, 20
du modèle — sans trou ni doublon.

**Ce qu'elle a corrigé.** La conception voulait que le navigateur récupère les
données *et* ne dérive rien. Les deux exigences se contredisent en apparence,
puisque **décider quoi demander est une dérivation**. Il a fallu un endpoint de
plan : le serveur remet des URL déjà construites, le navigateur les exécute à
l'aveugle. D'où trois endpoints, non plus un.

Second écart, de même origine : **la borne entre les deux passés se lit dans la
réponse**, et ne peut donc pas figurer dans un plan construit d'avance. IFS est
désormais demandé en chevauchement, la réanalyse l'emportant à l'assemblage — une
requête de plus contre un aller-retour de moins, et la borne toujours lue dans
les données.

Rien de scientifique n'a bougé. Le chiffre à retenir est un coût : la correction
d'une requête de 90 jours prend **1,2 ms**, et la table complète tiendra en
**29 Mo** résidents.

→ [`application.md`](application.md)

---

## Étape 6 — Interface

Deux pages HTML statiques, JavaScript natif en modules ES, sans cadriciel ni
chaîne de compilation. L'accueil porte le formulaire et le choix de la commune,
les résultats la bande journalière, la couture, l'avertissement et la provenance
de la table.

Éprouvée sur données réelles : 18 journées à cheval sur aujourd'hui, la couture
au bon jour, les repères de mois aux seuls changements. Interface et API refusent
les mêmes plages sur dix cas limites, dont le 90ᵉ jour contre le 91ᵉ, et une
plage à cheval sur le passage à l'heure d'été.

**Ce qu'elle a corrigé.** La carte portait **cinq mesures**, elle en porte
**quatre**. [`application.md`](application.md) avait tranché sur le papier dans
le sens de la carte complète ; la première bande construite a tranché dans
l'autre, à l'usage — cinq nombres sur une carte destinée à être lue d'un coup
d'œil, et parcourue par dizaines, sont plus qu'elle n'en porte. Le vent moyen
reste servi par le contrat JSON, il n'est plus affiché.

Second écart, de forme : le même document annonçait un répertoire de gabarits là
où il exigeait un frontend statique servi par CDN. Les deux ne tiennent pas
ensemble, et c'est le gabarit qui saute.

**Et une confirmation, la première du genre.** La règle 3 avait été reformulée
juste avant l'étape, autour du **double exemplaire** plutôt que de la difficulté.
L'étape l'a mise à l'épreuve : le navigateur dérive trois choses — le repère de
mois, la marque de couture, le refus des bornes avant tout appel — et aucune
n'est un second exemplaire. Le serveur ne détient pas de version des deux
premières ; quant au troisième, ce sont les **nombres** qui divergeraient, et ils
viennent de `/api/config`. La reformulation tient.

→ [`application.md`](application.md)

---

## Étape 7 — La quinzaine à venir

**Ce que l'étape a corrigé de ce que les précédentes supposaient.** Le découpage
posait la coupure à ce soir : au-delà, le modèle climatique. C'était traité comme
une conséquence des sources disponibles, alors que c'était un segment manquant.
Un modèle climatique n'est pas initialisé sur l'état de l'atmosphère, donc sa
première journée est aussi étrangère à demain que la dernière l'est à 2050 — et
demain, à la différence de 2046, se vérifie. Le constat n'est pas venu d'une
mesure mais de l'usage : les premiers jours se lisaient comme une prévision
fausse.

**Ce n'est pas un quatrième segment, c'est le segment IFS qui va plus loin.**
L'archive jusqu'à ce soir, la prévision jusqu'à J+14, le même système de part et
d'autre. Ce soir cesse d'être une couture ; il y en a toujours deux, et la
seconde se place là où la prévisibilité s'arrête.

**Le sondage qui a décidé l'étape**, Toulouse, dix journées communes : l'analyse
et la prévision sont à 0,53 °C et 3,4 points de nébulosité d'écart moyen. À
comparer aux −1,8 à +0,9 °C de la couture d'archive que le forçage de `models`
évite, et aux 8 à 11 points de déficit du modèle climatique qui justifient toute
la grille. C'est la plus petite jonction de la série. La mesure aux dix sites de
l'étape 2 reste à passer → `scripts/forecast_seam/`.

**Ce que l'étape a débloqué sans qu'on le cherche.** Une plage tenant dans la
quinzaine ne comporte aucune journée simulée, donc n'appelle aucune correction :
elle est servie partout dans le monde, sans attendre les 594 nœuds.

**Ce qu'elle a coûté.** La règle 1 a dû être amendée : « l'application ne produit
pas de prévision » était devenu faux. L'amendement distingue les deux régimes de
futur sans rien retirer au lointain, et la contrepartie est assumée — un lecteur
qui vérifie J+3 et trouve juste peut reporter cette confiance sur 2046.

→ [`donnees.md`](donnees.md), [`projet.md`](projet.md), `scripts/forecast_seam/`

---

## Le graphe de la période

Hors numérotation : une addition à l'étape 6, pas une étape. Sous la bande, les
mêmes journées dessinées — deux courbes de températures, les précipitations en
barres, toute la plage d'un seul regard. Deux panneaux partageant un axe de
dates, jamais deux échelles verticales sur un tracé. Ils sont trois depuis le
cumul, et la règle n'a pas bougé : c'est elle qui lui a valu un panneau.

**Ce qu'il a corrigé de ce que l'étape 6 supposait.** Deux phrases de
[`application.md`](application.md) sont tombées, et aucune des deux n'était
fausse sur le fond. « La bande montre les journées, et rien au-dessus d'elles »
disait *la bande* quand elle voulait dire *l'interface* : une courbe est une
marque par journée et n'agrège rien, ce qu'elle ajoute est une forme que l'œil
compose. Et « la page est la fenêtre », qui tenait pour un ensemble fixe de blocs,
ne survit pas à un bloc de 420 px : la page passe de 789 à 1212 px et défile. Le
choix entre replier le graphe et laisser la page s'allonger a été tranché par le
porteur du projet, en faveur du second.

**Les deux axes sont alors les deux seules décisions du graphe** — un troisième
panneau en a ajouté un depuis → [Le cumul des
précipitations](#le-cumul-des-précipitations) —, et les deux ont été
arbitrées comme des décisions de traitement, non de développement. La température
se cale sur les bornes de l'échelle de couleur ; les précipitations sur la
journée la plus arrosée de la période, avec un plancher de 10 mm — sans lequel
une bruine de 0,3 mm dessinerait la barre d'un orage.

**Ce que le rendu a attrapé et que les tests ne pouvaient pas voir.** L'étiquette
de l'axe des pluies sortait du cadre par la gauche et affichait « 0,0 mm » là où
elle devait dire « 10,0 mm » : un chiffre faux, lisible, et parfaitement
silencieux. Regarder le dessin est une vérification à part entière, et pas un
excès de zèle — c'est le même constat que la mesure des contrastes avait imposé à
l'accueil.

**Une confirmation de la règle 3, appliquée cette fois à l'intérieur du
navigateur.** La bande et le graphe doivent marquer la même couture au même jour.
Le serveur n'en détient aucune version, donc rien n'y obligeait ; mais une règle
tenue à deux endroits diverge, que la frontière soit entre deux langages ou entre
deux modules. Elle est sortie dans `series.js`, que les deux vues appellent.

**Ce qu'il a coûté, et un défaut qu'il a mis au jour.** Les deux tables de
contrastes ont été remesurées en entier : le dégradé étant ancré au document, une
page plus haute l'étire et déplace chaque bloc. Tout est monté — plancher à 6,5:1
contre 4,6:1 auparavant —, ce qui est mécanique et non un progrès de palette. La
remesure a par ailleurs montré que `ink_contrast.py` mesurait les deux
températures contre la carte alors qu'elles sont sur leur aplat depuis la rampe :
il rapportait un blanc sur blanc à 1,0:1 et en faisait le plancher de la page.
Les deux lignes ont été retirées, la table de la rampe publiant déjà les neuf
rapports qui comptent.

→ [`application.md`](application.md)

---

## La saison demandée par son nom

Le formulaire ne savait demander qu'une plage de dates. Or la question que le
site existe pour poser porte sur une saison — « un été à Montpellier en 2050 » —
et y répondre obligeait le visiteur à savoir que l'été ouvre le 21 juin, puis à
essuyer un refus parce qu'il en avait demandé 92 quand l'API en servait 90.
L'accueil porte donc **deux modes exclusifs** : la plage de dates, inchangée, et
une saison assortie d'une année.

**Et il ne montre ni l'un ni l'autre avant qu'on ait choisi.** La page s'ouvre
sur un lieu et deux bandes ; le panneau se déplie au clic, le bouton d'envoi avec
lui. Une plage étalée d'emblée répondait avant qu'on ait posé la question, et
laissait partir une quinzaine par défaut que personne n'avait regardée si le
visiteur allait droit au bouton. Le repli est écrit dans le script et non dans le
balisage : livrée ouverte, la page reste utilisable sans JavaScript.

**Quatre arbitrages ont été rendus par le porteur du projet** avant d'écrire une
ligne : deux modes exclusifs plutôt qu'un raccourci ; l'année est celle où la
saison *commence*, ce qui ne se voit que sur l'hiver ; sous l'équateur la saison
demandée est celle du lieu ; et la borne passe à 92.

**Quatre-vingt-dix n'était une saison que par approximation.** Aux bornes
astronomiques que l'interface propose — le 21 —, l'hiver fait 90 jours, l'automne
91, le printemps et l'été 92. La borne amputait donc les deux plus longues de
deux jours, ce qui était sans conséquence tant qu'on ne pouvait pas demander une
saison par son nom. `MAX_DAYS` est la seule écriture du nombre, et le passage a
révélé la copie qui l'accompagnait : `errors.py` écrivait 90 en dur, en anglais
et en français, et les deux phrases auraient continué de l'annoncer.

**La page de résultats n'a pas bougé d'une ligne, et c'est le résultat.** Le mode
saison écrit dans `debut` et `fin` au lieu de les remplacer ; ni le sélecteur de
saison ni celui d'année ne porte de `name`, donc rien du mode ne quitte
l'accueil. L'URL reste les mêmes cinq paramètres, `/api/plan` reçoit un
intervalle comme toujours, et une saison *est* un intervalle. C'est ce que le
contrat JSON et le découpage en segments achetaient depuis le début.

**Une confirmation de la règle 3 à l'intérieur d'un fichier.** `seasonOf` lit une
date et rend une saison ; `rangeOf` fait l'inverse. Écrire « 21 juin au 20
septembre » une seconde fois pour le second sens aurait été la duplication que la
règle vise, et la règle ne se soucie pas de ce que les deux copies tiennent dans
le même module. Les bornes sont donc déclarées une fois, et un test **referme le
cycle** sur les quatre saisons et les deux hémisphères : sans lui, le jour où les
deux lectures divergent, le formulaire demande un été et la page peint un hiver.

**Ce que la borne a démenti, sans rien casser.** `season.js` justifiait son
comptage par « deux candidates au plus », l'hiver faisant exactement 90 jours. À
92 une plage peut en toucher trois. Aucune ligne n'a changé : le comptage n'a
jamais compté que des journées, et c'est la justification qui avait pris une
commodité pour une propriété.

**L'accueil s'est fait mesurer pour la première fois par une commande**, et c'est
elle qui a dessiné le formulaire. Ses six contrastes avaient été relevés à la
main une fois ; `ink_contrast.py` fait désormais les deux pages, l'accueil en
trois colonnes — un état par panneau, plus celui où rien n'est ouvert. Le dégradé
étant ancré au document, la hauteur que les bandes ajoutent pousse les champs
vers le bleu pâle, et **la bande entre 50 % et 65 % du dégradé ne porte aucune
encre** : le noir pur y plafonne à 4,0:1. C'est une hauteur, pas un ton — et
trois décisions de forme en sont sorties, qu'aucun jugement à l'œil n'aurait
prises : bandes côte à côte plutôt qu'empilées (45 px contre 96), plus basses que
le bouton d'envoi, et la respiration du haut de page ramenée de 10 vh à 6 vh. Une
quatrième est venue du rendu et non du chiffre : à 45 % d'opacité les bandes
lisaient comme des dalles collées sur la photographie, et elles sont passées à
24 %, où elles gardent 7,7:1.

Plancher à **4,6:1** contre 4,2 avant ce travail.

**Deux constats consignés plutôt que recouverts.** Le bouton sort à 7,0:1 quand
le document publiait 7,5, sur une méthode dont la table de la page de résultats
se reproduit sur ses quarante-huit cellules. Et **les autres tailles de fenêtre
ne passent pas**, ce qui est antérieur à ce travail et n'avait jamais été mesuré :
sur une fenêtre haute le plancher est l'avertissement de la règle 1, à 3,7:1. Le
remède touche la composition de la page et **reste à arbitrer**.

→ [`application.md`](application.md)

---

## La comparaison à une autre année

Hors numérotation : une addition à l'étape 6, comme le graphe. Un bouton sous le
dessin pose les températures d'une année ancienne sur le même panneau — une bande
grise que les deux courbes de l'année demandée traversent ou surmontent. Le menu
s'ouvre sur **1991**, mesurée comme la plus ordinaire de la période la plus
ancienne exploitable, et laisse choisir de 1950 à la dernière année entièrement
passée.

**Ce qu'elle a corrigé de ce que [`idees.md`](idees.md) supposait.** Trois
suppositions sont tombées, et aucune n'était une erreur de raisonnement : c'était
la forme envisagée qui les portait. La seconde bande de quatre-vingt-dix cartes a
été remplacée par une superposition sur le graphe, ce qui a fait tomber avec elle
la ligne de synthèse qui devait la sauver — laquelle était une agrégation. Le
déclenchement ne suit pas la règle du refus hors grille : une plage passée
n'exige aucune correction, donc la comparaison marche partout dans le monde, y
compris là où le futur est refusé. Et l'année n'est pas figée par région, le
défaut mesuré suffisant à écarter la lecture fausse.

**Elle n'a rien coûté au serveur, et c'est le point le plus important.** Les
mêmes dates dans une autre année repassent par `/api/plan` et `/api/days`, donc
mêmes segments, mêmes seuils, même fonction de classe de ciel. La règle 2 est
tenue sans une ligne de Python — deux requêtes d'archive, et pas de grille.

**Ce que le rendu a attrapé, trois fois.** Le bloc de comparaison posé sur le
dégradé mesurait **1,1:1** : encre sombre sur un fond qui vire au noir en bas de
page. L'encre pâle de la provenance n'était pas la réponse — celle-ci est tenue
au pied par une marge automatique quand ce bloc suit la fin du graphe, donc sur
une fenêtre haute il retombe au milieu de l'orange. Il est passé sur le papier,
seul sol qui ne bouge pas. Le gris des courbes, ensuite, mesurait 2,95:1, sous
les 3:1 qu'un trait suivi à l'œil demande ; il est à 3,44:1. Et la bande a
purement disparu le jour où sa force est passée dans un jeton : `.chart-ribbon`
se posait à 0,07 d'opacité, que la règle ne remettait plus à 1, si bien que
0,22 × 0,07 ne peignait rien. Invisible, silencieux, parfaitement plausible dans
le code.

**Une règle a été élargie sciemment.** Le test qui refuse tout texte du graphe
n'étant ni un titre, ni une graduation, ni un repère a gagné une entrée pour
l'année comparée. Une année nomme une marque, comme l'étiquette de couture nomme
un passage ; ce que la règle vise — total, moyenne, comptage, extrême de la plage
— reste refusé, et un test vérifie que rien d'autre n'est passé avec.

**Ce que le dessin a gagné dans la foulée.** Les deux panneaux ont été agrandis
dans leur rapport de 1,75, le 1ᵉʳ, le 10 et le 20 de chaque mois portent des
repères au pied de **chacun** des deux panneaux, et le panneau des températures
s'est fermé par un trait qui est un cadre et non un zéro. La page passe de 1212 à
**1472 px** en 1440 × 960 ; toutes les tables de contraste ont été remesurées et
le plancher est monté de 6,5 à **7,7:1**. Un test a par ailleurs attrapé une
ligne supprimée par accident dans le gabarit du dessin — le panneau des pluies
s'était effondré en silence, hauteur `NaN`, aucune barre.

→ [`application.md`](application.md)

---

## Le cumul des précipitations

Hors numérotation : une addition au graphe, demandée le 14 août 2026. **Un
troisième panneau** sous celui des pluies porte une courbe montante, avec sa
propre ligne de base et sa propre graduation.

**Un interdit écrit a été levé, un autre a failli l'être.**
[`application.md`](application.md) refusait « aucun cumul » parmi les
agrégations, et « jamais deux échelles verticales sur un même tracé ». La
première forme écrite posait la courbe sur les barres avec un axe à droite, et
levait les deux ; le cumul a reçu un panneau, et seule l'agrégation a été
arbitrée.

**Ce que la forme superposée avait pour elle était réel** : même grandeur, même
unité, même zéro que les barres, donc un facteur entre les deux échelles et
jamais un décalage. Ce qui l'a emportée est qu'un lecteur devait tout de même
savoir laquelle il regardait, et que rien ne le lui rappelait là où il posait les
yeux. Le panneau coûte de la hauteur de page — arbitrage déjà rendu dans le même
sens à l'arrivée du graphe — et ne demande rien.

**Elle laisse deux traits au dessin.** La courbe ne porte aucun point, un point
marquant une lecture et aucun pluviomètre ne relevant un cumul ; elle se coupe
sur une journée manquante, faute de quoi le trou dessinerait ce que dessine une
journée sèche. Écrits pour rendre la superposition honnête, ils valent tels quels
dans un panneau à part.

**La graduation des millimètres est devenue une fonction appelée deux fois**,
filets, nombres et pied compris — recopiée, c'eût été cinq lignes évidentes
tenues à deux endroits, ce que le prototype avait déjà produit sur cinq
comparaisons de seuils.

**Le rendu a de nouveau attrapé ce que les tests ne voyaient pas.** L'étiquette
du cumul affichait « 00,0 mm » là où elle disait « 100,0 mm » : la marge gauche
avait été mesurée sur « -10 °C », six caractères, et le total en demande huit.
Elle passe de 56 à **68 unités**. Même défaut qu'à 42 sur l'axe des pluies, deux
étapes plus tôt.

**La page passe de 1472 à 1705 px** en 1440 × 960, tables de contraste
remesurées. Le plancher monte de 7,7 à **7,9:1** et change de porteur :
l'étiquette de couture en été, poussée plus bas sur le dégradé, passe à 8,6 et
cède la place au dépliant de provenance. Rien à en conclure de général — un
déplacement le long d'un dégradé se renverse au changement de mise en page
suivant.

→ [`application.md`](application.md)

---

## Le futur servi partout, non corrigé hors grille

**Ce qui a changé.** Une recherche dépassant la prévision était refusée partout
où la grille n'a pas ses quatre nœuds, c'est-à-dire partout sauf la France
métropolitaine et ses abords. Elle est désormais servie, et la projection y est
rendue **telle que le modèle la produit**. Un lieu ne fait plus jamais refuser
une recherche ; seul ce qu'elle demande le peut.

**Ce qui a fait pencher, et ce n'est pas un argument de méthode.** Le motif du
refus reste vrai et la mesure ne bouge pas : le modèle est en retrait de 8 à 11
points de nébulosité, et trois des cinq classes de ciel en dépendent. Ce qui a
changé, c'est l'alternative, une fois chiffrée. Étendre la grille au monde au pas
de 0,5° demande de l'ordre de cent mille nœuds, soit **deux à cinq ans** de quota
au débit mesuré ; même desserrée à 3°, la collecte prend vingt à soixante jours.
Le refus n'était donc pas une attente, c'était un refus définitif hors de France.
Une réponse imparfaite et signalée a été préférée à une absence de réponse.

**Trois mesures faites à cette occasion**, sur les 438 nœuds servis, en comparant
chaque simplification à la correction par nœud. Aucune correction laisse 9,00
points d'erreur moyenne et fait changer de classe 21,1 % des jours secs ; un
décalage mensuel national, 3,68 points et 6,3 % ; une grille QDM desserrée à 3°,
1,68 point et 3,6 %. **Desserrer la grille coûte donc moins cher que simplifier
la méthode**, ce qui n'allait pas de soi : à budget de nœuds donné, la méthode
est gratuite, les deux requêtes par nœud rapportant la série journalière entière
quoi qu'on en fasse ensuite. Le seul levier sur le quota est le nombre de nœuds.

**Le décalage mensuel global a donc été envisagé, puis écarté.** Douze nombres
tirés des nœuds existants rattraperaient 59 % de l'écart au modèle brut, mesuré
en France, et supprimeraient la rupture visible à la couture. Ils ont été écartés
parce que rien ne prouve que le biais du modèle se transporte hors de France, et
qu'une correction non validée présentée comme une correction vaut moins qu'une
absence de correction déclarée. C'est un arbitrage du porteur du projet.

**Ce que le régime dégradé coûte, et il faut le dire.** Le passé et la quinzaine
à venir sont des observations et restent justes partout ; seul le segment simulé
est brut. La bande **s'éclaircit visiblement** là où la prévision passe la main à
la simulation. C'est l'artefact de couture que tout le reste du dispositif
combat, accepté ici en connaissance de cause, et **provisoire** : il tient
jusqu'à ce qu'une grille mondiale existe.

**Le garde-fou n'a pas été supprimé, il a été rendu intentionnel.** `pipeline.correct`
levait `UncorrectedFuture` dès qu'une journée simulée arrivait sans correction.
Le supprimer aurait suffi à servir le monde, et aurait fait disparaître avec lui
le cinquième verrou : une recherche française perdant sa correction par un défaut
aurait été servie en silence. Un mot-clé `outside_grid` porte donc la décision de
l'appelant, et la levée subsiste pour tout le reste. Le silence est demandé,
jamais subi.

**Ce qui a suffi à l'interface : rien.** L'avertissement qu'exige la règle 1 est
piloté par `has_simulated`, pas par la grille, donc il s'affiche hors couverture
comme ailleurs. Et `sources(grid)` rend une liste vide quand la grille est nulle,
donc le dépliant de provenance omet simplement son bloc de grille. Le contrat
portait déjà la distinction, `grid` valant `null` quand rien n'a corrigé.

→ [`application.md`](application.md), *Hors de la zone couverte*

---

## La chaleur humide

**Ce qui a été ajouté.** Une température humide sur chaque journée, dérivée du
point de rosée et de la température moyenne par la formule de Stull, celle-là
même qu'Open-Meteo applique ; et, sur les seules journées qui franchissent
26 °C ou 30 °C, un bandeau sur la carte. La règle, les seuils et ce qui les a
placés → [`regles.md`](regles.md) ; la forme à l'écran →
[`application.md`](application.md).

**Ce que cette étape a corrigé de ce qu'on supposait.** Trois choses.

La grandeur *est* servie par Open-Meteo, contrairement à ce qu'on aurait pu
croire d'une variable aussi dérivée — mais nulle côté Climate, comme le
`weather_code`. Le piège de l'absence silencieuse n'est donc pas une singularité
de ce dernier : c'est le comportement de l'API pour **toute** variable dérivée,
`apparent_temperature` comprise. Le §4 de [`donnees.md`](donnees.md) le dit
désormais dans ces termes.

Le maximum journalier paraissait la grandeur à servir, puisque c'est de lui que
parle la littérature. Il ne se reconstruit qu'à 0,8 °C près depuis des agrégats
journaliers, contre 0,05 pour la moyenne — et la moyenne s'est révélée la
meilleure grandeur pour une autre raison, indépendante de sa précision : la
chaleur éprouve par la dose et non par la pointe, et une moyenne sur
vingt-quatre heures contient la nuit.

Enfin, **ajouter une variable a cassé le rejeu d'un dossier gelé.** Replier le
point de rosée sous `TEMPERATURE_VARIABLES` a transformé la relecture du cache de
l'étape 2 en erreur : une mesure cessait d'être reproductible pour raccourcir une
liste de constantes. Deux listes distinctes, et deux tests qui les épinglent.

**Ce qui reste.** L'humidité du modèle climatique n'est pas calibrée, et c'est le
même problème que celui de l'étape 4, pris un cran plus tôt : la formule est
réglée, c'est l'entrée qui ne l'est pas. Un seul point mesuré, et une sensibilité
qui rend le second seuil fragile. Le détail et ce qu'il faudrait mesurer →
[`regles.md`](regles.md), *L'humidité reste à calibrer*.

---

## Ce qui reste calé sur une base mince

Aucune décision scientifique n'est en attente, mais trois points méritent d'être
réexaminés le moment venu :

- **le seuil de neige de 1,5 °C**, établi sur deux sites et une seule saison ;
- **les deux seuils de chaleur humide**, dont le second varie d'un facteur trois
  sous le biais d'humidité plausible du modèle, lequel n'est mesuré qu'en un
  point. C'est le seul de ces points qui appelle une collecte plutôt qu'une
  relecture ;
- **l'ensemble des mesures du projet**, qui reposent sur dix sites.
