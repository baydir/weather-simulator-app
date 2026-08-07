# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Ce fichier ne porte que **les règles qui s'appliquent toujours** et **la carte
des documents**. Tout le reste — l'intention, les données, les méthodes, la
science, l'application — vit dans `docs/`, un document par sujet, à charger
quand la tâche le touche.

---

## Les règles qui ne se négocient pas

### 1. L'application ne produit pas de prévision

Cette contrainte prime sur toutes les autres. Un modèle climatique ne prédit pas
les conditions du 14 juillet 2046 : il produit une trajectoire plausible. Trois
règles en découlent, applicables au code comme aux textes de l'interface :

- **Vocabulaire de la prévision proscrit pour les dates futures** — « prévision »,
  « il fera ». Les termes retenus sont « simulation », « météo plausible »,
  « scénario ».
- **Tout écran affichant une date future porte un avertissement explicite et
  visible.**
- **Aucune assertion d'exactitude portant sur une date déterminée n'est admise.**

Le pourquoi → [`docs/projet.md`](docs/projet.md).

### 2. Toute grandeur affichée se calcule identiquement sur toute la série

Quelle que soit la source qui a fourni la journée. **Ce principe prime sur la
précision.**

Il en découle une règle contre-intuitive : lorsqu'une information n'existe que
du côté du passé, **elle est écartée plutôt qu'exploitée**. Le passé est
délibérément ramené au niveau du futur, jamais l'inverse. Une richesse
disponible d'un seul côté produirait une rupture à la couture — l'artefact que
tout le dispositif vise à empêcher. La série comportant **deux coutures** et non
une, le principe vaut à chacune.

### 3. La classe de ciel est servie par une fonction unique, appelée trois fois

Toute duplication de cette logique — entre segments, ou entre Python et
JavaScript comme dans le prototype initial — rouvre la divergence que la règle 2
interdit. **Le navigateur ne dérive rien** : il récupère, transmet, affiche.

### 4. Gouvernance : la science se valide, le développement s'autonomise

**Domaine scientifique et traitement des données — validation obligatoire.** Le
porteur du projet est compétent sur ces sujets et en conserve l'arbitrage. Y
relèvent : le choix des modèles et du scénario, les méthodes de correction de
biais, la reconstruction de variables absentes, l'homogénéisation des séries,
les choix statistiques et les métriques de validation. Les options s'exposent
avec leurs implications et leurs limites ; **la décision revient au porteur du
projet**.

**Développement logiciel — autonomie étendue.** Architecture, bibliothèques,
organisation du code et modalités d'implémentation s'arrêtent sans validation
préalable. Les difficultés et les compromis notables sont signalés.

**Cas mixtes : le premier régime l'emporte.** Une décision de développement
emportant une conséquence scientifique relève de la validation, quelle que soit
son apparence technique — cache modifiant la granularité temporelle, agrégation
ou arrondi côté interface, remplissage de valeurs manquantes, simplification
introduite pour la performance. **En cas de doute, la validation est requise.**

### 5. Conventions de langue

- Code, identifiants, commentaires, messages de commit : **anglais**.
- Interface et textes destinés à l'utilisateur : **français**.
- Documentation : français ; traduction anglaise prévue ultérieurement.

---

## La carte des documents

| Si la tâche touche à… | Lire |
|---|---|
| l'intention, la finalité, le public | [`docs/projet.md`](docs/projet.md) |
| requêtes, sources, variables, assemblage, cache | [`docs/donnees.md`](docs/donnees.md) |
| classe de ciel, seuils, correction de nébulosité | [`docs/regles.md`](docs/regles.md) |
| modèles, référence, biais, limites, références | [`docs/science.md`](docs/science.md) |
| architecture, affichage, grille de correction | [`docs/application.md`](docs/application.md) |
| l'avancement, ce qu'une étape a établi | [`docs/journal.md`](docs/journal.md) |
| une piste écartée ou une question ouverte | [`docs/idees.md`](docs/idees.md) |

Les chiffres restent attachés au script qui les mesure : chaque `README.md` de
`scripts/` dit ce qui s'y démontre.

| Dossier | Ce qu'il établit |
|---|---|
| `scripts/verification/` | les mesures de conception, antérieures à tout code — **gelé** |
| `scripts/model_selection/` | le départage des cinq modèles, étape 2 |
| `scripts/sky_thresholds/` | le calage des seuils de ciel, étape 3 |
| `scripts/calibration_grid/` | la grille de correction, étape 4 |
| `scripts/inspect_seam.py` | lecture des coutures sur requête réelle |

Les trois premiers ne se ressemblent pas, et c'est délibéré. `verification/` date
de la conception : aucune dépendance, `urllib` seul, chaque script isolé. Les
deux autres sont postérieurs au paquet et s'appuient sur lui — refaire la
construction des requêtes y aurait ouvert la porte à deux comportements
divergents — et séparent la collecte, lente et limitée en débit, de l'analyse,
qui se rejoue hors réseau depuis `data/`.

---

## Où on en est

Étapes 0 à 3 et **étape 5 faites**. **Étape 4 en cours** : la méthode de
correction, la table et son interpolation sont écrites, la collecte des 594
nœuds reste à mener (23 faits, dont trois mailles refermées autour de Paris —
assez pour éprouver la chaîne). **L'interface n'est pas commencée.**

Le détail, et ce que chaque étape a corrigé de ce que la précédente supposait →
[`docs/journal.md`](docs/journal.md).

---

## Tenue du dépôt

**Un fait vit dans un seul fichier.** Une valeur contestée se remesure par le
script correspondant, puis se corrige **sur place** — jamais ajoutée à côté de
l'ancienne, jamais recopiée dans un second document.

**Chaque document fait foi sur son domaine.** En cas de divergence entre un
document et le code, c'est le document qui l'emporte et le code qui doit être
corrigé — ou le document amendé, si c'est lui qui a pris du retard.

**Les documents et les dossiers de mesure ne se modifient pas sans
validation** : `docs/`, `CLAUDE.md`, `scripts/verification/`,
`scripts/model_selection/`, `scripts/sky_thresholds/`. Le reste du code relève
de l'autonomie de développement définie plus haut.

**Environnement** : `./venv/bin/python`. Les tests tournent hors réseau, l'accès
aux API étant injecté.
