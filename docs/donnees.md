# Données — de l'API à la série homogène

**Comment obtenir une série journalière homogène de 1950 à 2050 en un point
donné.** Ce document fait foi sur ce sujet et sur lui seul.

Ailleurs : pourquoi ce modèle et cette référence → [`science.md`](science.md) ;
ce qu'on dérive ensuite de ces données → [`regles.md`](regles.md).

---

## 1. Quatre segments, cinq requêtes

Une plage demandée est découpée en quatre segments. Chacun a sa source. Une
requête n'appelle que les segments qu'elle recoupe.

| Segment | Période | Source | Résolution |
|---|---|---|---|
| Passé ancien | 1950-01-01 → dernier jour servi par les réanalyses | `era5_land` (températures) **+** `era5` (le reste) | 11 km / 25 km |
| Passé récent | lendemain de cette borne → aujourd'hui | `ecmwf_ifs` | 9 km |
| Prévision | demain → J+14 | `ecmwf_ifs025` | 25 km |
| Futur | lendemain du dernier jour servi par la prévision → 2050-12-31 | `MRI_AGCM3_2_S` | 10 km |

Le passé ancien coûte **deux** requêtes parce que la source se choisit *par
variable* : ERA5-Land ne sert que les températures, tout le reste y est nul.
Les deux réponses se joignent sur la seule date.

Le passé récent existe parce que les réanalyses ont **5 à 6 jours de retard**.
Sans lui, toute requête touchant aujourd'hui finirait par un trou d'une semaine.

La prévision existe parce qu'un modèle climatique **n'est pas initialisé sur
l'état de l'atmosphère** : sa première journée simulée est aussi étrangère à la
météo de demain que la dernière l'est à 2050. Servi par le modèle, J+1 se lisait
donc comme une prévision fausse — et à la différence de 2046, le lecteur peut
vérifier demain.

**Ce n'est pas un quatrième segment de plein droit, c'est le segment IFS qui va
plus loin.** Même système de part et d'autre d'aujourd'hui : l'archive jusqu'à
ce soir, la prévision ensuite. **Ce soir n'est donc pas une couture** — il y en a
toujours deux, et la seconde s'est déplacée à la fin de la prévision.

Les deux produits ne sont pas identiques pour autant : l'archive sert une
*analyse* à 9 km, la prévision une *intégration vers l'avant* à 0,25°. L'écart
mesuré à cette jonction → [`science.md`](science.md) et
`scripts/forecast_seam/`.

| Usage | Adresse |
|---|---|
| Passé (réanalyses et IFS) | `https://archive-api.open-meteo.com/v1/archive` |
| Prévision | `https://api.open-meteo.com/v1/forecast` |
| Futur | `https://climate-api.open-meteo.com/v1/climate` |
| Géocodage | `https://geocoding-api.open-meteo.com/v1/search` |

---

## 2. Paramètres

Communs aux cinq requêtes : `latitude`, `longitude`, `start_date`, `end_date`
(`YYYY-MM-DD`), `daily`, `models`, `timezone`. L'endpoint de prévision accepte
`start_date`/`end_date` comme les deux autres, ce qui permet de construire les
cinq requêtes par la même fonction.

```
models=era5_land      daily=temperature_2m_max,temperature_2m_min,temperature_2m_mean
models=era5           daily=precipitation_sum,snowfall_sum,cloud_cover_mean,
                            wind_speed_10m_max,wind_speed_10m_mean
models=ecmwf_ifs      daily=<les huit>
models=ecmwf_ifs025   daily=<les huit>          (API Forecast)
models=MRI_AGCM3_2_S  daily=<les huit>          (API Climate)
```

Trois règles sans exception :

- **`timezone=auto`** partout. Les deux API réagrègent les journées selon ce
  paramètre — à Singapour, la série se décale d'un jour entier entre `GMT` et
  l'heure locale. Une couture ne tient que si ses deux côtés sont découpés à la
  même heure.
- **`models` toujours forcé.** Laissé libre, l'endpoint d'archive choisit sa
  source variable par variable et bascule vers IFS en 2017 : une seconde
  couture, non documentée, de −1,8 à +0,9 °C.
- **Une borne de couture se lit dans la réponse**, jamais dans un nombre de jours
  codé en dur, et cela vaut aux **deux** coutures. Côté passé, c'est le dernier
  jour effectivement servi par les réanalyses, IFS reprenant au lendemain : une
  constante serait fausse un jour sur deux. Côté futur, c'est le dernier jour
  effectivement servi par la prévision, qui peut en rendre moins que la
  quinzaine demandée.

  Aucune des deux ne se connaît au moment de bâtir le plan, et le navigateur
  l'exécute d'un seul tenant. Les deux segments qui suivent sont donc **demandés
  en recouvrement** — IFS sur toute la plage post-2017, le modèle climatique dès
  demain — et le chevauchement se règle au retour, la source antérieure
  l'emportant là où elle a servi. Même fonction dans les deux cas.

