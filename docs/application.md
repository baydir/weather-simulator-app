# Application — architecture, affichage, grille

Comment le site est bâti et ce qu'il montre. Les règles qu'il applique →
[`regles.md`](regles.md) ; ce qu'il refuse de promettre →
[`projet.md`](projet.md).

---

## Nature du site

Un site grand public volontairement restreint : **une page d'accueil portant le
formulaire, une page de résultats**. Des pages explicatives viendront plus tard,
statiques et peu interactives.

Le formulaire demande un lieu et une période, **et la période de deux façons** :
une plage de dates, ou une saison et une année → [la section qui le
décrit](#deux-façons-de-poser-la-même-question). La seconde ne produit rien que
la première ne produise : elle écrit les mêmes deux dates, dans la même URL.

L'accueil n'annonce pas le site par son nom. Il pose une question qui tourne —
« Pourrais-je faire pousser des tomates à Montpellier en 2050 ? » — et met la
promesse dessous. Un nom dit comment la chose s'appelle et rien de ce à quoi
elle sert ; le nom reste dans le titre de l'onglet, qui est l'endroit où un nom
se lit vraiment. Derrière, un couchant en dégradé, et la chaleur qui en monte.
Le détail de ces choix, et les contrastes mesurés qui les bornent →
[la section *Le ciel de l'accueil*](#le-ciel-de-laccueil).

Objectif de conception : simple d'abord, extensible ensuite. Chaque brique est
pensée pour être remplacée sans que les autres bougent.

---

## Répartition entre client et serveur

**Les données sont récupérées par le navigateur**, géocodage compris. Le motif
n'est pas le volume — une plage de 90 jours pèse 4 Ko — mais le fait que **les
limites d'Open-Meteo s'appliquent par adresse IP** : un serveur qui
interrogerait les API concentrerait toute l'affluence sur une seule adresse et
atteindrait la limite immédiatement. Nous l'avons atteinte depuis un seul poste
pendant les travaux préparatoires.

Le géocodage passe par l'API dédiée d'Open-Meteo, non par Nominatim, dont les
conditions d'usage proscrivent les usages intensifs.

**Le navigateur dérive ce dont le serveur ne détient pas de version** : mise en
forme, repères de lecture, ordonnancement, cache. Toute grandeur affichée, et
toute règle dont dépend une grandeur affichée, est calculée en Python, côté
serveur — la classe de ciel doit être produite par une fonction unique, et le
prototype initial montre ce qu'entraîne sa duplication entre JavaScript et
Python. Le critère n'est pas la difficulté de la tâche, c'est le double
exemplaire → [`CLAUDE.md`](../CLAUDE.md), règle 3.

Le navigateur poste les données brutes ; le serveur valide les entrées, applique
la correction de nébulosité, le bloc de transformation et la classe de ciel, et
renvoie le JSON journalier. Sans état et sans base de données, il monte en charge
par simple multiplication des instances, derrière un frontend statique servi par
CDN.

### Une recherche se fait en deux appels

**Décider quoi demander, le serveur en détient une version** — et pas une version
décorative : `/api/days` rejoue le plan pour vérifier que les payloads reçus
correspondent bien à la recherche. Le refaire dans le navigateur serait donc un
second exemplaire de ce découpage, avec ce qu'il faut pour diverger : couper la
plage à aujourd'hui, choisir les modèles, savoir que le passé ancien coûte deux
requêtes parce que la source se choisit par variable. **S'y ajoute une raison de
correction** : la coupure se fait à la date du jour prise sur l'horloge du
serveur, quand celle du navigateur est celle du visiteur.

Le serveur décide donc et remet des **URL déjà construites**, requête encodée
comprise ; le navigateur appelle `fetch` sur chacune.

| Appel | Entrée | Sortie |
|---|---|---|
| `POST /api/plan` | lieu et plage | `today`, et la liste `{id, url}` des requêtes à exécuter |
| `POST /api/days` | les mêmes, `today` renvoyé tel quel, les payloads bruts | la série journalière classée |
| `GET /api/config` | — | gabarit de géocodage, bornes de couverture, plage maximale, bornes de l'échelle de température |

`today` circule du premier appel au second pour que les deux moitiés s'accordent
sur l'endroit où l'observé s'arrête. Il est **vérifié à un jour près** de
l'horloge du serveur, et la recherche est refusée sinon : au passage de minuit,
la coupure entre ce qui a eu lieu et ce qui pourrait avoir lieu s'est déplacée.

`/api/config` existe pour que la plage maximale soit **servie et non recopiée** :
la borne de 92 jours s'applique dans l'interface comme dans l'API, et une
seconde copie divergerait. **Les huit bornes de l'échelle de température y sont
passées pour le même motif** : le graphe gradue son axe dessus, et l'échelle
écrite une seconde fois en JavaScript est exactement la duplication que la
règle 3 vise. Ce qui voyage est l'échelle, jamais les teintes — elles restent
dans la feuille de style, comme le pictogramme reste hors du contrat.

Les trois appels sont sans état, de sorte que la propriété que défendait la
règle antérieure d'un endpoint unique — monter en charge en multipliant les
instances — reste entière.

**La requête IFS est demandée en chevauchement.** La borne entre les deux passés
se lit dans la réponse des réanalyses ; elle n'est donc pas connue au moment de
construire le plan. Plutôt qu'un second aller-retour, ou qu'une latence codée en
dur que [`donnees.md`](donnees.md) proscrit, IFS est demandé sur toute la portion
de la plage postérieure à 2017, et **la réanalyse l'emporte à l'assemblage
partout où elle a servi**. La série produite est identique ; le coût est une
requête de plus, de 92 jours au plus, sur toute plage touchant 2017.

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
    pages/         home.html, results.html — HTML statique, aucun gabarit
    static/css/    style.css, une feuille bâtie sur des variables
    static/js/     fetch.js, i18n.js, present.js, bounds.js, band.js, chart.js,
                   series.js, season.js, dom.js, prompt.js, home.js, results.js
```

Dans `api/`, `plan.py` porte **à la fois la façon de demander chaque segment et
la façon de le relire**. Les deux tiennent dans le même objet à dessein : un plan
et une lecture en désaccord sur les variables qu'une requête portait échoueraient
de la manière la moins visible qui soit — une colonne silencieusement absente.

La séparation entre `domain` et `transform` est délibérée : `domain` porte les
règles arrêtées et n'a pas vocation à bouger, `transform` est le point de
maîtrise sur les données, appelé entre la correction et l'affichage, et ne
transforme rien par défaut.

`pages/` et non `templates/` : le second mot annonce un gabarit exécuté par le
serveur, quand ce document réclame par ailleurs un frontend statique servi par
CDN. Un CDN n'exécute pas de gabarit ; les pages sont donc des fichiers, et l'API
les sert par un montage **conditionnel** — `web/` absent, elle démarre quand même.

**La frontière entre modules ne s'est pas posée là où on l'attendait.** Elle ne
sépare pas le rendu du reste, comme le laissait entendre un `render.js`, mais
**ce qui se vérifie sans navigateur de ce qui n'existe que dans la page** :
`present.js` (formatage et arrondis), `bounds.js` (les refus du formulaire),
`band.js` (la construction de la bande), `chart.js` (la géométrie du graphe),
`series.js` et `season.js` tournent sous `node --test` ; `home.js` et
`results.js` ne portent que le câblage. C'est la même frontière qui garde une
migration possible.

**`season.js` porte une table et deux lectures, et c'est la règle 3 appliquée à
l'intérieur d'un fichier.** `seasonOf` prend une date et rend une saison, pour
que la page de résultats trouve son sol ; `rangeOf` prend une saison et rend deux
dates, pour que le formulaire puisse la demander par son nom. Écrire « 21 juin au
20 septembre » une seconde fois pour le second sens serait le double exemplaire
que la règle vise, et la règle ne se soucie pas de ce que les deux copies
tiennent dans le même module — cinq lignes évidentes divergent aussi sûrement
qu'une règle savante. Les bornes sont donc déclarées une fois et les deux
lectures la parcourent, **dont un test referme le cycle** : demander une saison
et relire ce qui revient doit rendre la même saison, sur les quatre et sur les
deux hémisphères. Le jour où les deux lectures divergeraient, le formulaire
demanderait un été et la page peindrait un hiver.

Une propriété de cette table mérite d'être sue avant d'y toucher : **toutes les
bornes tombent sur le 21**, et `rangeOf` s'y appuie pour prendre la veille de la
suivante — le 20 du même mois, sans arithmétique de date ni fuseau à lire. Une
borne déplacée au 1ᵉʳ rendrait un jour zéro, en silence ; un test l'interdit.

**`series.js` ne porte qu'une fonction, et c'est une leçon de la règle 3 appliquée
à l'intérieur du navigateur.** La bande et le graphe doivent marquer la même
couture au même jour ; tenue à deux endroits, cette règle diverge comme
n'importe quelle autre. Le serveur n'en détient aucune version — l'origine de
chaque journée voyage dans le contrat, et ce qui se dérive ici est seulement
*lequel* des passages mérite une marque.

**`prompt.js` la montre autrement**, et c'est pourquoi la question qui tourne a
son module plutôt qu'un coin de `home.js` : ici la frontière ne passe pas entre
deux fichiers mais **à l'intérieur d'un seul**. `next` est de l'arithmétique et
se teste sans horloge ni DOM ; `rotate` est une minuterie posée sur une page et
ne se teste pas. Séparer les deux à l'intérieur du module est ce qui rend la
partie vérifiable vérifiable.

Les questions elles-mêmes sont tenues **par deux tests et non par un**, et le
partage mérite d'être su avant d'en écrire une nouvelle : `prompt.test.js`
vérifie qu'il y en a, que chacune pose bien une question, et que la promesse
garde son verbe — « Simulez », l'un des trois termes que la règle 1 retient ;
`present.test.js` porte la liste des mots proscrits et signale la fautive sous
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
La borne valait 90 et disait « une saison » par approximation : elle amputait de
deux jours les deux plus longues, ce qui n'était sans conséquence que tant qu'on
ne pouvait pas demander une saison par son nom. La valeur ne s'écrit qu'à un
endroit, `MAX_DAYS`, et voyage par `/api/config` — jusqu'au libellé du refus, qui
l'a écrite en dur jusqu'ici et aurait continué d'annoncer 90.

Chaque journée porte un pictogramme, les températures minimale et maximale, le
cumul de précipitations et la vitesse de vent maximale.

**Sous la bande, les mêmes journées dessinées** : deux courbes de températures et
les précipitations en barres, sur toute la plage d'un seul regard. Ce que ce
second bloc apporte et ce qu'il n'a pas le droit de calculer →
[la section qui lui est consacrée](#le-graphe-sous-la-bande).

**Deux choses sont mises en avant : l'allure du ciel et les deux
températures.** Le pictogramme d'abord, les degrés dessous, en corps supérieur
au reste. C'est ce qu'on vient chercher sur un bulletin, et une carte lue d'un
coup d'œil, parcourue par dizaines, a besoin d'un point d'entrée pour le regard.

Les précipitations et le vent suivent, **à poids égal entre eux** : aucun des
deux n'est relégué par rapport à l'autre, et le vent en particulier garde la
taille et la graisse des précipitations.

La règle antérieure voulait les quatre mesures de même rang. La bande construite
l'a démentie à l'usage : à poids égal, rien ne se détache et la carte se lit
comme un tableau.

**La maximale au-dessus, la minimale en dessous**, empilées et non côte à côte.
La règle antérieure les posait sur une ligne, « minimale à gauche, maximale à
droite », dans l'ordre où [`projet.md`](projet.md) et le README écrivent la
paire : « 21 °C / 39 °C ». La maquette de la page de résultats les empile et
mène par la maximale, qui est le chiffre qu'une lecture d'été vient chercher ;
c'est aussi ce qui libère la place de les composer en grand sur une tuile
étroite. **Les deux textes qui écrivent la paire dans l'autre sens n'ont pas été
touchés** : ils énoncent une plage en prose, pas une carte, et « 21 °C / 39 °C »
s'y lit du plus petit au plus grand comme on écrit un intervalle.

L'ordre de lecture suit l'œil : un lecteur d'écran entend désormais la maximale
en premier, et `tests/js/band.test.js` fige cet ordre. Le signe degré accompagne
chacune des deux — c'est ce que l'empilement coûte, là où une ligne unique en
faisait servir un seul pour les deux.

**Les températures ne portent pas de libellé.** Deux nombres près d'un signe
degré n'en demandent pas. Ce que la carte doit dire, en revanche, c'est laquelle
est la maximale — et à l'écran **seule la position l'indique désormais**, les deux
nombres partageant une même échelle de couleur depuis qu'elle existe : à 22 °C,
une maximale et une minimale portent le même aplat. Ce qui n'est une information
ni pour un lecteur d'écran, ni pour qui ne voit pas l'ordre. Chacune est donc
nommée pour qui ne la voit pas.

**Les libellés des deux autres mesures sont sortis de l'écran, pas du
document.** La carte porte « 4,8 mm » et « 31 km/h » nus : les unités suffisent à
l'œil. Un lecteur d'écran n'a pas d'unités sur quoi s'appuyer, et le `dt` reste
donc dans le document, hors champ — c'est ce qui garde « vent maximal » attaché
au nombre que ce document interdit de lire comme une moyenne. La classe de ciel
écrite, qui double le pictogramme, suit la même règle et pour la même raison.

**Le vent moyen n'est pas affiché.** La question s'est posée deux fois. Le
présent document portait d'abord les deux vents, [`projet.md`](projet.md) la
carte sans aucun ; la première bande construite a tranché à l'usage : cinq
mesures sur une carte destinée à être lue d'un coup d'œil, et parcourue par
dizaines, sont plus qu'elle n'en porte. La grandeur reste dans le contrat JSON,
où rien ne coûte de la garder.

| Classe | Contrat JSON | Pictogramme |
|---|---|---|
| Dégagé | `clear` | ☀️ |
| Nuageux | `cloudy` | ⛅ |
| Couvert | `overcast` | ☁️ |
| Pluie | `rain` | 🌧️ |
| Neige | `snow` | 🌨️ |

**Une sixième valeur circule : l'absence de classe.** Une journée dont il manque
une variable nécessaire ne reçoit pas de classe, et le contrat porte `null`
plutôt qu'une valeur inventée. L'interface doit prévoir cette carte-là.

Les émojis conviennent à une première version : disponibles partout, sans
ressource à charger. Deux points en découlent — **le contrat JSON transporte la
classe, jamais le pictogramme**, de sorte qu'un passage à des icônes dessinées
ne touchera que l'affichage ; et chaque pictogramme s'accompagne d'un équivalent
textuel, l'émoji seul n'étant pas accessible aux lecteurs d'écran.

**Le vent maximal ne doit pas être libellé « rafale ».** `wind_speed_10m_max`
est le plus fort vent *établi* de la journée. Une rafale est autre chose et vaut
couramment le double : 36,8 km/h contre 14,4 km/h à Pontarlier en juin 2024. Le
libellé retenu est « vent maximal ». **Ni « vent » seul**, désormais que c'est le
seul affiché : la carte se lirait comme une moyenne, et le chiffre serait faux
d'un tiers.

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
portant le pictogramme de la pluie serait une contradiction visible à l'écran,
là où « 0,4 » et « 1,2 » se distinguent. Sur les degrés et les kilomètres par
heure, rien ne dépend du dixième et il n'ajoute rien à la lecture — la forme
retenue est celle qu'emploie déjà [`projet.md`](projet.md) : « 21 °C / 39 °C,
ciel dégagé, 0 mm ».

### Ce que l'interface ne calcule pas

Aucune moyenne de période, aucun comptage de journées de pluie, aucun cumul,
aucun extrême de la plage. Ce sont des agrégations, et une agrégation faite à
l'affichage relève de la même validation que l'arrondi ci-dessus. **L'interface
montre les journées, et rien au-dessus d'elles.**

La règle antérieure disait « la bande » ; le graphe l'a élargie sans la changer.
Une courbe est **une marque par journée** et n'agrège rien : ce qu'elle ajoute
est la forme de la période, que l'œil compose et que l'interface ne calcule pas.
La distinction porte, et elle est vérifiée par un test qui refuse par défaut tout
texte du graphe n'étant ni un titre, ni une graduation, ni un repère de lecture —
c'est ainsi qu'a été retirée l'étiquette qui écrivait le plafond des
précipitations, laquelle nommait la journée la plus arrosée, c'est-à-dire un
extrême de la plage.

**Le cadrage des deux axes est la seule chose que le graphe décide**, et les deux
relèvent de la validation qu'exige la règle 4 → [la section sur le
graphe](#le-graphe-sous-la-bande).

Une ligne de synthèse est envisagée dans [`idees.md`](idees.md), mais adossée à
la comparaison au climat ancien, non retenue pour la première version.

**Tout écran affichant une journée simulée porte un avertissement explicite et
visible** → [`projet.md`](projet.md). Une recherche qui ne dépasse pas la
prévision n'en porte pas : l'avertissement y serait faux. La bascule se lit sur
`has_simulated`, jamais sur un comptage de journées.

---

### Le ciel de l'accueil

L'accueil porte un couchant, **écrit en dégradé CSS** à partir de onze couleurs
échantillonnées dans la photographie de référence. La photographie n'ayant aucun
détail — c'est un lavis —, le dégradé la reproduit pour zéro octet et reste net à
n'importe quelle densité d'écran, là où une image de 540 px de large étirée sur
un écran large serait floue.

**Il est ancré au document, non à la fenêtre**, et ce point n'est pas cosmétique.
Fixé à la fenêtre, la couleur sous un élément donné dépend de la hauteur d'écran
du lecteur : mesuré sous l'avertissement, le fond allait de `#d89470` sur une
fenêtre de 700 px à `#124a73` sur une de 2000. Aucune encre ne sert la bande
claire et le bleu profond. Ancré au document, c'est `#e28f5b` à toutes les
hauteurs, et l'encre se choisit au lieu de s'espérer.

**Aucun voile n'est posé dessus.** Un assombrissement progressif a été essayé
puis retiré : il achète du contraste en salissant la photographie, ce qui est la
mauvaise monnaie. La lisibilité se paie en encre — l'encre secondaire est
éclaircie sur cette page, et l'avertissement passe en brun brûlé parce qu'il est
le seul texte à tomber sur la bande claire quelle que soit la fenêtre.

Contrastes mesurés sur le rendu, fenêtre 1440 × 900, par
[`scripts/ink_contrast.py --page home`](../scripts/ink_contrast.py). **Le
défilement n'entre plus dans la mesure** : la sonde lit les positions en
coordonnées de document, comme le dégradé y est ancré. **Trois colonnes, une par
état du formulaire** : la page s'ouvre sans panneau, et la hauteur du formulaire
change selon celui qu'on déplie. Sur cette page, la hauteur *est* la lisibilité.

| Texte | rien d'ouvert | plage de dates | saison entière |
|---|---|---|---|
| la question | 11,2:1 | 11,2:1 | 11,2:1 |
| la promesse | 7,8:1 | 7,8:1 | 7,8:1 |
| l'étiquette *Lieu* | 7,8:1 | 7,8:1 | 7,8:1 |
| le champ *Lieu* | 7,0:1 | 7,0:1 | 7,0:1 |
| la bande choisie | — | 9,7:1 | 7,7:1 |
| la bande au repos | 9,7:1 | 7,7:1 | 8,2:1 |
| l'étiquette *Du* | — | 5,1:1 | — |
| le champ *Du* | — | 4,6:1 | — |
| l'étiquette *Saison* | — | — | 5,1:1 |
| le champ *Saison* | — | — | 4,6:1 |
| le bouton | — | 7,0:1 | 7,0:1 |
| l'avertissement | 5,9:1 | 5,9:1 | 5,9:1 |

**Ces chiffres se remesurent à chaque changement de mise en page**, et pas par
excès de zèle : resserrer la page a fait glisser le formulaire sur du bleu plus
clair et emporté l'étiquette *Lieu* à 4,4:1, sous le seuil. Ici, mise en page et
lisibilité sont la même question. La table est désormais **imprimée par une
commande** et non relevée à la pipette, ce qui est ce qui a permis de la
remesurer sérieusement pour la première fois.

**Ce que la mesure par commande a arbitré, trois fois.** Les deux bandes de mode
coûtent au formulaire une hauteur qu'il n'avait pas, et le dégradé étant ancré au
document, tout ce qui les suit glisse vers le bleu pâle : les premiers essais
faisaient tomber les champs de six dixièmes de rapport. Trois décisions en
découlent, et aucune n'aurait été prise sans le chiffre.

- **Côte à côte, non empilées.** Deux bandes pleine largeur coûtaient quelque
  96 px, une paire en coûte 45.
- **Plus basses que le bouton d'envoi** — 12 px de rembourrage contre 20. Elles
  choisissent la question, lui la pose.
- **Le reste est repris sur l'air du haut de page**, dont la respiration passe de
  10 vh à 6 vh. C'est le seul endroit de la page où la hauteur n'achète rien
  d'autre que du vide, et les champs étaient ce qui s'approchait le plus de la
  bande pâle.

Plancher à **4,6:1**, contre 4,2:1 avant ce travail, et toutes les lignes sont
égales ou meilleures.

**Une valeur a bougé sans que la mise en page l'explique**, et il faut le dire
plutôt que la recouvrir. Le bouton sortait à 7,5:1 et la commande en lit
**7,0**, dont 6,7 sur la géométrie d'avant les bandes. La méthode n'est pas en
cause — les cinq autres lignes publiées se reproduisaient au dixième, et la table
de la page de résultats se reproduit sur ses quarante-huit cellules —, donc
l'écart tient à une géométrie antérieure ou à un relevé manuel fait autrement.
C'est la valeur mesurée qui est publiée.

**La bande située entre 50 % et 65 % du dégradé ne porte aucune encre.** Le fond
y va de `#4b688b` à `#677390`, et à ces clartés le noir pur plafonne à 4,0:1
quand l'ivoire de la page atteint 4,2. Ce n'est donc pas un choix de ton, c'est
une hauteur : le seul remède est que le formulaire n'y descende pas. C'est ce qui
avait déjà fait éclaircir l'encre secondaire deux fois ; les étiquettes du
formulaire prennent maintenant l'encre pleine, leur hiérarchie restant portée par
leur forme — onze pixels, capitales, interlettrage.

**Les autres tailles de fenêtre ne passent pas, et c'est antérieur à ce
travail.** La table n'a jamais été publiée que pour 1440 × 900, faute d'outil
pour en mesurer d'autres. Planchers relevés, avant et après :

| Fenêtre | avant les bandes | après |
|---|---|---|
| 1440 × 900 | 4,2:1 | **4,6:1** |
| 1280 × 720 | 3,2:1 | 3,1:1 |
| 1440 × 1200 | 3,7:1 | 3,7:1 |
| 390 × 844 | 2,9:1 | 3,1:1 |

Le seul déplacement est **un dixième perdu en 1280 × 720**, une géométrie qui
échouait déjà et échoue encore : la seule fenêtre réglée est celle sur laquelle
la table est publiée. Sur une fenêtre haute le
plancher est **l'avertissement**, à 3,7:1 — la phrase que la règle 1 rend
non négociable, portée par la seule ligne de la page qui ne puisse pas se
déplacer. Le remède touche la composition de la page, documentée et arbitrée
ailleurs dans ce fichier : **il reste à décider.**

**Et le rapport ne suffit pas.** L'avertissement était mesuré à 5,9:1 en italique
et restait pénible à lire : un rapport compare les couleurs de deux surfaces et
ne sait rien de la finesse des traits entre elles. C'est ce qui a fait renoncer à
l'italique, non le contraste.

La chaleur qui monte de la bande basse **n'est pas le filtre SVG de déplacement**
avec lequel elle a d'abord été écrite. Rastérisé pixel par pixel et par image, il
faisait tomber 120 images par seconde à 12 sur un écran de 2560 px ; ni le
masquer ni le calculer en demi-résolution n'y changeait rien. Déplacer les pixels
d'un lavis ne fait que changer un peu la couleur de chacun, ce qu'une bande
translucide qui passe dessus produit aussi : sans détail à déformer, l'opération
chère et la gratuite convergent. Mesuré après : 121 images par seconde.

Le miroitement s'arrête entièrement sous `prefers-reduced-motion`, comme la
rotation de la question.

### Le formulaire sur le ciel

Trois pièces du formulaire ont été reprises après coup, et pour le même motif à
chaque fois : **elles avaient été dessinées contre le papier sombre, où le fond
est une constante.** Sur un dégradé le fond est une variable, et ce qui tenait a
cessé de tenir.

**Le bouton ne porte plus de fond opaque.** Il était `#4a443a`, une couleur de la
palette du papier ; sur le couchant il se lisait comme un morceau de la page de
résultats collé sur la photographie — le seul objet opaque d'une page dont toute
l'habitude est que rien n'est dans une boîte. Il porte désormais un brun brûlé à
45 %, que le ciel traverse, et un filet d'ivoire à 22 %. **Le filet est une ombre
interne et non une bordure** : une bordure ajouterait deux pixels de hauteur, et
sur cette page un bouton plus haut pousse l'avertissement sur une autre zone du
dégradé — la ligne du tableau ci-dessus a été corrigée de 7,8 à 7,5, et c'est la
seule qui ait bougé, la géométrie n'ayant pas changé d'un pixel. Le survol
**fonce** le fond au lieu de l'éclaircir, de sorte que le rapport monte en
approchant et ne descend jamais.

Une variante sans fond, filet seul, a été mesurée puis écartée à **3,7:1** : un
bouton transparent hérite du contraste de ce qu'il y a derrière, et à cet endroit
du ciel c'est perdu d'avance.

**La liste des lieux flotte au-dessus de la page au lieu de la pousser.** Dans le
flux, elle s'insérait entre le champ *Lieu* et les dates et les faisait descendre
dès la deuxième lettre tapée : les champs que le lecteur venait de regarder
glissaient sous ses yeux. Une liste de correspondances est une réponse passagère
à ce qu'on est en train d'écrire, pas une nouvelle partie du formulaire, et elle
ne doit coûter aucune hauteur — mesuré depuis : zéro.

**Elle est opaque, et c'est la seule surface du site qui le soit.** Ce qu'elle
recouvre, ce sont les deux champs de date, et lire un nom de commune au travers
de « 12/08/2026 » est pire que de ne pas afficher la liste du tout. Une opacité
de 97 % a été essayée : la date en dessous ressortait à 1,06:1 contre le panneau,
ce que le rapport déclare négligeable et que l'œil lit sans peine. **Un rapport
de contraste est construit pour du texte sur un fond et n'a rien à dire de six
niveaux d'écart au fond des noirs** — c'est le même avertissement que porte plus
haut le renoncement à l'italique, sous une autre forme. Le panneau est donc
plein, et il prend `#27030a`, le dernier arrêt du dégradé : la couleur dans
laquelle le couchant se termine, ramenée au premier plan. Cette valeur est
**servie et non recopiée**, sortie du dégradé dans une variable que les deux
lisent ; recopiée, le panneau garderait l'ancienne teinte le jour où la
photographie serait rééchantillonnée.

**Les champs de date ont dû rendre visible où l'on se trouve dans la date.** Le
navigateur marque le segment que la frappe suivante changera, et il le marque
avec une couleur système : dans Firefox un bleu, sur un champ posé sur un ciel
bleu. Mesuré, ce marquage ne se détachait du champ qu'à **1,54:1** — assez peu
pour que le défaut soit rapporté comme une impossibilité de remplir les dates,
alors que le champ prenait chaque touche. **Rien n'était bloqué ; c'est le retour
qui manquait**, et le symptôme ressemblait à s'y méprendre à une panne.

La page ne peut pas choisir cette couleur, et deux tentatives sont consignées ici
pour qu'elles ne soient pas refaites : `::selection` est inerte — Firefox ne fait
pas passer un segment de date par là, deux rendus à profil neuf sortent
identiques au pixel — et `accent-color` l'est également. Ce qui s'atteint, c'est
ce qui entoure la marque. `color-scheme: light` sur ces champs demande au système
sa marque claire, le bleu vif plutôt que le bleu-vert éteint ; et le champ prend
un fond sombre **pendant l'édition seulement**. Ensemble : **4,3:1 dans Firefox,
3,3:1 dans Chromium**. Au repos, une date reste ce qu'est tout champ de cette
page, une ligne de texte sur un filet.

**Deux conséquences se paient, et la seconde n'est pas réparable.** L'icône du
calendrier de Chrome devient noire sous le schéma clair ; une inversion la rend à
l'ivoire. Mais le calendrier natif, lorsqu'il s'ouvre, s'affiche désormais en
clair : la marque de segment et le calendrier viennent du même réglage et ne se
séparent pas. L'échange est assumé — le calendrier est un passage bref, le
repérage dans la date un geste constant.

#### Deux façons de poser la même question

Le formulaire demande une période de deux manières, **exclusives et
basculables** : une plage de dates, ou une saison assortie d'une année. La
seconde existe parce que la question que ce site pose porte le plus souvent sur
une saison — « un été à Montpellier en 2050 » — et que la première obligeait à
savoir que l'été ouvre le 21 juin.

**La page s'ouvre sans aucun des deux, et c'est un troisième état de plein
droit.** L'accueil montre un lieu et deux bandes ; le panneau ne se déplie qu'une
fois l'une pressée. Étaler une plage que personne n'a demandée revenait à
répondre avant d'avoir posé la question — et à laisser partir, si le visiteur
allait droit au bouton, une quinzaine par défaut qu'il n'avait pas regardée.
**Le bouton d'envoi est donc replié avec les panneaux.** La touche Entrée reste
un chemin d'envoi qu'aucun bouton caché ne ferme, et le formulaire la refuse
explicitement tant qu'aucune période n'a été choisie.

**Le mode saison écrit dans les deux champs de date ; il ne les remplace pas.**
C'est ce qui fait que la page de résultats n'a rien eu à apprendre : ni le
sélecteur de saison ni celui d'année ne porte d'attribut `name`, donc aucun des
deux n'est soumis, et l'URL reste les mêmes cinq paramètres — `lieu`, `lat`,
`lon`, `debut`, `fin`. Une saison est un intervalle, et l'API n'a jamais rien
demandé d'autre.

**La bascule est deux boutons, non un groupe de radios**, et pour la même raison
en sens inverse : des radios ne se groupent qu'en partageant un `name`, et un
`name` est précisément ce qu'un formulaire GET met dans l'adresse.

**Deux bandes, dans la grammaire du bouton d'envoi et à un rang en dessous.**
Elles portent un fond, jamais un filet seul — la variante transparente avait été
mesurée à 3,7:1 sur le bouton d'envoi et écartée, un bouton sans fond héritant du
contraste de ce qu'il y a derrière. Mais elles le portent **plus léger**, à 24 %
contre 45 : à leur hauteur le brun se compose sur du bleu et non sur le couchant,
et à 45 % elles lisaient comme deux dalles collées sur la photographie, ce que le
bouton d'envoi avait justement renoncé à être. Choisir une bande l'approfondit
jusqu'au fond du bouton et lui donne un filet d'encre pleine : le rapport monte
en s'approchant et ne descend jamais, comme au survol du bouton.

**Le repli est écrit dans le script, pas dans le balisage.** La page est livrée
les deux panneaux ouverts et le bouton visible ; c'est `home.js` qui les ferme au
chargement. Dans l'autre sens, un visiteur sans JavaScript rencontrerait un
formulaire sans période et sans moyen d'en révéler une — là, il retrouve
exactement le formulaire d'avant la saison.

**L'année est celle où la saison commence**, pour les quatre. Cela ne se voit que
sur l'hiver, seule saison à cheval sur deux années civiles : « hiver 2029 » va du
21 décembre 2029 au 20 mars 2030. L'usage français laisse le tour ambigu ; la
règle retenue est uniforme. La contrepartie est que l'hiver 2050 finirait en
2051, hors couverture — la liste des années est donc construite à partir des
bornes servies par `/api/config`, et cette année-là n'y figure pas plutôt que
d'être offerte pour être refusée.

**Sous l'équateur, la saison demandée est celle du lieu.** « Été » à Santiago va
du 21 décembre au 20 mars. C'est le même saut que fait déjà le sol de la page de
résultats, pris en sens inverse — sans quoi une recherche intitulée « été »
ouvrirait une page peinte en hiver.

**Quitter le mode saison ne remet pas les dates par défaut.** La plage qu'une
saison vient de produire est une plage parfaitement bonne à ajuster à la main, et
l'effacer jetterait ce que le visiteur vient de demander.

### La saison de la page de résultats

La page de résultats était une bande de cartes sur papier plat. Elle porte
désormais **le sol de la saison sur laquelle porte la recherche**. L'été vient de
`design/summer_result.svg` et la page a été dessinée sur lui ; les trois autres
en dérivent.

**La saison se compte, elle ne se lit pas à une extrémité.** Le navigateur
parcourt la plage jour par jour et retient celle qui en tient le plus. Trois
arbitrages complètent la règle :

- **Bornes astronomiques**, 21 décembre au 20 mars et ainsi de suite — les dates
  sur lesquelles le visiteur a été interrogé. Elles glissent d'un jour selon
  l'année dans le ciel et pas ici : un sol qui changerait de teinte le 20 mars
  une année et le 21 la suivante répondrait à une question que personne ne pose.
- **Saisons inversées sous l'équateur.** La latitude voyage dans l'URL à côté des
  dates, et janvier à Santiago est un été. Une latitude illisible retombe sur
  l'hémisphère nord — le calendrier, plutôt qu'une erreur.
- **À égalité parfaite, la saison où la plage se termine.** Une plage se lit vers
  l'avant.

**La règle tenait un raccourci qu'elle a perdu, et le comptage n'en dépendait
pas.** À 90 jours, une plage ne pouvait toucher que deux saisons, l'hiver — la
plus courte — en faisant exactement 90. À 92, elle peut en toucher trois : un
jour d'automne, un hiver entier, un jour de printemps. Aucune ligne n'a changé,
parce que le comptage n'a jamais compté que des journées ; c'est la justification
qui avait fait de cette borne une propriété du calcul, alors qu'elle n'en était
qu'une commodité.

**La saison demandée et la saison peinte se rejoignent, et ce n'est pas une
coïncidence.** Depuis que l'accueil sait demander « été 2029 », deux chemins
mènent à un sol : le comptage décrit ici, et le choix du visiteur. Ils
s'accordent parce que `rangeOf` et `seasonOf` lisent la même table en sens
inverse — y compris sous l'équateur, où l'un traduit vers l'hémisphère nord et
l'autre en revient. Un test le vérifie plutôt que de l'espérer →
[l'organisation du code](#organisation-du-code).

**Ce comptage se fait dans le navigateur, et la règle 3 n'y voit rien à redire** :
le serveur n'en détient aucune version, il n'y a donc pas de second exemplaire.
C'est de la mise en forme dérivée de deux dates déjà présentes dans l'URL, au
même titre que le repérage des mois dans la bande. La saison est posée sur le
`body` avant le premier rendu, et **avant les quatre allers-retours** : une
recherche refusée porte son sol comme une autre.

**L'été est relevé, les trois autres sont dessinés.** Le dégradé de la maquette
est une image matricielle encastrée dans le fichier Inkscape : il a été décodé
puis échantillonné tous les dix pour cent, ce qui donne onze arrêts. Il n'existe
pas de maquette pour les trois autres, et leur inventer onze arrêts serait une
précision qui ne mesurerait rien — ils en portent **cinq**, choisis pour la
teinte du milieu. Cet arrêt central est tout le travail : blanc à marron
interpolé en sRVB passe par un beige sale, blanc à bleu par un gris mort. À deux
arrêts, ces sols seraient des lavis de rien.

```
été       0 % #fafdea   30 % #fe9e52   60 % #fd3a0c   90 % #810402
         10 % #f9deb1   40 % #ff7b30   70 % #fd2101  100 % #070000
         20 % #fbbe7f   50 % #fd5816   80 % #d60e01

hiver     0 % #f7fbfe   20 % #dbeaf7   40 % #b3d0e8   60 % #6f9dc9   80 % #2c5b90   100 % #0a1b33
printemps 0 % #f9fcef   20 % #eaf3c8   40 % #d8e894   60 % #c8d94a   80 % #5f8a22   100 % #0f2409
automne   0 % #fdf7ec   20 % #fae2bd   40 % #f3bb72   60 % #e08a35   80 % #a4501a   100 % #1e0c03
```

**La forme est celle de l'été, et elle doit l'être** : clair jusqu'au milieu,
l'assombrissement concentré après 70 %. C'est ce qui porte la date nue au-dessus
d'une carte, et c'est ce qui permet à la provenance de rester pâle au pied sur
les quatre. **Le printemps y perd sa lecture littérale** — il avait été demandé
blanc à vert-jaune — et le vert-jaune occupe désormais le milieu, le pied
descendant vers un vert de sous-bois. C'était l'alternative : un pied clair
obligeait la provenance à changer d'encre selon la saison.

**Cette page s'inverse en descendant, et c'est toute sa difficulté.** Le ciel de
l'accueil va du sombre au clair et une seule encre ivoire le sert d'un bout à
l'autre. Ici le premier écran est presque blanc et le dernier presque noir, sur
les quatre saisons. Aucune encre ne sert les deux extrémités. L'encre est donc
sombre par défaut, et **le seul bloc qui bascule au clair est la provenance**,
au pied de la page.

Six variables changent avec la saison, et six seulement : le dégradé, sa tête, et
les quatre encres qui se posent dessus.

| | encre | encre secondaire | filet | filet fort |
|---|---|---|---|---|
| hiver | `#0b1c30` | `#12293f` | `#5b87b5` | `#2f5b87` |
| printemps | `#17280c` | `#24380f` | `#7d9438` | `#4c6d1e` |
| été | `#21100a` | `#3d1608` | `#c9793f` | `#8f3f16` |
| automne | `#2a1206` | `#3d1c07` | `#bd7734` | `#8c4315` |

**La couleur de tête est servie, jamais recopiée** : `--sky-head` est à la fois
le fond du `body` et le premier arrêt du dégradé, comme `--sky-foot` sur
l'accueil l'est du panneau de candidats et du dernier arrêt.

**Rien d'autre ne bouge**, parce que rien d'autre ne touche au sol. Les cartes
restent blanches sur les quatre, et les deux températures se mesurent contre une
carte, non contre un ciel — c'est pourquoi elles donnent le même rapport partout.

**L'encre secondaire y est presque aussi noire que l'encre principale**, sur les
quatre saisons, et c'est une mesure qui l'a imposé : sur l'été, `#7a3f24`, le ton
qui *lit* comme secondaire, tombe à 2,6:1 sur l'orange saturé du milieu, où se
posent le marqueur de mois et la ligne du scénario. Ce qui sépare ces textes de
ce qu'ils nomment, c'est leur forme — onze pixels, capitales, interlettrage —,
exactement comme sur l'accueil quand le ton ne peut plus le porter.

**Le blanc du projet est celui des cartes**, et le graphe est dessiné sur le même
papier. Sur ce sol, rien de plus discret ne tiendrait : une carte est ce sur quoi
l'œil se pose. **La carte cesse par ailleurs d'être la boîte** : la date se pose
nue sur le dégradé, et seul le corps en dessous est dessiné.

Le rouge `#d40000` et le bleu `#0044aa` de la maquette, qui portaient les deux
températures, servent de repli sur une carte — une journée sans température n'a
pas de bande, donc pas de couleur d'échelle, et retombe sur eux — et **de couleur
propre aux deux courbes du graphe**, où ils reprennent leur premier métier :
nommer la maximale et la minimale. C'est aussi ce qui impose le papier sous le
graphe plutôt que le sol : posée sur le dégradé, une courbe rouge tomberait vers
les deux tiers sur le rouge de l'été, où elle cesse d'exister. Les deux nombres
d'une carte se mesurent contre une carte pour la même raison.

**La page tient au moins la fenêtre**, comme l'accueil, et pour deux raisons
superposées. Le calque du ciel est calé sur le `body` : sans hauteur minimale il
s'arrête où s'arrête le contenu, et une page de 789 px dans une fenêtre de 960
laissait 171 px de crème nue sous le dégradé. Et la provenance, qui s'écrit en
clair, ne le peut que là où le dégradé a viré au noir : simplement posée après la
bande, une fenêtre haute l'aurait fait atterrir sur l'orange. Tenue au pied par
une marge automatique, elle est **à 92-94 % du dégradé quelle que soit la
fenêtre**.

**Elle ne tient plus dans la fenêtre, en revanche, et c'est un arbitrage rendu.**
Le graphe ajoute quelque 420 px : la page passe de 789 à **1212 px** en
1440 × 960 et de 720 à **1144** en 1280 × 720. Le choix était entre replier le
graphe comme la provenance et laisser la page défiler ; c'est le second qui a été
retenu, le graphe étant la seconde lecture de la recherche et non une note. La
propriété perdue est réelle — cette page était faite pour être vue d'un coup — et
elle ne se paie pas en lisibilité : le dégradé étant ancré au document, une page
plus haute l'étire, chaque bloc glisse vers une portion plus claire, et **tous les
rapports montent** (tables ci-dessous).

**Le rythme vertical y reste plus serré que le rythme partagé.** Mesurée à 893 px
au rythme partagé avant le graphe, elle tombait à 789, et un second cran sous
800 px de fenêtre la ramène à 720. L'air se reprend aux deux bouts d'abord, où il
ne sépare rien, avant de se reprendre aux intervalles. Ce resserrement n'a plus
pour objet de tenir dans un écran ; il garde son sens, qui est de ne pas
distendre un ensemble de blocs qu'on lit à la suite.

Contrastes mesurés sur le rendu, fenêtre 1440 × 960, par
[`scripts/ink_contrast.py`](../scripts/ink_contrast.py) :

| Texte | hiver | printemps | été | automne |
|---|---|---|---|---|
| le lieu | 15,7:1 | 14,5:1 | 15,5:1 | 15,8:1 |
| la plage | 13,2:1 | 11,6:1 | 12,3:1 | 13,3:1 |
| nouvelle recherche | 14,8:1 | 14,0:1 | 13,0:1 | 14,8:1 |
| l'avertissement | 13,6:1 | 13,3:1 | 10,6:1 | 13,6:1 |
| le scénario | 11,2:1 | 10,6:1 | 8,5:1 | 11,1:1 |
| le mois | 10,3:1 | 10,2:1 | 7,4:1 | 10,1:1 |
| le jour | 11,7:1 | 12,3:1 | 8,2:1 | 11,3:1 |
| les deux mesures | 16,9:1 | 15,3:1 | 18,1:1 | 17,4:1 |
| la couture | 9,5:1 | 11,4:1 | 6,5:1 | 9,3:1 |
| les repères du graphe | 14,6:1 | 12,5:1 | 15,7:1 | 15,1:1 |
| la couture du graphe | 16,9:1 | 15,3:1 | 18,1:1 | 17,4:1 |
| la provenance | 8,3:1 | 7,4:1 | 9,3:1 | 8,8:1 |

**Les deux températures ne sont plus des lignes de cette table**, et leur retrait
est une correction et non un ménage. Elles ne sont pas sur la carte mais sur leur
aplat depuis que la rampe existe ; mesurées contre la carte, le script rapportait
un chiffre blanc sur papier blanc à **1,0:1** et en faisait le plancher de la
page. Le rapport qui veut dire quelque chose est celui de l'encre contre sa
propre bande, et la table de la rampe le publie neuf fois. Les valeurs qui
figuraient ici, 5,4:1 et 8,6:1, décrivaient la page d'avant les aplats.

**Les deux lignes du graphe ne bougent pas d'un dixième d'une saison à l'autre**,
et pour la raison qui vaut déjà pour les cartes : elles sont sur le papier, qui
ne tourne pas.

**L'été est le plus sombre des quatre sols, et donc le plus tendu.** Les trois
autres descendent moins vite et laissent partout plus de marge ; c'est la page
dessinée sur la maquette qui fixe le plancher, pas celles qui en dérivent.

**Une géométrie, quatre palettes.** La page mesurée est la vue `results` — dix
jours en arrière, quarante en avant —, qui porte un avertissement en haut et une
couture au milieu ; la saison est ensuite imposée sur le `body`, quatre fois. Ce
n'est pas un artifice : une plage à cheval sur aujourd'hui, en janvier, *est* une
page d'hiver avec avertissement et couture. C'est le seul moyen de comparer
quatre sols sur une même page, la saison d'une vraie couture dépendant du jour où
l'on mesure.

**Deux tailles de fenêtre, donc deux jeux de chiffres.** Le dégradé étant ancré
au document, une page raccourcie fait glisser chaque bloc sur une autre portion.
À 1280 × 720, la page fait 1144 px et tout se resserre d'un cran :

| Texte | hiver | printemps | été | automne |
|---|---|---|---|---|
| le lieu | 15,9:1 | 14,6:1 | 15,8:1 | 15,9:1 |
| la plage | 13,3:1 | 11,7:1 | 12,5:1 | 13,4:1 |
| nouvelle recherche | 14,9:1 | 14,0:1 | 13,2:1 | 14,9:1 |
| l'avertissement | 13,9:1 | 13,4:1 | 11,0:1 | 13,9:1 |
| le scénario | 11,4:1 | 10,7:1 | 8,7:1 | 11,4:1 |
| le mois | 10,7:1 | 10,3:1 | 7,8:1 | 10,5:1 |
| le jour | 12,0:1 | 12,5:1 | 8,6:1 | 11,7:1 |
| les deux mesures | 16,9:1 | 15,3:1 | 18,1:1 | 17,4:1 |
| la couture | 9,9:1 | 11,5:1 | 6,7:1 | 9,7:1 |
| les repères du graphe | 14,6:1 | 12,5:1 | 15,7:1 | 15,1:1 |
| la couture du graphe | 16,9:1 | 15,3:1 | 18,1:1 | 17,4:1 |
| la provenance | 8,6:1 | 7,9:1 | 9,8:1 | 9,2:1 |

**Le plancher de la page est la couture, à 6,5:1 en été** sur la fenêtre haute et
6,7 sur la courte — l'étiquette verticale est le seul texte que la géométrie
pousse sur la partie sombre du dégradé, et l'été le seul sol où cela coûte
quelque chose. Le sens des deux géométries s'est inversé le jour où le graphe est
arrivé : la page ne se raccourcit plus pour tenir dans l'écran, elle s'allonge
dans les deux cas, et **c'est la fenêtre courte qui donne désormais les meilleurs
rapports**, la page y étant proportionnellement plus haute que le dégradé
qu'elle traverse.

**Ces chiffres étaient plus bas avant le graphe** — plancher à 4,6:1 sur la
fenêtre courte —, et la remontée n'est pas un progrès de palette : c'est la
conséquence mécanique d'une page plus haute sur un dégradé ancré au document.
Elle se reperdrait le jour où la page raccourcirait, ce qui est la raison pour
laquelle cette table se remesure à chaque changement de mise en page plutôt que
de se recopier.

### L'échelle de couleur des températures

Les deux nombres d'une carte portent un aplat coloré, et le nombre se lit dessus.
**L'échelle est absolue** : la couleur ne dépend que de la température, jamais de
la date ni du lieu. Janvier est froid et juillet est chaud, et l'échelle le dit —
c'est ce que font les cartes météo grand public. Aucune normale n'entre donc dans
le calcul ; les normales ont servi à **placer les bornes**, pas à comparer.

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

**Neuf, parce que neuf se nomment.** Mesuré sur les mêmes données que les bornes,
une recherche de 47 jours montre 1,9 à 2,8 couleurs distinctes avec un pas de
10 °C — la bande entière est alors un aplat presque uniforme — et 2,7 à 4,0 avec
un pas de 5. Un pas de 2,5 °C a été essayé et écarté pour la raison inverse :
vingt-deux teintes ne se nomment plus, et une échelle dont les paliers n'ont pas
de nom est un dégradé, qui suggère une précision que des agrégats journaliers
n'ont pas. Le détail des mesures →
[`scripts/temperature_scale/`](../scripts/temperature_scale/README.md).

**Où l'échelle commence est ce qui garde les couleurs justes.** De 5 à 40 plutôt
que de 0 à 35, chaque couleur tombe là où un lecteur français l'attend — le jaune
sur 15-20, l'orange sur 20-25, le rouge à partir de 25 — et la bande haute revient
à une chaleur que le climat de référence n'atteint jamais. Le prix est un bas
d'échelle grossier : tout ce qui est sous 5 °C porte une seule couleur, soit 7 %
des maximales françaises et 28 % des minimales.

**L'encre bascule avec le fond, et c'est ce qui rend le jaune possible.** Une
encre blanche unique obligerait chaque aplat à être assez sombre pour la porter,
et un jaune assez sombre pour du blanc *est* un ocre — une première rampe l'a été,
et c'est ce qui l'a fait rejeter. Chaque bande nomme donc son encre : blanc sur
les quatre sombres, noir cassé sur les cinq claires. **Plancher mesuré : 5,51:1**,
porté par le rouge clair ; `scripts/ink_contrast.py` relit les neuf paires depuis
la feuille de style à chaque fois que l'une bouge.

**Où la couleur ne sépare plus.** Les trois dernières bandes sont rouges ou
noires : la teinte n'y distingue plus rien, seule la clarté le fait, et l'écart
entre le rouge très foncé et le noir vaut 1,50:1. Côte à côte c'est net ;
éloignées dans la bande, ces deux-là se lisent surtout par le nombre qu'elles
portent. Les six premières s'en sortent mieux parce qu'elles changent de teinte
en même temps que de clarté.

**L'aplat est la seule forme pleine du site**, là où la feuille pose que rien
n'est dans une boîte. L'exception se paie et se justifie : une teinte posée sur
une surface se distingue bien mieux de sa voisine que la même teinte sur les
traits fins d'un chiffre, et c'est la seule chose de la carte qui doive se lire
comme une **quantité** plutôt que comme un mot.

**La période de référence est 1981-2010**, la normale de l'OMM, et c'est
délibérément une référence froide pour un site qui montre l'avenir. À Paris,
d'après le modèle climatique, les journées à 30 °C ou plus passent de 4,9 par an
à 21, et celles à 35 ou plus de 0,5 à 5,3. L'échelle rougit à mesure que le siècle
avance, parce que la référence ne bouge pas.

### Le graphe sous la bande

**Une carte dit une journée ; quatre-vingt-dix cartes disent quatre-vingt-dix
journées, une à la fois, et jamais la forme de la période** — où la chaleur se
tient, quelle quinzaine est humide. C'est ce que le graphe ajoute, et c'est ce
qui règle sa largeur : dessiné colonne par colonne sous les cartes, il serait
parfaitement aligné et inutile, huit jours de courbe étant exactement ce que la
bande montre déjà. Il prend donc la largeur de la page et porte la plage entière.

**Deux panneaux partageant un axe de dates, jamais deux échelles verticales sur
un même tracé.** L'endroit où deux échelles se rencontrent est arbitraire, et un
lecteur prend le croisement d'une courbe et d'une barre pour un fait
météorologique. Les températures sont donc au-dessus, les précipitations en
dessous, dans un panneau à elles avec leur propre ligne de base. Chacun porte son
titre : les unités disent ce qui est mesuré, pas ce qu'on regarde.

**Chaque journée porte sa marque, et les segments sont droits.** La donnée est
l'agrégat journalier ; le segment qui joint deux marques est une commodité pour
l'œil, et c'est précisément pourquoi il ne doit pas être lissé — une courbe
adoucie inventerait un mardi après-midi dont la série n'a aucune lecture. Une
journée manquante coupe la courbe au lieu d'être traversée, et une lecture isolée
garde son point sans segment.

**L'écart entre les deux températures est rempli**, très pâle. L'amplitude
devient une épaisseur, ce qui est la seule chose que le graphe dise et qu'une
carte ne dise pas — et il la dit sans rien calculer : c'est la place entre deux
lectures déjà tracées.

#### Les deux axes

Ce sont les deux seules décisions du graphe, et toutes deux ont été arbitrées.

**En température, l'axe se cale sur les bornes de l'échelle de couleur** : bas au
multiple de cinq sous la lecture la plus froide, haut au multiple au-dessus de la
plus chaude, plus une demi-bande d'air à chaque bout. **À l'intérieur de
l'échelle, chaque filet est une borne servie** — le même palier que les aplats
des cartes, de sorte qu'une hauteur ici et une couleur là-haut sont la même
lecture. **Au-delà de ses deux extrémités ouvertes, le réglage continue au même
intervalle** : tout ce qui est sous 5 °C est une seule bande et n'a aucune borne
à tracer, si bien qu'une période gelée aurait reçu un panneau réglé une fois. La
continuation est ce qui pose la ligne sur zéro, et symétriquement sur 45.

Un axe absolu fixe a été écarté : il tiendrait la comparaison entre deux
recherches, au prix d'écraser une plage d'été dans un tiers du panneau, ce qui
coûte exactement ce que le graphe apporte.

**En précipitations, l'axe prend la journée la plus arrosée de la période, avec
un plancher de 10 mm.** Le plancher n'est pas un confort : sans lui, une plage
dont la journée la plus humide fait 0,3 mm cadrerait l'axe sur 0,3 mm, et cette
bruine dessinerait la même barre qu'un orage de 40 mm ailleurs. Rien n'étant
servi pour graduer ce panneau, l'intervalle se choisit sur la hauteur qu'il a :
le plus petit pas rond laissant au plus quatre intervalles — 5 et 10 sur une
période calme, 10 et 20 sur une période humide. Les millimètres y gardent leur
dixième, comme sur les cartes : deux règles d'arrondi pour une seule grandeur
seraient une divergence de plus.

**Aucun nombre portant sur la période n'est écrit.** Le plafond dépend du
maximum, mais il n'est pas affiché — l'étiquette qui le nommait a été retirée,
étant un extrême de la plage → [Ce que l'interface ne calcule
pas](#ce-que-linterface-ne-calcule-pas).

#### Ce que le graphe emprunte

**Il est dessiné sur le papier des cartes**, et ses marques prennent les couleurs
déjà nommées par la feuille. Il n'ajoute donc **aucune variable saisonnière** :
les six qui tournent restent six.

**Il porte la même couture que la bande, au même jour** — une verticale
traversant les deux panneaux, sous la même étiquette. Où elle tombe est une règle
partagée par un seul module, `series.js`, et non recopiée dans chacune des deux
vues.

**Son équivalent accessible est la bande elle-même**, qui porte déjà chaque
valeur en toutes lettres. Le dessin est annoncé par un nom qui renvoie à elle, et
ne réénonce aucun nombre : une infobulle serait un second exemplaire de la carte.

**Sous 58 rem, il défile latéralement au lieu de rétrécir.** Le dessin est un
`viewBox` unique et se met à l'échelle en entier, sa typographie comprise : à la
largeur d'un téléphone, les nombres de l'axe sortaient à quatre pixels. Il n'y a
pas de point de rupture à choisir — le minimum est l'endroit où onze unités
valent onze pixels — et c'est la réponse que la bande donne déjà au même
problème.

---

## Le contrat JSON

Un tableau d'objets journaliers, stable et documenté, pour qu'un graphique, un
cumul ou une carte s'y branchent sans toucher au pipeline. Chaque journée porte
`date`, `origin`, `source`, les deux températures, `precipitation`,
`cloud_cover`, les deux vents, `sky`, et les deux bandes de l'échelle de couleur
— `temperature_min_band` et `temperature_max_band`.

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

La réponse porte en outre **`has_simulated`** et les métadonnées de la grille.
Le premier dit si l'avertissement est dû. Il est servi plutôt que recalculé sur
les journées, parce que le serveur en détient une version : c'est le même
constat qui lui fait aller chercher la correction de nébulosité. Et c'est la
donnée dont dépend la règle 1, celle qui prime sur toutes les autres. Les
secondes sont nulles quand rien n'a été corrigé, ce qui est la réponse honnête
pour une plage entièrement passée.

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
quantiles** — la réanalyse sur la période de calibration, le modèle sur cette
même période, le modèle sur la projection. Le premier écart est le biais, le
second la tendance à préserver. Trente-neuf niveaux par vecteur, arrondis au
dixième de point.

### Le réseau

Réseau **mondial fixe au pas de 0,5°**, aux multiples exacts depuis −180° et
−90°. Non négociable : caler l'origine sur la France imposerait de tout
recalculer au premier élargissement.

**Le pas de 0,5° est confirmé par la mesure, contre 1° qui aurait coûté quatre
fois moins.** Biais relevé tous les 0,25° le long de trois transects traversant
la côte, puis erreur qu'une interpolation linéaire commettrait entre nœuds
espacés d'un degré, puis d'un demi :

| Transect | Erreur à 0,5° (moy / max) | à 1,0° (moy / max) |
|---|---|---|
| Atlantique (Landes) | 0,17 / 0,30 | 0,20 / 0,50 |
| Méditerranée (Languedoc) | 0,32 / 0,73 | 0,39 / 1,02 |
| Manche (Normandie) | 0,21 / 0,56 | 0,41 / 0,90 |

**Deux constats méritent d'être isolés.** La côte n'y est pour rien : le
franchissement terre-mer ne produit aucune rupture du biais — à −1,25° de
longitude sur l'Atlantique, il vaut −10,59 des deux côtés. C'est le **relief**
qui commande, et fortement : 5,52 points sur un seul degré à la montée vers les
Cévennes, de 87 m à 1 147 m. Le script 15 concluait « champ de biais lisse » sur
un transect jurassien ; ce n'est pas faux mais ce n'est pas général.

**L'interpolation porte donc une erreur propre, à déclarer avec les autres :**
0,3 point de nébulosité en moyenne, 0,7 au maximum sur relief, même à 0,5°.

### Le volume et le coût

Établi par une sonde d'altitude d'un jour sur chaque nœud de la boîte englobante
— ERA5 renvoyant zéro en mer, l'altitude sépare la terre de l'eau pour un coût
négligeable :

| | |
|---|---|
| Nœuds dans la boîte (41,0-51,5 N, −5,5-10,0 E) | 704 |
| Terrestres | 475 |
| À collecter : terre + couronne côtière | **594** |

La couronne de nœuds marins touchant la terre est conservée délibérément : une
ville littorale a des nœuds en mer parmi les quatre qui l'entourent, et les
omettre laisserait l'interpolation manchote là précisément où les gens habitent.

**Le coût de la collecte est la contrainte dominante.** Deux requêtes par nœud —
la réanalyse sur la période de calibration, le modèle sur 1985-2050 d'un seul
tenant. Le réseau ne représente qu'une heure ; tout le reste est de l'attente.

**Le plafond est journalier, non horaire.** C'est le point à retenir, et il a été
mal lu d'abord. Open-Meteo le dit lui-même, dès qu'on le franchit :

```
HTTP 429 : Daily API request limit exceeded. Please try again tomorrow.
```

Les nœuds arrivent par **salves** — une quinzaine à une vingtaine en quelques
minutes quand le budget se recharge — puis plus rien pendant des heures. Le
rythme *dans* une salve n'est donc pas un débit : mesuré sur une fenêtre de
trente-six minutes, il donne trente nœuds par heure et une prévision de quinze à
vingt heures pour la France, qui s'est révélée fausse d'un facteur dix.

Ce qui se mesure vraiment, c'est le rendement d'une journée civile :

| Journée | Nœuds |
|---|---|
| 9 août | 61 |
| 10 août | 127 |

**Cinquante à cent trente nœuds par jour**, quelle que soit la façon dont on s'y
prend — raccourcir le palier de reprise de 300 à 60 s a été essayé, sans effet.
La France demande donc **de l'ordre de la semaine**, en temps réel, pour une
collecte qui n'occupe qu'une heure de réseau.

La documentation d'Open-Meteo annonce par ailleurs des limites qui impliqueraient
quatre nœuds par jour, plus de vingt fois moins que ce qu'on observe, et l'API
n'expose aucun en-tête de quota. **Le débit ne se prédit pas, il se mesure — et
il se mesure sur des journées entières, pas sur des fenêtres.**

Conséquence pratique : la collecte tire sur le même quota que le navigateur d'un
visiteur, puisque c'est la même adresse IP. **Elle se coupe avant d'essayer le
site**, faute de quoi les recherches échouent sur le message de limite.

Le remplissage est **ordonné par population desservie décroissante**, estimée en
sommant les aires d'attraction françaises pondérées par l'inverse du carré de la
distance. Ce n'est pas un confort : une première tentative collectait par
latitude croissante et a passé ses premières heures sur le plateau ibérique. La
collecte est ainsi interruptible, reprenable, et couvre l'essentiel des
recherches réelles dès ses premières heures.

### Hors de la zone couverte

L'application **refuse la recherche avec un message explicite**. Afficher des
données non corrigées reviendrait à montrer un futur artificiellement
ensoleillé ; se rabattre sur le nœud le plus proche serait silencieux et
trompeur.

**Ce refus ne vaut que si la plage comporte des journées simulées.** Une requête
entièrement passée n'appelle aucun coefficient : la refuser serait gratuit, et
priverait sans motif un utilisateur de Santiago de l'histoire météorologique de
sa ville.

**Depuis l'étape 7, la quinzaine à venir échappe elle aussi au refus.** Elle vient
d'ECMWF IFS, qui ne demande aucune correction, donc une recherche qui n'atteint
pas le modèle climatique est servie partout dans le monde. Le message le dit :
c'est « pour les dates lointaines » que le lieu n'est pas couvert, et « les dates
passées **et les jours à venir** » restent consultables. Ce libellé a été faux
pendant la durée de l'étape — il annonçait que seul le passé restait accessible —
et c'est le genre d'erreur qu'aucun test ne rattrape, un message restant vrai
grammaticalement en cessant de l'être en fait.

### Métadonnées et table provisoire

La table porte ses propres métadonnées — modèle corrigé, maille, périodes de
calibration et de projection, date de génération, nombre de nœuds. Une table lue
sans savoir cela est une source d'erreur silencieuse, et c'est précisément la
pièce dont un successeur héritera sans avoir vu comment elle a été faite.

**Une table provisoire existe, et elle se dénonce.** La collecte se comptant en
heures de quota, une table à correction identité couvre toute la boîte française
pour que le reste de la chaîne s'écrive sans l'attendre. **Elle ne doit jamais
être servie** : une correction nulle affiche un futur artificiellement ensoleillé
de 8 à 11 points, et trois des cinq classes en dépendent. Cinq verrous plutôt
qu'un — un drapeau `placeholder` dans les métadonnées, dont un test vérifie
qu'il survit à l'écriture-relecture ; une propriété exposée à l'appelant ; un nom
de fichier distinct ; une exclusion du dépôt ; et **le refus de démarrer**.

Le dernier est le seul qu'aucun oubli ne contourne, les quatre autres supposant
qu'un appelant pense à les consulter. L'application lit la table une fois au
démarrage et s'arrête net si elle porte le drapeau.

L'exclusion du dépôt, elle, ne tenait au départ que par ricochet : la règle
`data/` du `.gitignore`, non ancrée, excluait tout dossier de ce nom — dont
celui de la ressource serveur, ce qui privait un déploiement de la table réelle
et empêchait git de lire la ligne écrite pour le fichier provisoire. La règle est
désormais ancrée à la racine.

---

## Préparé sans être construit

- **L'internationalisation** : tous les textes visibles sont extraits dans un
  dictionnaire dès le départ. Trivial maintenant, coûteux plus tard.
- **Les pages explicatives** : statiques, aucune infrastructure particulière.

---

## Choix techniques

**FastAPI** plutôt que Flask : validation des entrées par Pydantic,
documentation OpenAPI automatique, meilleur ajustement à une API JSON sans état.

**JavaScript natif en modules ES**, sans cadriciel. Deux pages ne le justifient
pas, et l'absence de chaîne de compilation garde le projet abordable. Les
frontières de modules sont posées de sorte qu'une migration reste possible.
