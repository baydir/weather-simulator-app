# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> Document en cours de rédaction. Sections rédigées : 1, 2, 3, 4.

---

## Avancement

Les étapes 0 et 1 sont faites. Le dépôt contient le présent document, `scripts/verification/`, et le paquet `src/weather_simulator/`, dont `sources/` récupère et assemble la série homogène de 1950 à 2050. La classe de ciel, la correction de nébulosité et l'API restent à écrire.

L'enchaînement ci-dessous fixe **l'ordre**, imposé par les dépendances, et non le contenu de chaque étape — celui-ci se décide au moment de l'aborder, à la lumière de ce que la précédente aura révélé.

| | Étape | Dépend de | État |
|---|---|---|---|
| 0 | Nettoyage du prototype, packaging, `.gitignore` | — | **fait** |
| 1 | Récupération et série homogène, sans classe de ciel | 0 | **fait** |
| 2 | Confirmation du modèle parmi les cinq éligibles | 1 | à faire |
| 3 | Calage des seuils de nébulosité et classe de ciel | 1 | à faire |
| 4 | Grille de calibration France et correction de nébulosité | 2 | à faire |
| 5 | API, validation des entrées et bloc de transformation | 3, 4 | à faire |
| 6 | Interface : accueil, résultats, bande journalière | 5 | à faire |
| 7 | Élargissement mondial de la grille | 4 | à faire |

La confirmation du modèle vient en deuxième position pour deux raisons : l'étape 1 produit l'outil qui permet de la mener, et tout ce qui suit en dépend. Changer de modèle après avoir généré la grille de calibration imposerait de la refaire entièrement.

Trois décisions demeurent ouvertes et relèvent du porteur du projet : les seuils de nébulosité de 30 % et 70 %, provisoires ; la méthode de correction du biais, dont le document exige seulement qu'elle préserve la tendance ; et le modèle lui-même, `MRI_AGCM3_2_S` restant provisoire.

---

## 1. Contexte général du projet

### Objet

Weather Simulator App est une application web restituant, jour par jour, les conditions météorologiques d'un lieu donné, pour toute date comprise entre 1950 et 2050.

L'utilisateur renseigne une localisation et une plage de dates. L'application retourne pour chaque journée les températures minimale et maximale, l'aspect du ciel et les précipitations, selon les modalités de présentation d'une application météorologique grand public.

### Finalité

La finalité du projet est pédagogique et non technique.

Le changement climatique est habituellement communiqué au moyen de moyennes globales et d'anomalies de température (« +2,7 °C à l'horizon 2100 »). Ces grandeurs sont exactes mais agrégées : elles ne renseignent pas sur les conditions concrètes rencontrées à une date et en un lieu déterminés.

Le projet repose sur l'hypothèse que la restitution des projections climatiques sous une forme déjà familière — le bulletin météorologique quotidien — en améliore l'appropriation par un public non spécialiste. L'énoncé « 14 juillet 2046, Paris : 21 °C / 39 °C, ciel dégagé, 0 mm » présente un caractère concret que l'anomalie globale n'a pas.

Le format d'application météorologique constitue donc un choix fonctionnel et non un habillage. Toute décision de conception qui s'en écarte doit être justifiée au regard de cet objectif.

### Contrainte principale : l'application ne produit pas de prévision

Cette contrainte prime sur toutes les autres.

Un modèle climatique ne prédit pas les conditions du 14 juillet 2046. Il produit une trajectoire cohérente, c'est-à-dire une séquence de journées statistiquement plausible dans un climat modifié. La date affichée situe la journée dans une saison et dans une décennie ; elle n'engage aucune exactitude sur cette journée.

Il en découle les règles suivantes, applicables au code comme aux textes de l'interface :

- Le vocabulaire de la prévision est proscrit pour les dates futures : « prévision », « il fera ». Les termes retenus sont « simulation », « météo plausible », « scénario ».
- Tout écran affichant une date future comporte un avertissement explicite et visible.
- Aucune assertion d'exactitude portant sur une date déterminée n'est admise.

L'application doit être suffisamment réaliste pour remplir sa fonction pédagogique, et suffisamment explicite sur son statut pour ne pas induire en erreur. Cet arbitrage se pose à chaque décision d'interface.

### Public visé

Public francophone non spécialiste. La compréhension de l'application ne doit supposer aucune connaissance préalable des modèles climatiques.

### Régimes de données

Une requête peut couvrir simultanément le passé et le futur. L'application combine alors deux sources de nature différente :

- Passé (1950 → date du jour) : observations issues de réanalyses météorologiques.
- Futur (date du jour → 2050) : sorties d'un modèle climatique.