Aucune clé d'accès. Limites de débit **par adresse IP** — d'où la récupération
côté navigateur en production.

---

## 3. Les huit variables extraites

Huit variables, **toutes au pas journalier** (`daily`), jamais horaire — l'API
Climate ne sert pas l'horaire, et s'en servir côté passé seulement rouvrirait
une couture.

Trois de température, cinq de surface. Le partage n'est pas de commodité : il
décide de quelle requête sert quoi dans le passé ancien.

**Températures — requête `era5_land` dans le passé ancien**

| Nom Open-Meteo | Champ | Unité | Ce que c'est | Usage |
|---|---|---|---|---|
| `temperature_2m_max` | `temperature_max` | °C | maximum de la journée locale à 2 m | affiché |
| `temperature_2m_min` | `temperature_min` | °C | minimum de la journée locale à 2 m | affiché |
| `temperature_2m_mean` | `temperature_mean` | °C | moyenne de la journée locale à 2 m | critère de neige, **non affiché** |

**Surface — requête `era5` dans le passé ancien**

| Nom Open-Meteo | Champ | Unité | Ce que c'est | Usage |
|---|---|---|---|---|
| `precipitation_sum` | `precipitation` | mm | cumul journalier, toutes phases confondues | affiché |
| `snowfall_sum` | `snowfall` | **cm** | cumul journalier de neige, en hauteur tombée | **récupéré, non lu** — *optionnel* |
| `cloud_cover_mean` | `cloud_cover` | % | nébulosité totale, moyenne des 24 heures | classe de ciel |
| `wind_speed_10m_max` | `wind_speed_max` | km/h | vent **établi** le plus fort — pas la rafale | affiché |
| `wind_speed_10m_mean` | `wind_speed_mean` | km/h | vent moyen sur la journée à 10 m | **servi, non affiché** → [`application.md`](application.md) |

**Les segments récent (`ecmwf_ifs`), prévision (`ecmwf_ifs025`) et futur
(`MRI_AGCM3_2_S`) demandent les huit d'un coup**, en une requête chacun : les
trois sources les servent toutes. Vérifié sur la prévision, `cloud_cover_mean`
et `temperature_2m_mean` comprises, qui étaient les deux à craindre.

Trois précisions qui coûtent cher si on les découvre en route :

- **La neige est en centimètres**, quand tout le reste des précipitations est en
  millimètres.
- **`temperature_2m_mean` n'est pas affichée.** Elle n'est demandée que parce
  que le critère de neige en dépend, et les quatre sources la servent,
  ERA5-Land compris.
- **`snowfall_sum` est la seule variable dont l'absence est tolérée** : le
  modèle climatique la sert par plages manquantes, ni saisonnières ni
  régulières. Elle est conservée comme témoin, mais rien n'en dépend. Toute
  autre variable absente est une erreur.

**Écartées, et pourquoi :**

| Variable | Motif |
|---|---|
| `rain_sum` | inutilisée, et trouée comme la neige |
| `wind_direction_10m_dominant` | nulle côté Climate |
| `wind_gusts_10m_max` | servie par les trois sources, mais non retenue pour l'instant |
| `weather_code` | nulle côté Climate |
| `sunshine_duration` | non servie côté Climate |
| `shortwave_radiation_sum` | sert au calage hors ligne, pas à la requête |

**Principe qui commande tout le reste :** une grandeur disponible d'un seul côté
est écartée, jamais exploitée. Le passé est ramené au niveau du futur.

---

## 4. Les pièges de l'API

**L'absence est silencieuse, et de deux manières.** L'API Climate accepte
`weather_code`, répond HTTP 200 et renvoie une colonne entière de `null` avec
une unité `undefined`. Elle accepte de même `hourly` et `temporal_resolution`,
répond HTTP 200, et ne renvoie aucun bloc horaire. **Le statut HTTP ne dit rien
— l'absence doit être détectée explicitement.**

**Deux sortes de nul, à ne pas confondre :**

- une variable qu'une source ne sert *jamais* → erreur ;
- une journée qu'elle n'a *pas encore* rattrapée → normal, on la retire de la
  queue pour qu'une autre source la couvre.

Seules les journées où *toutes* les variables manquent sont retirées, de sorte
qu'une variable absente d'un bout à l'autre reste signalée au lieu d'être
rognée en silence.

**Les noms de retour varient.** Demandé un seul modèle, l'API renvoie le nom nu
(`temperature_2m_max`) ; le suffixe (`temperature_2m_max_MRI_AGCM3_2_S`)
n'apparaît que si plusieurs modèles sont demandés. Les deux graphies sont
acceptées à la lecture.

**La neige est en centimètres**, pas en millimètres.

**Le transport lâche autrement qu'en HTTP** — voir la docstring de
`sources/client.py` : tout échec de transport est réessayé, 429 et 503 compris.

