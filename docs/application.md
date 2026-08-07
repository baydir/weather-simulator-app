# Application — architecture, affichage, grille

Comment le site est bâti et ce qu'il montre. Les règles qu'il applique →
[`regles.md`](regles.md) ; ce qu'il refuse de promettre →
[`projet.md`](projet.md).

---

## Nature du site

Un site grand public volontairement restreint : **une page d'accueil portant le
formulaire, une page de résultats**. Des pages explicatives viendront plus tard,
statiques et peu interactives.

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

**Le navigateur ne dérive rien.** Il récupère, il transmet, il affiche. Toute
donnée calculée l'est en Python, côté serveur — la classe de ciel doit être
produite par une fonction unique, et le prototype initial montre ce qu'entraîne
sa duplication entre JavaScript et Python.

Le navigateur poste les données brutes ; le serveur valide les entrées, applique
la correction de nébulosité, le bloc de transformation et la classe de ciel, et
renvoie le JSON journalier. **Il n'expose qu'un seul endpoint utile.** Sans état et sans base de
données, il monte en charge par simple multiplication des instances, derrière un
frontend statique servi par CDN.

---

## Organisation du code

```
src/weather_simulator/
    sources/       requêtes, lecture des payloads, assemblage des trois segments
    domain/        enregistrement journalier, seuils, classe de ciel
    transform/     bloc de transformation, neutre par défaut
    api/           endpoint, validation des entrées
    calibration/   table de coefficients et interpolation
web/
    static/js/     fetch.js (transport seul), render.js, i18n.js
    templates/     accueil, résultats
```

La séparation entre `domain` et `transform` est délibérée : `domain` porte les
règles arrêtées et n'a pas vocation à bouger, `transform` est le point de
maîtrise sur les données, appelé entre la correction et l'affichage, et ne
transforme rien par défaut.

---

## Affichage

Une bande journalière, une carte par jour, défilant horizontalement lorsqu'elle
excède la largeur de l'écran. **Plage bornée à 90 jours**, soit une saison —
contrainte appliquée à la fois dans l'interface et dans l'API, jamais dans le
seul navigateur.

Chaque journée porte les températures minimale et maximale, le cumul de
précipitations, les vitesses de vent moyenne et maximale, et un pictogramme :

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
couramment le double : 36,8 km/h contre 14,4 km/h à Pontarlier en juin 2024. Les
libellés retenus sont « vent moyen » et « vent maximal ».

**Tout écran affichant une date future porte un avertissement explicite et
visible** → [`projet.md`](projet.md).

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
tenant. Le réseau ne représente qu'une heure ; c'est le débit autorisé qui
commande, de l'ordre de **trente nœuds par heure**, soit quinze à vingt heures
pour la France. La documentation d'Open-Meteo annonce des limites qui
impliqueraient quatre nœuds par jour, deux cents fois moins que ce qu'on
observe, et l'API n'expose aucun en-tête de quota : **le débit ne se prédit pas,
il se mesure.**

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

**Ce refus ne vaut que si la plage comporte un segment futur.** Une requête
entièrement passée n'appelle aucun coefficient : la refuser serait gratuit, et
priverait sans motif un utilisateur de Santiago de l'histoire météorologique de
sa ville.

### Métadonnées et table provisoire

La table porte ses propres métadonnées — modèle corrigé, maille, périodes de
calibration et de projection, date de génération, nombre de nœuds. Une table lue
sans savoir cela est une source d'erreur silencieuse, et c'est précisément la
pièce dont un successeur héritera sans avoir vu comment elle a été faite.

**Une table provisoire existe, et elle se dénonce.** La collecte se comptant en
heures de quota, une table à correction identité couvre toute la boîte française
pour que le reste de la chaîne s'écrive sans l'attendre. **Elle ne doit jamais
être servie** : une correction nulle affiche un futur artificiellement ensoleillé
de 8 à 11 points, et trois des cinq classes en dépendent. Quatre verrous plutôt
qu'un — un drapeau `placeholder` dans les métadonnées, dont un test vérifie
qu'il survit à l'écriture-relecture ; une propriété exposée à l'appelant ; un nom
de fichier distinct ; une exclusion du dépôt.

---

## Préparé sans être construit

- **L'internationalisation** : tous les textes visibles sont extraits dans un
  dictionnaire dès le départ. Trivial maintenant, coûteux plus tard.
- **Le contrat JSON de sortie** : un tableau d'objets journaliers, stable et
  documenté. Un graphique, un cumul ou une carte s'y brancheront sans toucher au
  pipeline.
- **Les pages explicatives** : statiques, aucune infrastructure particulière.

---

## Choix techniques

**FastAPI** plutôt que Flask : validation des entrées par Pydantic,
documentation OpenAPI automatique, meilleur ajustement à une API JSON sans état.

**JavaScript natif en modules ES**, sans cadriciel. Deux pages ne le justifient
pas, et l'absence de chaîne de compilation garde le projet abordable. Les
frontières de modules sont posées de sorte qu'une migration reste possible.
