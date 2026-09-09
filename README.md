# Weather Simulator

Une application météo qui couvre n'importe quelle journée entre 1950 et 2050,
en n'importe quel point du globe. On saisit un lieu et une plage de dates ;
elle affiche, jour par jour, l'aspect du ciel, les températures minimale et
maximale, les précipitations et le vent.

Trois régimes se succèdent, sous la même présentation. Le passé vient de
réanalyses. La quinzaine à venir est une prévision météorologique ordinaire.
Au-delà, c'est une simulation climatique.

> ⚠️ **Au-delà de la quinzaine, ce n'est pas une prévision.**
> Un modèle climatique ne prédit pas les conditions d'une date donnée. Il produit
> une trajectoire cohérente, c'est-à-dire une suite de journées plausibles dans un
> climat modifié. La date situe la journée dans une saison et dans une décennie ;
> elle n'engage rien sur cette journée-là.

## Pourquoi

Le changement climatique se communique par des moyennes globales et des anomalies
de température, « +2,7 °C à l'horizon 2100 ». Ces grandeurs sont exactes mais
agrégées : elles ne disent rien des conditions rencontrées en un lieu et à une
date. « 21 °C / 39 °C, ciel dégagé, 0 mm » a une matérialité que l'anomalie n'a
pas. La forme du bulletin météo est donc un choix de fond, pas un habillage.

## Données

Une plage demandée est découpée en quatre segments, chacun servi par sa source.

| Segment | Période | Source |
|---|---|---|
| Passé ancien | 1950 jusqu'au dernier jour servi par les réanalyses | ERA5 et ERA5-Land |
| Passé récent | les cinq à six jours suivants, jusqu'à aujourd'hui | ECMWF IFS |
| Prévision | demain jusqu'à J+14 | ECMWF IFS |
| Futur | ensuite jusqu'à fin 2050 | MRI-AGCM3-2-S, CMIP6 HighResMIP |

Le tout par les API publiques d'Open-Meteo. La seule trajectoire d'émissions
disponible approche RCP8.5, soit une hypothèse haute.

Deux principes commandent le reste. Toute grandeur affichée est calculée de la
même façon sur les quatre segments, pour qu'aucune rupture n'apparaisse aux
jonctions. Et une grandeur qu'une seule source sert est écartée plutôt
qu'exploitée, quitte à la reconstruire de variables que les quatre servent.

## Ce que l'application montre

Une bande de cartes, une par journée, jusqu'à quatre-vingt-douze jours. Sous
elle, les mêmes journées dessinées en trois panneaux : températures,
précipitations, cumul des précipitations. Une autre année peut être superposée en
gris pour comparer. Les journées affichées s'exportent en CSV.

Deux grandeurs sont reconstruites plutôt que servies, faute d'exister sur les
quatre segments : l'aspect du ciel, et la température humide, qui signale les
journées où l'humidité empêche la transpiration de refroidir le corps.

L'application répond partout dans le monde. La grille de correction du modèle
climatique ne couvre pour l'instant que la France ; ailleurs la projection est
servie telle que le modèle la donne, et la page le dit.

## État

Le site fonctionne. La collecte de la grille de correction est en cours, 438
nœuds sur 594. Deux étapes restent ouvertes : l'élargissement de la grille au
monde, et la calibration de l'humidité du modèle.

L'avancement détaillé est dans [`docs/journal.md`](docs/journal.md).

## Documentation

Les décisions, leurs justifications chiffrées et leurs limites sont écrites en
français, un document par sujet.

| Document | Sujet |
|---|---|
| [`CLAUDE.md`](CLAUDE.md) | les règles qui s'appliquent toujours, et la carte des documents |
| [`docs/projet.md`](docs/projet.md) | l'intention, la finalité, le public |
| [`docs/donnees.md`](docs/donnees.md) | requêtes, sources, variables, assemblage |
| [`docs/regles.md`](docs/regles.md) | classe de ciel, température humide, seuils, correction |
| [`docs/science.md`](docs/science.md) | modèles, référence, biais, limites |
| [`docs/application.md`](docs/application.md) | architecture, affichage, grille de correction |
| [`docs/journal.md`](docs/journal.md) | l'avancement, ce que chaque étape a établi |
| [`docs/idees.md`](docs/idees.md) | les pistes écartées et les questions ouvertes |

Les chiffres restent attachés au script qui les mesure : chaque `README.md` de
[`scripts/`](scripts/) dit ce qui s'y démontre.

## Structure

```
weather-simulator-app/
├── src/weather_simulator/
│   ├── domain/          classe de ciel, température humide, seuils, correction
│   ├── sources/         requêtes Open-Meteo, lecture des réponses, assemblage
│   ├── transform/       bloc de transformation, neutre par défaut
│   ├── api/             endpoints, validation des entrées, contrat JSON
│   └── calibration/     table de coefficients et interpolation
├── web/                 pages et JavaScript, sans construction ni dépendance
├── tests/               Python, et les tests d'interface lancés par node --test
├── scripts/             mesures, collectes, captures d'écran
├── docs/                les décisions et ce qui les fonde
└── CLAUDE.md            les règles permanentes et la carte des documents
```

## Installation

```bash
git clone git@github.com:SCarnot/weather-simulator-app.git
cd weather-simulator-app

python3 -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
```

Lancer le site :

```bash
uvicorn weather_simulator.api.app:app --reload
```

Lancer les tests :

```bash
pytest
```

Node sert de lanceur aux tests d'interface, et à rien d'autre. S'il est absent,
ces tests se déclarent ignorés et le reste tourne. Les scripts de
`scripts/verification/` n'ont aucune dépendance et s'exécutent sans installation.

---

*In English. Weather Simulator answers for any day between 1950 and 2050,
anywhere on Earth, in the form of an ordinary weather bulletin: sky, temperatures,
precipitation and wind, day by day. The past comes from reanalyses, the fortnight
ahead is a real forecast, and everything beyond is a climate simulation. That last
part is not a prediction: a climate model produces a plausible trajectory, never
the conditions of a given date. Design decisions are documented in French under
`docs/`; an English translation is planned.*