---

## 5. Ordre des opérations

1. Géocodage de la localisation.
2. Découpage de la plage à la date du jour, calculée côté serveur en
   `Europe/Paris` — ce fuseau ne fixe que *quel jour on est*, l'agrégation des
   journées suivant le lieu (`timezone=auto`). Aujourd'hui appartient à
   l'observé.
3. Passé ancien : deux requêtes, jusqu'à la veille au plus tard.
4. Jointure sur la date, et retrait des journées de queue qu'aucune des deux ne
   sert encore.
5. IFS du lendemain de cette borne jusqu'à aujourd'hui, si la plage y va.
6. Modèle climatique à partir de demain, si la plage y va.
7. Concaténation et tri chronologique.

Chaque journée porte son `origin` (`observed` / `forecast` / `simulated`) et sa
`source` (pour le diagnostic des coutures). Les trois régimes ne diffèrent
**que** par ces champs — jamais par les champs renseignés, jamais par la façon
de les calculer.

`forecast` n'est pas un troisième genre de série : c'est la queue du même
passage d'IFS qui sert le passé récent. Ce qui l'écarte d'`observed` n'est pas
l'instrument, c'est le temps — ces journées n'ont pas eu lieu. La distinction
porte : la correction de l'étape 4 ne s'applique qu'aux journées `simulated`, et
l'interface doit avertir sur celles-là sans avertir sur les autres.

Ce qui vient après — correction de nébulosité sur le seul segment futur, puis
classe de ciel appliquée aux quatre segments par une fonction unique — sort du
cadre de ce fichier.

---

## 6. Deux propriétés à connaître du segment récent

- **La valeur du jour courant est provisoire** : la journée n'étant pas finie,
  son agrégat comporte une part de prévision et bouge d'un passage du modèle au
  suivant (29,8 → 30,5 °C à Marseille en quelques dizaines de minutes).
- **Une journée récente change de source après coup** : servie par IFS
  aujourd'hui, elle le sera par la réanalyse dans 5 ou 6 jours, avec une valeur
  légèrement différente.

---

## 7. Mise en cache

Nécessaire : les deux API limitent le débit **par adresse IP**, et la limite a
été atteinte à plusieurs reprises depuis un seul poste.

**Il vit dans le navigateur**, la récupération s'y étant déplacée
→ [`application.md`](application.md). Ce n'est pas un pis-aller : la limite se
comptant par adresse, un cache par visiteur épouse exactement l'unité à laquelle
le quota s'épuise. Un cache serveur ne protégerait plus personne, le serveur
n'appelant plus les API. **Rien n'est fait à ce jour.**

**La durée de conservation ne peut pas être uniforme**, et c'est la conséquence
directe de la section précédente :

| Segment | Conservation |
|---|---|
| Passé ancien | indéfinie — figé |
| Futur | indéfinie — un modèle climatique ne change pas d'avis |
| Jours récents | courte — la valeur bouge, puis change de source |

Servir une valeur périmée sur ces derniers jours ferait réapparaître dans le
cache la marche que tout le dispositif s'emploie à supprimer dans les données.

Le cache ne doit **ni altérer la granularité temporelle ni introduire
d'agrégation** : un tel choix relèverait de la validation scientifique et non du
développement.

---

## 8. Limites de la chaîne

**Le passé ancien mélange deux réanalyses selon la variable.** La température ne
vient pas du même système physique que la nébulosité. Le coût était nul tant que
la classe de ciel ne lisait qu'ERA5 ; le critère de neige y fait maintenant
entrer la température moyenne, donc ERA5-Land, et la règle confronte deux
systèmes sur ce seul segment. La portée reste bornée — la règle ne se déclenche
que sur les jours humides et froids, et les deux réanalyses s'accordent à mieux
d'un demi-degré en plaine. L'asymétrie disparaîtrait si ERA5-Land servait les
précipitations, ce qu'il ne fait pas.

**La résolution n'est pas monotone le long de la série**, à rebours de
l'intuition : IFS 9 km, ERA5-Land 11 km, futur 10 km, ERA5 **25 km**. Les
précipitations et la nébulosité du passé ancien sont donc *moins* finement
résolues que celles du futur.

---

## 9. Où c'est, dans le code

| Fichier | Rôle |
|---|---|
| `sources/openmeteo.py` | adresses, modèles, variables, construction des requêtes |
| `sources/client.py` | GET JSON, réessais, débit |
| `sources/parse.py` | lecture des payloads, nuls silencieux, jointure |
| `sources/series.py` | découpage de la plage, assemblage des quatre segments |
| `sources/errors.py` | `FetchError`, `MissingVariableError`, `CoverageError` |
| `domain/records.py` | `DailyRecord`, `Origin`, unités |
| `scripts/inspect_seam.py` | lecture des coutures sur requête réelle |