Les deux sources proviennent d'Open-Meteo. Le choix des modèles est traité en section 2 ; la construction d'une série homogène malgré le changement de source est traitée en section 3.

### Gouvernance des décisions techniques

Tout point technique bloquant est soumis à validation préalable. Le degré d'autonomie diffère toutefois selon le domaine.

**Domaine scientifique et traitement des données — validation obligatoire.** Le porteur du projet est compétent sur ces sujets et en conserve l'arbitrage. Relèvent notamment de ce régime : le choix des modèles climatiques et du scénario d'émissions, les méthodes de correction de biais, la reconstruction de variables absentes des sources, les procédés d'homogénéisation des séries, ainsi que les choix statistiques et les métriques de validation associées. Ces décisions ne sont pas prises unilatéralement : les options sont exposées avec leurs implications et leurs limites, la décision revient au porteur du projet.

**Développement logiciel — autonomie étendue.** L'architecture, le choix des bibliothèques, l'organisation du code et les modalités d'implémentation peuvent être arrêtés sans validation préalable. Les difficultés rencontrées et les compromis notables sont néanmoins signalés.

**Cas mixtes.** Une décision de développement emportant une conséquence scientifique ou statistique relève du premier régime, quelle que soit son apparence technique. Sont notamment concernés : un mécanisme de cache modifiant la granularité temporelle des données, une agrégation ou un arrondi effectué côté interface, un remplissage de valeurs manquantes, ou toute simplification introduite pour des raisons de performance. En cas de doute sur le régime applicable, la validation est requise.

### Conventions de langue

- Code, identifiants, commentaires et messages de commit : anglais.
- Interface et textes destinés à l'utilisateur : français.
- Présent document : français ; traduction en anglais prévue ultérieurement.

### État du dépôt

Un prototype antérieur (Flask, JavaScript) subsiste dans `src/meteo_app/`, accompagné d'un script manuel dans `notebooks/`. Il ne constitue pas une base : les décisions consignées dans le présent document ne sont pas contraintes par son implémentation. Il la contredit d'ailleurs sur plusieurs points — modèle climatique dépourvu de nébulosité, endpoint d'archive par défaut, logique de découpage dupliquée entre JavaScript et Python, géocodage par Nominatim.

**Autorisation permanente : ce prototype peut être supprimé, réécrit ou réorganisé sans validation préalable.** L'autorisation couvre `src/meteo_app/`, `notebooks/`, ainsi que les fichiers de packaging et le `README.md` qui s'y rapportent. Elle vaut pour toute session, sans qu'il soit nécessaire de la redemander. L'ensemble étant versionné, la suppression reste réversible par l'historique Git.

Cette autorisation porte sur le code hérité, non sur le présent document ni sur `scripts/verification/`.

Les faits chiffrés cités dans les sections 2, 3 et 4 sont établis par les scripts de `scripts/verification/`, exécutables isolément et sans dépendance. Leur `README.md` indique ce que chacun démontre. Toute valeur contestée doit être remesurée par le script correspondant, puis corrigée dans le présent document — jamais ajoutée à côté de l'ancienne.

---

## 2. Scientifique

### Sources

Deux jeux de données, tous deux exposés par Open-Meteo :

- **Passé** — *Historical Weather API*, réanalyses ERA5 (0,25°, depuis 1940) et ERA5-Land (0,1°, depuis 1950).
- **Futur** — *Climate API*, modèles CMIP6 du protocole HighResMIP (Haarsma et al., 2016), corrigés de leur biais et ramenés à une grille de 10 km par Open-Meteo.

Ce choix tient à l'homogénéité de format des deux jeux et à l'absence de clé d'accès pour un usage non commercial. Il n'est pas définitif : d'autres sources sont envisageables (voir *Améliorations envisagées*).

### Couverture, vérifiée le 31 juillet 2026

| | Historical API | Climate API |
|---|---|---|
| Période | 1940-01-01 → veille du jour courant | 1950-01-01 → 2050-12-31 |
| Hors bornes | — | HTTP 400, « Invalid date » |
| Pas de temps | horaire et journalier | journalier seulement |
| `weather_code` | disponible | **valeurs nulles, sans erreur** |

Variables non nulles dans les deux sources : températures (max, min, moyenne), précipitations (totales, pluie, neige), nébulosité moyenne, rayonnement, humidité relative, vent, pression au niveau de la mer, point de rosée. Réservées à l'historique : `weather_code`, `sunshine_duration`, `precipitation_hours`, évapotranspiration, température ressentie.

L'API Climate accepte le paramètre `weather_code`, répond HTTP 200 et renvoie des valeurs nulles assorties d'une unité `undefined`. L'absence est donc silencieuse : tout code appelant doit la détecter explicitement plutôt que se fier au statut HTTP.

