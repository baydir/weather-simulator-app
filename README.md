# Weather Simulator

Quel temps fera-t-il à Pontarlier le 14 juillet 2046 ? La question n'a pas de
réponse — mais elle a une réponse *plausible*, et c'est celle que cette
application restitue, jour par jour, sous la forme familière d'un bulletin
météorologique.

L'utilisateur saisit un lieu et une plage de dates comprise entre 1950 et 2050.
L'application affiche pour chaque journée les températures minimale et maximale,
l'aspect du ciel, les précipitations et le vent.

> ⚠️ **Ce n'est pas une prévision.**
> Un modèle climatique ne prédit pas les conditions d'une date donnée. Il produit
> une trajectoire cohérente, c'est-à-dire une séquence de journées
> statistiquement plausible dans un climat modifié. La date situe la journée dans
> une saison et dans une décennie ; elle n'engage aucune exactitude sur cette
> journée.

## Pourquoi

Le changement climatique se communique d'ordinaire par des moyennes globales et
des anomalies de température (« +2,7 °C à l'horizon 2100 »). Ces grandeurs sont
exactes mais agrégées : elles ne disent rien des conditions concrètes rencontrées
en un lieu et à une date. L'énoncé « 21 °C / 39 °C, ciel dégagé, 0 mm » a un
caractère tangible que l'anomalie globale n'a pas. Le format d'application météo
est donc ici un choix fonctionnel, non un habillage.

## Données

| Régime | Source |
|---|---|
| Passé, 1950 → veille | Réanalyses ERA5 et ERA5-Land, via l'*Historical Weather API* d'Open-Meteo |
| Futur, jour → 2050 | Modèle CMIP6 HighResMIP, via la *Climate API* d'Open-Meteo |

La seule trajectoire d'émissions disponible approche RCP8.5, soit une hypothèse
haute. Toute grandeur affichée est calculée de façon identique de part et d'autre
de la date du jour, afin qu'aucune rupture n'apparaisse à la couture.

Les choix scientifiques, leurs justifications chiffrées et leurs limites sont
consignés dans [`CLAUDE.md`](CLAUDE.md). Les mesures qui les fondent sont
reproductibles par les scripts de
[`scripts/verification/`](scripts/verification/README.md).

## État

Projet en cours de construction. La conception est arrêtée, le code démarre.
L'avancement par étapes est suivi dans [`CLAUDE.md`](CLAUDE.md).

## Structure

```
weather-simulator-app/
├── src/weather_simulator/
│   ├── domain/          classe de ciel, seuils, correction de biais
│   ├── transform/       bloc de transformation, neutre par défaut
│   ├── api/             endpoint, validation des entrées
│   └── calibration/     table de coefficients et interpolation
├── web/                 frontend statique (à venir)
├── scripts/verification/ scripts établissant les faits chiffrés de CLAUDE.md
├── CLAUDE.md            décisions de conception
└── pyproject.toml
```

## Installation

```bash
git clone git@github.com:SCarnot/weather-simulator-app.git
cd weather-simulator-app

python3 -m venv venv
source venv/bin/activate

pip install -e ".[dev]"
```

Les scripts de vérification n'ont aucune dépendance : bibliothèque standard
seule, ils s'exécutent sans installation préalable.

---

*In English — Weather Simulator renders climate projections as an everyday
weather bulletin: pick a place and any date range between 1950 and 2050, get a
day-by-day account of temperature, sky, precipitation and wind. It is a
simulation, not a forecast: a climate model produces a plausible trajectory, not
the conditions of a given date. Design decisions are documented in French in
`CLAUDE.md`; an English translation is planned.*