### Modèle retenu

Deux des sept modèles sont écartés pour indisponibilité de données, non par arbitrage :

- `CMCC_CM2_VHR4` — ne fournit aucune valeur de nébulosité. C'est le modèle utilisé par défaut dans le prototype initial.
- `EC_Earth3P_HR` — ne couvre pas l'année 2050.

Les cinq restants couvrent 1950-2050 sur l'ensemble des sites testés. **`MRI_AGCM3_2_S` est retenu à titre provisoire**, pour sa résolution native la plus fine (20 km).

Ce choix reste à confirmer par comparaison sur la période de recouvrement : biais et RMSE sur les températures extrêmes, distribution des précipitations, fréquence des jours de pluie, variance jour à jour, sur des sites de climats contrastés. Le modèle doit demeurer paramétrable, sans valeur codée en dur.

### Scénario d'émissions

L'API Climate n'expose aucun sélecteur de scénario. Les paramètres `scenario`, `ssp` et `experiment` sont acceptés sans erreur mais demeurent sans effet : les valeurs renvoyées sont identiques quelle que soit la demande. La seule trajectoire disponible approche RCP8.5, soit une hypothèse d'émissions haute. Sa lecture courante comme scénario tendanciel est contestée : elle a été conçue pour explorer un futur à risque élevé et peu probable, non pour décrire la trajectoire attendue (Hausfather & Peters, 2020). Ce statut doit être explicite dans l'interface.

### Statut de la référence

ERA5 n'est pas une mesure, mais une réanalyse : un modèle météorologique contraint par assimilation d'observations. Là où celles-ci sont denses, il s'en approche ; ailleurs, il produit surtout du modèle.

La distinction est déterminante, car ERA5 sert de référence à toute évaluation du modèle climatique menée dans ce projet. Ses propres erreurs sont donc, par construction, invisibles à nos comparaisons.

### ERA5 et ECMWF IFS : deux instruments, non deux degrés de justesse

L'*Historical Weather API* expose une troisième source, `ecmwf_ifs` : l'analyse opérationnelle d'ECMWF, à 9 km, disponible **du 1er janvier 2017 au jour même, sans latence**, là où ERA5 et ERA5-Land accusent cinq à six jours de retard. Elle sert les huit variables du projet sans valeur nulle, en une seule requête.

L'écart entre les deux sources n'est documenté nulle part sous forme chiffrée : la littérature compare chaque système aux observations de surface, jamais l'un à l'autre. Il a donc été mesuré ici (script 19), sur quatre sites français et sept années. Trois mécanismes l'expliquent.

**La résolution.** ERA5 tourne à 31 km avec le cycle 41r2 d'IFS, figé en 2016 ; l'IFS opérationnel tourne à 9 km. Une maille de 31 km centrée sur Pontarlier moyenne la vallée du Doubs avec les plateaux voisins : au 1er janvier 2017, ERA5 y donne 0,2 °C de température maximale contre 5,4 °C pour IFS. À Paris, où il n'y a pas de relief à résoudre, les deux donnent 0,9 °C. L'écart est géométrique, non physique.

**La correction d'altitude d'ERA5-Land.** ERA5-Land n'est pas une réanalyse indépendante mais le modèle de surface rejoué à 11 km, forcé par l'atmosphère d'ERA5 et corrigé par un gradient thermique vertical quotidien (Muñoz-Sabater et al., 2021). Il corrige donc précisément le défaut d'altitude qui fait diverger ERA5. D'où le classement observé sur la température : IFS ≈ ERA5-Land ≠ ERA5. Ce constat conforte après coup le forçage d'ERA5-Land retenu en section 3.

**Les montées de version.** ERA5 rejoue quatre-vingts ans avec une seule version du modèle. IFS change une à deux fois par an. Or ECMWF annonce explicitement, d'une version à l'autre, l'amélioration des champs de vent et de température près de la surface — soit exactement ceux sur lesquels les deux sources divergent le plus. La série IFS porte donc ses propres ruptures internes, aux dates de mise à jour.

Il en résulte qu'aucune des deux sources n'est « plus fausse » dans l'absolu : ni l'une ni l'autre n'est une mesure, et la question n'a de sens qu'au regard de l'usage. Pour restituer un point un jour donné, en terrain complexe surtout, IFS est meilleur — il voit le relief. Pour comparer deux dates séparées de décennies, ERA5 est meilleur — il ne change pas d'instrument en chemin. Open-Meteo tranche d'ailleurs dans le même sens : *« when studying climate change over decades, it is advisable to exclusively utilise ERA5 or ERA5-Land »*.

Amplitude de l'écart, sur 2018-2024 : moins de 1 °C sur les températures, moins de 1 mm par jour sur les précipitations, moins de 1 point de nébulosité hors montagne. Deux exceptions. Le **vent** décale de −3,1 à +3,3 km/h selon le site, avec changement de signe — Brest vers le bas, Pontarlier vers le haut — soit le quart de la valeur. Et la **haute montagne** dégrade tout : à Chamonix, −5,2 points de nébulosité et +1,8 °C sur la température maximale hivernale. L'écart de température varie en outre avec la saison, ce qui interdit de le corriger par un décalage unique.

### Limites

Les mesures citées ci-dessous reposent sur un nombre restreint de sites et de périodes. Elles établissent des motifs, non des amplitudes valables en tout point. L'échantillon est appelé à être élargi.

**1. Aucun code météorologique pour le futur.** La variable existe dans l'historique mais pas dans les projections. L'aspect du ciel doit être reconstruit à partir des autres variables ; les modalités relèvent de la section 3.

**2. Nébulosité sous-estimée deux fois.** Le modèle est en retrait d'ERA5 sur tous les sites testés — de −5,1 points à Pontarlier à −30,2 à Singapour, en passant par −8,1 à Brest, −10,2 à Marseille, −6,7 à Reykjavik et −21,2 à Bamako. Ces valeurs sont mesurées contre ERA5 explicitement forcé : l'endpoint par défaut sélectionne sa source variable par variable et bascule vers ECMWF IFS en 2017, ce qui fausse toute comparaison. L'écart n'est donc ni local ni imputable au relief : Pontarlier est le site le moins touché. Il est en revanche stable dans le temps, les valeurs 2041-2050 étant indiscernables de l'historique du modèle, ce qui le rend calibrable sur la période de recouvrement. Les réanalyses sont par ailleurs elles-mêmes en retrait des observations de surface — constat établi en Méditerranée sur ERA-Interim et MERRA, antérieurs à ERA5 (Enriquez-Alonso et al., 2015). L'extrapolation à ERA5 n'est donc pas démontrée, mais si elle se vérifie, les deux erreurs s'additionnent dans le même sens.

**3. Précipitations lissées par ERA5.** La réanalyse surestime les pluies faibles et le nombre de jours pluvieux, et sous-estime les épisodes intenses (Lavers et al., 2022). Deux mécanismes se cumulent. D'abord l'agrégation spatiale : une maille de 30 km ne livre qu'une moyenne, dans laquelle une cellule convective de quelques kilomètres est diluée par construction. Ensuite la paramétrisation de la convection, non résolue explicitement, que les schémas déclenchent trop souvent et trop longtemps à intensité trop faible — biais documenté sur les modèles de climat, où il s'aggrave à mesure que la résolution se dégrade (Chen et al., 2021). Les épisodes orageux ne sont donc pas absents, mais représentés de façon diffuse. Conséquence directe : les cumuls journaliers sont exploitables, les intensités ne le sont pas.

**4. Correction de biais restreinte à la moyenne.** Le procédé appliqué par Open-Meteo — correction linéaire à coefficients mensuels — ajuste la moyenne mensuelle sans corriger la variance ni les extrêmes. Nos mesures le confirment : les écarts de moyenne sur la température restent inférieurs à 0,35 °C, tandis que les rapports d'écart-type s'échelonnent de 0,61 à 1,41 selon la variable et le site.

**5. Extrêmes de température et sécheresses : aucun déficit constaté.** Contrairement à ce qu'on pouvait craindre, le modèle produit sur la période de recouvrement *davantage* de jours chauds que l'observation, davantage de vagues de chaleur d'au moins trois jours, et des sécheresses maximales plus longues. L'autocorrélation d'ordre 1 des températures est reproduite à 0,01 près : la persistance temporelle tient. Deux réserves : le test chevauche la période d'ajustement des coefficients de correction, donc flatte le modèle ; et il ne dit rien de l'amplification future des extrêmes, invérifiable par nature. Aucune correction n'est appliquée sur ce point — en introduire une là où la mesure n'établit pas de déficit reviendrait à injecter une erreur.

**6. Modèle unique et phénomènes non résolus.** Retenir une seule sortie interdit toute estimation de l'incertitude inter-modèles. Or aux échéances proches, celle-ci et la variabilité interne l'emportent sur l'incertitude de scénario (Hawkins & Sutton, 2009) — c'est-à-dire que le choix du modèle pèse ici davantage que celui de la trajectoire d'émissions. Par ailleurs, malgré une grille ramenée à 10 km, la résolution effective reste celle de la maille d'origine : orages, brouillards de vallée et effets de relief fins ne sont pas représentés. La descente d'échelle recale et redistribue, elle n'ajoute pas d'information.

**7. Asymétrie de résolution temporelle.** L'historique est disponible au pas horaire, les projections au pas journalier seulement. Toute grandeur dérivée doit donc être construite à partir d'agrégats journaliers des deux côtés, sous peine de rupture à la date du jour. C'est la contrainte structurante de la section 3.

### Améliorations envisagées

- Correction du biais de nébulosité par calibration sur la période de recouvrement.
- Enveloppe d'incertitude fondée sur l'écart entre les cinq modèles éligibles, sans renoncer à l'affichage d'une trajectoire unique.
- Comparaison aux projections régionalisées DRIAS de Météo-France, mieux évaluées sur la France, et à la trajectoire de référence TRACC.
- Ouverture à d'autres scénarios d'émissions, ce qui suppose de changer de source.

### Références

- Chen, D., Dai, A. & Hall, A. (2021). The convective-to-total precipitation ratio and the « drizzling » bias in climate models. *Journal of Geophysical Research: Atmospheres*. [10.1029/2020JD034198](https://doi.org/10.1029/2020JD034198) — *porte sur les modèles CMIP5, non sur ERA5.*
- Enriquez-Alonso, A. et al. (2015). Cloud cover climatologies in the Mediterranean obtained from satellites, surface observations, reanalyses, and CMIP5 simulations. *Climate Dynamics*. [10.1007/s00382-015-2834-4](https://doi.org/10.1007/s00382-015-2834-4) — *porte sur ERA-Interim et MERRA, antérieurs à ERA5.*
- Haarsma, R. J. et al. (2016). High Resolution Model Intercomparison Project (HighResMIP v1.0) for CMIP6. *Geoscientific Model Development*, 9, 4185-4208. [10.5194/gmd-9-4185-2016](https://doi.org/10.5194/gmd-9-4185-2016)
- Hausfather, Z. & Peters, G. P. (2020). Emissions – the « business as usual » story is misleading. *Nature*, 577, 618-620. [10.1038/d41586-020-00177-3](https://doi.org/10.1038/d41586-020-00177-3)
- Hawkins, E. & Sutton, R. (2009). The potential to narrow uncertainty in regional climate predictions. *Bulletin of the American Meteorological Society*, 90, 1095-1107. [10.1175/2009BAMS2607.1](https://doi.org/10.1175/2009BAMS2607.1)
- Lavers, D. A., Simmons, A., Vamborg, F. & Rodwell, M. J. (2022). An evaluation of ERA5 precipitation for climate monitoring. *Quarterly Journal of the Royal Meteorological Society*, 148. [10.1002/qj.4351](https://doi.org/10.1002/qj.4351)
- Muñoz-Sabater, J. et al. (2021). ERA5-Land: a state-of-the-art global reanalysis dataset for land applications. *Earth System Science Data*, 13, 4349-4383. [10.5194/essd-13-4349-2021](https://doi.org/10.5194/essd-13-4349-2021) — *établit la résolution de 9 km et la correction par gradient thermique.*
- ECMWF (2024). IFS upgrade improves near-surface wind and temperature forecasts. *ECMWF Newsletter* 181. [ecmwf.int](https://www.ecmwf.int/en/newsletter/181/earth-system-science/ifs-upgrade-improves-near-surface-wind-and-temperature) — *une montée de version parmi d'autres ; illustre l'inhomogénéité propre à IFS.*
- Open-Meteo. *Historical Weather API — documentation*. [open-meteo.com](https://open-meteo.com/en/docs/historical-weather-api) — *source de la recommandation de n'employer qu'ERA5 ou ERA5-Land pour l'étude du climat sur des décennies, et des latences annoncées.*

---

## 3. Traitement des données

### Principe directeur

Toute grandeur affichée doit être calculée **de façon identique de part et d'autre de la date du jour**. Ce principe prime sur la précision.

Il en découle une règle contre-intuitive : lorsqu'une information n'existe que du côté du passé, elle est écartée plutôt qu'exploitée. Le passé est délibérément ramené au niveau du futur, jamais l'inverse. Une richesse disponible d'un seul côté produirait une rupture à la date du jour, c'est-à-dire exactement l'artefact que cette section a pour objet d'empêcher.

### Sources

Le choix de la source se fait **par variable**, chacune demeurant homogène de 1950 à aujourd'hui.

| Grandeur | Passé | Futur |
|---|---|---|
| Températures min / max | Historical, `models=era5_land` (~11 km) | Climate, `MRI_AGCM3_2_S` (10 km) |
| Précipitations, neige | Historical, `models=era5` (~25 km) | idem |
| Nébulosité | Historical, `models=era5` (~25 km) | idem |
| Vitesse du vent | Historical, `models=era5` (~25 km) | idem |

Période : 1950-01-01 → J−1 pour le passé, J → 2050-12-31 pour le futur.

Le forçage explicite de la source n'est jamais facultatif. L'endpoint par défaut sélectionne la sienne variable par variable et bascule vers ECMWF IFS en 2017, introduisant dans le passé une seconde couture, non documentée, dont l'écart varie de −1,8 à +0,9 °C selon le site, la saison et l'heure du jour. Un décalage constant serait corrigible ; celui-ci ne l'est pas.

Le partage entre les deux réanalyses est contraint et non préférentiel : **ERA5-Land ne sert que les températures**, toutes les autres variables y étant nulles. Cette contrainte coïncide avec le bon choix pour la couture. Les projections ayant été calées sur ERA5-Land, l'écart du modèle à cette réanalyse reste compris entre +0,02 et +0,20 °C sur les sites testés, contre −0,75 à +0,43 °C face à ERA5.

Les deux API rapportent la même altitude pour un point donné, dérivée du même modèle numérique de terrain. La jointure des deux requêtes se fait sur la seule date, sans réconciliation.

### Adresses et paramètres

| Usage | Adresse |
|---|---|
| Passé | `https://archive-api.open-meteo.com/v1/archive` |
| Futur | `https://climate-api.open-meteo.com/v1/climate` |
| Géocodage | `https://geocoding-api.open-meteo.com/v1/search` |

Paramètres communs : `latitude`, `longitude`, `start_date`, `end_date` (format `YYYY-MM-DD`), `daily` (liste), `timezone`, `models` (liste). L'API Climate n'accepte qu'un seul modèle à la fois pour rester homogène avec le reste du dispositif.

Le segment passé exige **deux requêtes**, distinguées par le seul paramètre `models` :

```
models=era5_land  &  daily=temperature_2m_max,temperature_2m_min
models=era5       &  daily=precipitation_sum,rain_sum,snowfall_sum,
                            cloud_cover_mean,wind_speed_10m_max,
                            wind_speed_10m_mean
```

Le segment futur en exige une seule, avec `models=MRI_AGCM3_2_S` et l'ensemble des variables.

Unités renvoyées : températures en °C, précipitations et pluie en mm, **neige en cm**, nébulosité en pourcentage, vent en km/h. L'unité de la neige est une source d'erreur classique, les seuils de la classe de ciel étant exprimés en centimètres.

Aucune clé d'accès n'est requise pour un usage non commercial. Les limites de débit s'appliquent **par adresse IP**, ce qui fonde la répartition client / serveur exposée en section 4.

### Variables retenues

| Grandeur | Traitement |
|---|---|
| Températures min et max | directes des deux côtés |
| Précipitations | cumul journalier, direct des deux côtés |
| Vitesse du vent | directe des deux côtés |
| Direction du vent | **écartée** — valeurs nulles côté Climate |
| Aspect du ciel | **reconstruit**, cinq classes |

### Pourquoi l'aspect du ciel doit être reconstruit

Le `weather_code` d'Open-Meteo n'est pas un produit de réanalyse : c'est une variable dérivée, calculée heure par heure à partir de la nébulosité, des précipitations et de la neige, puis agrégée à la journée **par maximum** — la journée prend le code de son pire moment.

Deux obstacles interdisent de la réutiliser. D'une part elle est nulle côté Climate. D'autre part, l'API Climate ne livre que des agrégats journaliers : appliquée à ceux-ci, la règle d'Open-Meteo ne reproduit son propre résultat que dans 15 % des cas. Deux millimètres tombés en deux heures et les mêmes deux millimètres étalés sur vingt-quatre ne donnent pas le même code, et l'information infra-journalière qui les sépare n'existe pas côté futur.

Réduite à trois familles — sec, pluie, neige — la concordance remonte à 90,7 %. C'est ce signal grossier, et lui seul, qui survit au passage au pas journalier.

### Classe de ciel

Cinq classes, calculées par le même arbre de décision sur les deux régimes, à partir des seuls agrégats journaliers :

1. **Neige** — si cumul de neige ≥ 1 cm
2. **Pluie** — sinon, si cumul de précipitations ≥ 1 mm
3. **Couvert** — sinon, si nébulosité moyenne ≥ 70 %
4. **Nuageux** — sinon, si nébulosité moyenne ≥ 30 %
5. **Dégagé** — sinon

Les seuils de nébulosité sont **provisoires** et doivent être calés sur la distribution observée, de sorte que la fréquence des classes sur la période historique demeure vraisemblable. Les seuils de précipitation reprennent les conventions usuelles du cumul journalier.

Aucune gradation d'intensité n'est proposée : les cumuls journaliers ne portent pas l'information nécessaire pour la fonder. Une bruine et un orage de quarante millimètres reçoivent donc la même classe — appauvrissement assumé, et à réexaminer si la restitution s'en trouve trop pauvre.

### Correction de la nébulosité

C'est la seule correction appliquée. Elle est nécessaire parce que la nébulosité détermine trois des cinq classes et que le modèle la sous-estime systématiquement, de 5,1 à 10,2 points sur les sites français testés. Appliquer les seuils bruts produirait un futur artificiellement ensoleillé.

La correction est calibrée sur la période de recouvrement, mois par mois et par lieu, par transposition de quantiles. La variante à privilégier est celle qui **préserve la tendance** du modèle : une transposition naïve forcerait la distribution future sur la distribution passée et effacerait précisément le signal que l'application cherche à montrer. Le choix de la méthode relève du régime de validation scientifique défini en section 1.

Cette correction est légitime parce que le biais est stable dans le temps : les valeurs du modèle sur 2041-2050 sont indiscernables de son propre historique.

Aucune autre correction n'est appliquée. En particulier, ni les extrêmes de température ni la durée des sécheresses ne sont retouchés, la mesure n'y ayant établi aucun déficit.

### Ordre des opérations

1. Géocodage de la localisation en coordonnées.
2. Découpage de la plage de dates à la date du jour, calculée côté serveur en `Europe/Paris`.
3. Interrogation des API selon le découpage : deux requêtes pour le segment passé, une pour le segment futur.
4. Jointure sur la date des deux requêtes du segment passé.
5. Correction de la nébulosité sur le segment futur.
6. Application de la classe de ciel aux deux segments, par la même fonction.
7. Concaténation et tri chronologique.

L'étape 6 doit être servie par une fonction unique, appelée deux fois. Toute duplication de cette logique rouvrirait la porte à la divergence que la section entière vise à interdire.

### Validation

- Absence de marche à la couture : comparaison des niveaux et des variances de part et d'autre de la date du jour.
- Vraisemblance de la distribution des classes de ciel, comparée à la distribution observée.
- Détection explicite des valeurs nulles. L'API Climate répond `HTTP 200` avec des valeurs nulles pour les variables qu'elle ne sert pas ; se fier au statut HTTP ne suffit pas.

### Limites du dispositif

Le passé mélange deux réanalyses selon la variable : la température ne provient pas du même système physique que la nébulosité. Deux éléments bornent la portée de ce compromis. La classe de ciel demeure cohérente, nébulosité, précipitations et neige provenant toutes trois d'ERA5 ; et la température est affichée seule, sans entrer dans aucune grandeur dérivée.

La symétrie géographique n'est en revanche pas acquise. Elle vaut pour la température, à 11 km contre 10 km, mais non pour le reste : ERA5 est à ~25 km, soit deux fois et demie plus grossier que la grille du futur. Les précipitations et la nébulosité du passé sont donc **moins finement résolues que celles du futur**, à rebours de l'intuition courante.

### Mise en cache

Les deux API limitent le débit — la limite a été atteinte à plusieurs reprises pendant les travaux préparatoires. Une mise en cache est donc nécessaire.

Elle ne doit toutefois ni altérer la granularité temporelle des données ni introduire d'agrégation supplémentaire : conformément à la section 1, un tel choix relèverait du régime de validation scientifique et non du développement.

---

## 4. Spécifications du site

### Nature du site

Un site grand public, volontairement restreint : une page d'accueil portant le formulaire, une page de résultats. Des pages explicatives sur les modèles et la méthode viendront plus tard ; elles seront statiques et peu interactives.

L'objectif de conception est qu'il soit simple d'abord et extensible ensuite. Chaque brique est donc pensée pour être remplacée sans que les autres bougent.

### Répartition entre client et serveur

**Les données sont récupérées par le navigateur**, y compris le géocodage. Le motif n'est pas le volume — une plage de 90 jours pèse 4 Ko — mais le fait que **les limites d'Open-Meteo s'appliquent par adresse IP**. Un serveur qui interrogerait les API concentrerait toute l'affluence sur une seule adresse et atteindrait la limite immédiatement. Nous l'avons atteinte à plusieurs reprises depuis un seul poste pendant les travaux préparatoires.

Le géocodage passe par l'API dédiée d'Open-Meteo, et non par Nominatim, dont les conditions d'usage proscrivent les usages intensifs. Le prototype initial utilisait Nominatim.

**Le navigateur ne dérive rien.** Il récupère, il transmet, il affiche. Toute donnée calculée l'est en Python, côté serveur. Cette règle découle directement de la section 3 : la classe de ciel doit être produite par une fonction unique, et le prototype initial montre ce qu'entraîne sa duplication entre JavaScript et Python.

### Architecture

```
Navigateur                          Serveur (Python, sans état)
──────────                          ──────────────────────────
géocodage      → Open-Meteo
données passé  → Open-Meteo
données futur  → Open-Meteo
        │
        └── POST données brutes ──→ validation des entrées
                                    correction de nébulosité (grille)
                                    bloc de transformation
                                    classe de ciel
        ←── JSON journalier ────────┘
```

Le serveur n'expose qu'un seul endpoint utile. Sans état et sans base de données, il monte en charge horizontalement sans effort particulier. Le frontend étant statique, il se diffuse par CDN.

### Organisation du code

```
src/weather_simulator/
    domain/        classe de ciel, seuils, correction de biais
    transform/     bloc de transformation, neutre par défaut
    api/           endpoint, validation des entrées
    calibration/   table de coefficients et interpolation
web/
    static/js/     fetch.js (transport seul), render.js, i18n.js
    templates/     accueil, résultats
```

La séparation entre `domain` et `transform` est délibérée. `domain` porte les règles arrêtées en section 3 et n'a pas vocation à bouger. `transform` est le point de maîtrise sur les données météorologiques : appelé entre la correction et l'affichage, il ne transforme rien par défaut.

### Affichage

Une bande journalière, une carte par jour, défilant horizontalement lorsqu'elle excède la largeur de l'écran.

La plage est bornée à **90 jours**, soit une saison. La contrainte est appliquée à la fois dans l'interface et dans l'API : jamais dans le seul navigateur.

Chaque journée porte les températures minimale et maximale, le cumul de précipitations, la vitesse du vent et un **pictogramme de la classe de ciel** :

| Classe | Pictogramme |
|---|---|
| Dégagé | ☀️ |
| Nuageux | ⛅ |
| Couvert | ☁️ |
| Pluie | 🌧️ |
| Neige | 🌨️ |

Les émojis conviennent à une première version : disponibles partout, sans ressource à charger, immédiatement lisibles. Deux points en découlent.

Le contrat JSON transporte **la classe, jamais le pictogramme**. Le passage à un jeu d'icônes dessinées, qui corrigerait les variations d'apparence d'une plateforme à l'autre, ne touchera donc que l'affichage.

Chaque pictogramme s'accompagne d'un équivalent textuel, l'émoji seul n'étant pas accessible aux lecteurs d'écran.

Enfin, conformément à la section 1, tout écran affichant une date future porte un avertissement explicite et visible.

### Grille de correction

Les coefficients de correction de nébulosité sont **précalculés hors ligne** et embarqués comme ressource serveur. À la requête, l'application repère les quatre nœuds entourant le point, interpole et applique — sans aucun appel externe.

La grille est définie sur un **réseau mondial fixe** au pas de 0,5°, aux multiples exacts depuis −180° et −90°. Ce point n'est pas négociable : caler l'origine sur la France imposerait de tout recalculer lors du premier élargissement.

Le remplissage est progressif et ordonné par densité de population décroissante — la France d'abord, puis l'Europe, puis les régions les plus peuplées. La collecte est ainsi interruptible et reprenable, et couvre l'essentiel des recherches réelles dès ses premières heures.

Hors de la zone couverte, l'application **refuse la recherche avec un message explicite**. Afficher des données non corrigées reviendrait à montrer un futur artificiellement ensoleillé, ce qui n'est pas neutre ; se rabattre sur le nœud le plus proche serait silencieux et trompeur.

La table porte ses propres métadonnées : emprise, maille, période de calibration, date de génération.

### Montée en charge

Le poste coûteux — l'interrogation des API météorologiques — est reporté sur les clients, ce qui répartit la charge et contourne la limitation par adresse IP.

Il ne reste côté serveur qu'un calcul sans état portant sur 90 lignes au plus, et une lecture de table en mémoire. Aucune base de données n'est nécessaire. La montée en charge se fait donc par simple multiplication des instances, derrière un frontend statique servi par CDN.

### Préparé sans être construit

**L'internationalisation** : tous les textes visibles sont extraits dans un dictionnaire dès le départ. L'opération est triviale maintenant et coûteuse plus tard.

**Le contrat JSON de sortie** : un tableau d'objets journaliers, stable et documenté. Un graphique de températures, un cumul de précipitations ou une carte s'y brancheront sans toucher au pipeline.

**Les pages explicatives** : statiques, elles ne demandent aucune infrastructure particulière.

### Choix techniques

FastAPI plutôt que Flask : validation des entrées par Pydantic, documentation OpenAPI automatique, meilleur ajustement à une API JSON sans état.

JavaScript natif en modules ES, sans cadriciel. Deux pages ne le justifient pas, et l'absence de chaîne de compilation garde le projet abordable. Les frontières de modules sont posées de sorte qu'une migration reste possible si le site s'étoffe.
