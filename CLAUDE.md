# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> Document en cours de rédaction. Sections rédigées : 1, 2, 3, 4.

---

## Avancement

Les étapes 0, 1 et 2 sont faites. Le dépôt contient le présent document, `scripts/verification/`, `scripts/model_selection/`, et le paquet `src/weather_simulator/`, dont `sources/` récupère et assemble la série homogène de 1950 à 2050. La classe de ciel, la correction de nébulosité et l'API restent à écrire.

L'enchaînement ci-dessous fixe **l'ordre**, imposé par les dépendances, et non le contenu de chaque étape — celui-ci se décide au moment de l'aborder, à la lumière de ce que la précédente aura révélé.

| | Étape | Dépend de | État |
|---|---|---|---|
| 0 | Nettoyage du prototype, packaging, `.gitignore` | — | **fait** |
| 1 | Récupération et série homogène, sans classe de ciel | 0 | **fait** |
| 2 | Confirmation du modèle parmi les cinq éligibles | 1 | **fait** |
| 3 | Calage des seuils de nébulosité et classe de ciel | 1 | à faire |
| 4 | Grille de calibration France et correction de nébulosité | 2 | à faire |
| 5 | API, validation des entrées et bloc de transformation | 3, 4 | à faire |
| 6 | Interface : accueil, résultats, bande journalière | 5 | à faire |
| 7 | Élargissement mondial de la grille | 4 | à faire |

La confirmation du modèle venait en deuxième position pour deux raisons : l'étape 1 produisait l'outil qui permettait de la mener, et tout ce qui suit en dépend. Changer de modèle après avoir généré la grille de calibration aurait imposé de la refaire entièrement.

Deux décisions demeurent ouvertes et relèvent du porteur du projet : les seuils de nébulosité de 30 % et 70 %, provisoires ; et la méthode de correction du biais, dont le document exige seulement qu'elle préserve la tendance.

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

Un prototype antérieur (Flask, JavaScript) occupait `src/meteo_app/` et `notebooks/`. **Il a été supprimé à l'étape 0**, l'autorisation permanente qui figurait ici ayant été exercée ; il reste récupérable par l'historique Git. Il contredisait la conception sur tous les points structurants — modèle climatique dépourvu de nébulosité, endpoint d'archive par défaut, logique de découpage dupliquée entre JavaScript et Python, géocodage par Nominatim.

Le dépôt contient désormais :

- `src/weather_simulator/` — `sources/` récupère et assemble la série ; `domain/` porte l'enregistrement journalier et les seuils ; `transform/`, `api/` et `calibration/` attendent leur étape.
- `tests/` — tests hors réseau, l'accès aux API étant injecté.
- `scripts/verification/` — les mesures qui fondent les chiffres du présent document.
- `scripts/inspect_seam.py` — lecture des coutures sur requête réelle.

Les commentaires du code portent la justification des choix et renvoient aux constats du présent document. En cas de divergence entre les deux, **c'est le document qui fait foi** et le code qui doit être corrigé — ou le document amendé, si c'est lui qui a pris du retard.

**`scripts/verification/` et le présent document ne se modifient pas sans validation.** Le reste du code relève de l'autonomie de développement définie plus haut.

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

Les cinq restants couvrent 1950-2050 sur l'ensemble des sites testés. **`MRI_AGCM3_2_S` est retenu**, à l'issue de la comparaison décrite ci-dessous. Il l'était auparavant à titre provisoire, pour sa seule résolution native (20 km, la plus fine des cinq) ; il l'est désormais pour ses résultats. Le modèle demeure paramétrable, sans valeur codée en dur.

### Comment les cinq ont été départagés

La comparaison porte sur 1979-2014, dix sites de climats contrastés, quinze mesures — `scripts/model_selection/`. Les deux bornes sont contraintes : les runs historiques HighResMIP s'arrêtent fin 2014, au-delà de quoi les modèles suivent leur scénario et l'on confondrait le modèle avec son forçage ; et ERA5 avant 1979 est l'extension arrière préliminaire, de qualité moindre, ce qui ferait passer les faiblesses de la référence pour des erreurs de modèle.

**Les critères annoncés dans une version antérieure de ce document — biais et RMSE sur les températures extrêmes — ont dû être abandonnés, tous les deux.**

Le biais est fixé d'avance : Open-Meteo ramène chaque modèle sur ERA5-Land par coefficients mensuels (voir *La correction de biais d'Open-Meteo*), si bien que comparer les moyennes aurait classé ses coefficients et non les modèles. Le RMSE, lui, suppose que les deux séries décrivent les mêmes journées. Elles ne les décrivent pas : les runs HighResMIP sont forcés par les températures de surface océaniques observées mais leur atmosphère est libre, et la corrélation jour à jour des anomalies de température avec la réanalyse vaut 0,04 à Brest, 0,08 à Singapour — nulle. Le modèle ne rejoue pas plus le 14 juillet 1994 qu'il ne prédira le 14 juillet 2046. Un RMSE aurait mesuré cette désynchronisation, totale par construction, et donné à peu près la même valeur pour les cinq.

Ne subsiste que ce qu'une correction linéaire mensuelle laisse intact et qui ne suppose aucune synchronie : la comparaison de deux **populations de journées** sur 36 ans. Deux familles de mesures, appliquées aux mêmes agrégats journaliers que ceux que l'application affiche.

*Dispersion et persistance* — écarts-types des anomalies de température maximale, minimale et de nébulosité ; autocorrélation à j+1 de la température et de la nébulosité ; amplitude du cycle saisonnier ; longueur moyenne et p95 des séquences sèches, longueur moyenne des séquences humides. Les écarts-types et les autocorrélations se calculent sur les **anomalies**, climatologie du jour de l'année retirée : sur les valeurs brutes, l'autocorrélation à j+1 vaut environ 0,97 dans toute série qui a un été et un hiver, et mesurerait le cycle annuel au lieu de la persistance météorologique.

*Forme des distributions* — fréquence des jours humides, intensité moyenne et p99 des jours humides, p99 des anomalies de température maximale, p1 des anomalies de température minimale, étendue interdécile de la nébulosité. Les seuils employés sont ceux de la section 3, non des seuils forgés pour l'occasion.

Le **niveau** de nébulosité est délibérément exclu du classement : le biais y est en partie fabriqué par la correction d'Open-Meteo, et sa correction relève de l'étape 4. Seule la largeur de la distribution est lue, jamais son centre.

### Résultat

Rang moyen sur les dix sites, 1 étant le plus proche de la réanalyse et 5 le plus éloigné ; 3,00 serait le hasard.

| Modèle | Dispersion | Forme | Ensemble |
|---|---|---|---|
| **MRI_AGCM3_2_S** | 2,52 | 2,38 | **2,46** |
| FGOALS_f3_H | 3,16 | 2,99 | 3,09 |
| HiRAM_SIT_HR | 3,00 | 3,23 | 3,09 |
| MPI_ESM1_2_XR | 3,08 | 3,17 | 3,11 |
| NICAM16_8S | 3,24 | 3,23 | 3,24 |

**L'argument décisif n'est toutefois pas la moyenne, et il importe de le dire :** les quatre autres sont indiscernables entre eux, tous au niveau du hasard. Ce qui sépare `MRI_AGCM3_2_S` est **l'absence de site défaillant**. Il est premier ou deuxième sur huit sites sur dix, dernier nulle part, et son plus mauvais site — Strasbourg — le laisse à 3,10. Chacun des quatre autres s'effondre quelque part : NICAM16_8S à 4,60 à Singapour, MPI_ESM1_2_XR à 4,33 à Reykjavik, FGOALS_f3_H à 3,73 à Singapour, HiRAM_SIT_HR à 3,60 à Chamonix. Pour une application qui doit répondre en tout point du globe, c'est la robustesse qui compte, non la performance moyenne.

Deux illustrations. Sous les tropiques, où la référence donne 82,3 % de jours humides à Singapour, FGOALS_f3_H en donne 34,8 points de moins et HiRAM_SIT_HR 21,0 de moins : ils ne font pas la mousson, quand MRI_AGCM3_2_S s'en écarte de 1,4 point. Et NICAM16_8S fabrique des chaleurs qui n'existent pas, son p99 d'anomalie de température maximale dépassant la référence de 7,2 °C à Bamako et de 6,4 °C à Singapour.

Un défaut est en revanche **commun aux cinq**, et ne peut donc pas départager : la nébulosité change trop vite d'un jour au lendemain. Son autocorrélation à j+1 est en retrait sur presque tous les sites, de 0,01 à 0,17 point. Le ciel des modèles papillonne plus que le vrai ; `MRI_AGCM3_2_S` est le moins atteint. À retenir comme limite du dispositif.

**Une indisponibilité découverte à cette occasion :** `FGOALS_f3_H` et `HiRAM_SIT_HR` ne servent jamais `wind_speed_10m_max` — aucune valeur sur 36 ans, aux dix sites. Le vent moyen, lui, est servi par les cinq. L'audit de couverture initial (script 05) ne testait que quatre variables et ne pouvait pas le voir. Le fait est sans conséquence sur le choix retenu, `MRI_AGCM3_2_S` servant les deux, mais il aurait éliminé ces deux modèles d'office.

### Scénario d'émissions

L'API Climate n'expose aucun sélecteur de scénario. Les paramètres `scenario`, `ssp` et `experiment` sont acceptés sans erreur mais demeurent sans effet : les valeurs renvoyées sont identiques quelle que soit la demande. La seule trajectoire disponible approche RCP8.5, soit une hypothèse d'émissions haute. Sa lecture courante comme scénario tendanciel est contestée : elle a été conçue pour explorer un futur à risque élevé et peu probable, non pour décrire la trajectoire attendue (Hausfather & Peters, 2020). Ce statut doit être explicite dans l'interface.

### La correction de biais d'Open-Meteo

Le mécanisme conditionne tout ce que l'on peut mesurer sur ces sorties, et il n'était pas documenté ici. Il a été relevé dans la documentation d'Open-Meteo, puis vérifié en comparant la sortie servie à la sortie brute — le paramètre `disable_bias_correction=true`, non documenté dans nos scripts jusque-là, expose le modèle avant retouche.

**Douze coefficients par variable et par point de grille.** Un par mois du calendrier, non par mois de la série. Pour un point et une variable, on moyenne les cinquante janviers du modèle, on moyenne les cinquante janviers d'ERA5-Land, et l'écart des deux devient le coefficient de janvier. Tout 17 janvier le reçoit ensuite, celui de 1963 comme celui de 2049.

**La forme diffère selon la variable**, et la mesure la tranche sans ambiguïté : si l'écart corrigé−brut est constant sur le mois, la correction est additive ; si c'est le rapport, elle est multiplicative.

| Variable | Écart, écart-type | Rapport, écart-type | Nature |
|---|---|---|---|
| Température maximale | ±0,05 °C | ±5,5 | **additive**, +2,2 à +3,0 °C selon le mois |
| Précipitations | ±2,7 mm | ±0,001 | **multiplicative**, ×0,78 à ×0,83 |
| Vent moyen | ±4,5 km/h | ±0,003 | **multiplicative**, ×0,56 à ×0,59 |
| Nébulosité | ±2,3 pt | ±0,21 | **ni l'une ni l'autre** |

Additif pour une grandeur non bornée, multiplicatif pour une grandeur bornée à zéro : la cohérence est celle qu'on attend.

**La correction est aussi la descente d'échelle.** Trois points distants de 12 km autour de Pontarlier portent des jeux de coefficients entièrement différents — +3,02 °C en janvier au premier, +0,90 au deuxième, −0,04 au troisième — quand le modèle brut leur donne pratiquement la même valeur, tombant dans la même maille native de 20 km. Toute l'information de relief entre 20 et 10 km est portée par le champ de coefficients, non par le modèle. D'où une conséquence pratique : désactiver la correction ne retire pas seulement un décalage, elle rend le modèle aveugle au terrain.

**Trois propriétés commandent le reste du dispositif.**

La correction ne dépend pas de la valeur du jour : un 17 janvier doux et un 17 janvier glacial reçoivent le même décalage. La moyenne bouge, la variance et les extrêmes ne bougent pas — c'est ce qui fonde les critères de départage retenus à l'étape 2.

Elle ne change pas dans le temps : mêmes coefficients en 1980 et en 2046. La stationnarité du biais, que la section 3 postulait pour justifier une calibration sur la période de recouvrement, est donc mécanique et non plus seulement empirique. La tendance survit pour la même raison : un décalage ou un facteur constant par mois ne modifie pas une pente.

Elle introduit enfin **douze petites marches par an**, à date fixe : le 31 mars reçoit +2,94 °C à Pontarlier, le 1ᵉʳ avril +2,51. L'écart est très inférieur au bruit météorologique quotidien, donc invisible sur une carte journalière — mais il est réel, et à garder en mémoire si une moyenne mensuelle ou saisonnière venait à être affichée.

**La nébulosité fait exception, et c'est la variable la plus exposée du projet.** Ni écart ni rapport constant : elle ne reçoit pas de correction linéaire simple au pas journalier. L'explication la plus plausible — hypothèse, non fait établi — est que la correction s'applique au pas horaire et que la nébulosité, seule des quatre à être bornée des *deux* côtés, se fait rogner à 0 et à 100 avant d'être remoyennée sur la journée. Une température ne bute sur rien, une pluie multipliée par 0,8 n'atteint jamais zéro ; un ciel, si. Une partie des écarts relevés à la limite 2 est donc vraisemblablement fabriquée par la correction elle-même plutôt qu'héritée du modèle. Le point est à reprendre à l'étape 4, où la correction de nébulosité se décide.

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

**4. Correction de biais restreinte à la moyenne.** Le procédé appliqué par Open-Meteo — correction linéaire à coefficients mensuels, détaillé ci-dessous — ajuste la moyenne mensuelle sans corriger la variance ni les extrêmes. Nos mesures le confirment : les écarts de moyenne sur la température restent inférieurs à 0,35 °C, tandis que les rapports d'écart-type s'échelonnent de 0,61 à 1,41 selon la variable et le site.

**5. Extrêmes de température et sécheresses : aucun déficit constaté.** Contrairement à ce qu'on pouvait craindre, le modèle produit sur la période de recouvrement *davantage* de jours chauds que l'observation, davantage de vagues de chaleur d'au moins trois jours, et des sécheresses maximales plus longues. L'autocorrélation d'ordre 1 des températures est reproduite à 0,01 près : la persistance temporelle tient. Deux réserves : le test chevauche la période d'ajustement des coefficients de correction, donc flatte le modèle ; et il ne dit rien de l'amplification future des extrêmes, invérifiable par nature. Aucune correction n'est appliquée sur ce point — en introduire une là où la mesure n'établit pas de déficit reviendrait à injecter une erreur.

**6. Modèle unique et phénomènes non résolus.** Retenir une seule sortie interdit toute estimation de l'incertitude inter-modèles. Or aux échéances proches, celle-ci et la variabilité interne l'emportent sur l'incertitude de scénario (Hawkins & Sutton, 2009) — c'est-à-dire que le choix du modèle pèse ici davantage que celui de la trajectoire d'émissions. Par ailleurs, malgré une grille ramenée à 10 km, la résolution effective reste celle de la maille d'origine : orages, brouillards de vallée et effets de relief fins ne sont pas représentés. La descente d'échelle recale et redistribue, elle n'ajoute pas d'information.

**7. Asymétrie de résolution temporelle.** L'historique est disponible au pas horaire, les projections au pas journalier seulement. Toute grandeur dérivée doit donc être construite à partir d'agrégats journaliers des deux côtés, sous peine de rupture à la date du jour. C'est la contrainte structurante de la section 3.

**8. Neige servie par plages manquantes.** Le modèle laisse dans `snowfall_sum` — et dans `rain_sum` — des trous qui ne sont ni saisonniers ni uniformes : 61 jours chaque été à Marseille et à Brest, du 3 juillet au 1er septembre ; la moitié de l'année à Christchurch, hiver austral compris ; aucun à Ushuaia. Ils ne coïncident ni avec les jours secs — 19 jours de pluie mesurée en sont dépourvus — ni avec une saison. Leur ampleur dépend aussi du modèle : `FGOALS_f3_H` ne la sert jamais, `MPI_ESM1_2_XR` en perd 122 jours par an. Les précipitations totales et les températures, elles, sont complètes partout, ce qui fonde le critère dérivé retenu en section 3.

Un échantillon élargi à dix sites, à l'étape 2, apporte deux corrections à ce tableau. Aucun des cinq n'est complet : `NICAM16_8S`, que la mesure initiale donnait pour tel, descend à 83 % à Brest et à Christchurch. Et **aux sites tropicaux — Bamako, Singapour — les cinq servent 0 %** : là où la neige n'a pas d'objet, la variable est absente plutôt que nulle, ce qui n'est pas une défaillance. Ailleurs les taux vont de 50 à 100 % selon le modèle et le lieu.

La complétude n'a finalement pas pesé sur le choix du modèle : la classe de ciel ne lisant plus la neige, seule comptait la complétude des précipitations et des températures, acquise partout et pour les cinq.

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

Toute grandeur affichée doit être calculée **de façon identique sur toute la série**, quelle que soit la source qui a fourni la journée. Ce principe prime sur la précision.

Il en découle une règle contre-intuitive : lorsqu'une information n'existe que du côté du passé, elle est écartée plutôt qu'exploitée. Le passé est délibérément ramené au niveau du futur, jamais l'inverse. Une richesse disponible d'un seul côté produirait une rupture à la couture, c'est-à-dire exactement l'artefact que cette section a pour objet d'empêcher. Le cumul de neige en est l'application la plus coûteuse : mesuré fidèlement dans le passé, il est écarté de la classe de ciel parce que le futur ne le sert qu'irrégulièrement.

La série comportant **deux coutures** et non une, le principe vaut à chacune.

### Sources

La série se compose de **trois segments**, et non de deux. Le choix de la source se fait par segment, et à l'intérieur du passé ancien, par variable.

| Segment | Période | Sources |
|---|---|---|
| Passé ancien | 1950-01-01 → dernier jour servi par les réanalyses | `era5_land` (~11 km) pour les températures, `era5` (~25 km) pour le reste |
| Passé récent | lendemain de cette borne → aujourd'hui | `ecmwf_ifs` (~9 km), toutes variables |
| Futur | demain → 2050-12-31 | `MRI_AGCM3_2_S` (10 km), toutes variables |

**Le troisième segment existe parce que les réanalyses accusent un retard.** Cinq à six jours selon le jour — mesuré à J−5 puis à J−6 à vingt-quatre heures d'intervalle. Sans lui, toute requête touchant aujourd'hui se terminerait par un trou d'une semaine. L'analyse opérationnelle d'ECMWF n'a aucune latence et sert les huit variables en une requête.

**La borne entre les deux passés n'est jamais un nombre de jours codé en dur.** Elle se lit dans la réponse : le dernier jour effectivement servi par les réanalyses, IFS reprenant au lendemain. Une constante serait fausse un jour sur deux.

**IFS n'est délibérément pas employé avant cette borne**, bien qu'il couvre 2017 → aujourd'hui. C'est l'instrument le plus juste au jour le jour, mais il change de version une à deux fois par an : sa série porte ses propres ruptures. Le passé reste donc sur les réanalyses aussi loin qu'elles portent, et l'inhomogénéité se trouve confinée à moins d'une semaine — au lieu de neuf ans si la couture était placée en 2017. Sur cette poignée de jours, l'écart est très inférieur à la variabilité météorologique : à Pontarlier, six jours ne suffisent pas à distinguer un décalage d'un demi-degré du bruit. Le vent fait exception, seul paramètre où il resterait détectable. Le raisonnement complet et les mesures figurent en section 2.

Le forçage explicite de la source n'est jamais facultatif. L'endpoint par défaut sélectionne la sienne variable par variable et bascule vers ECMWF IFS en 2017, introduisant dans le passé une seconde couture, non documentée, dont l'écart varie de −1,8 à +0,9 °C selon le site, la saison et l'heure du jour. Un décalage constant serait corrigible ; celui-ci ne l'est pas.

Le partage entre les deux réanalyses est contraint et non préférentiel : **ERA5-Land ne sert que les températures**, toutes les autres variables y étant nulles. Cette contrainte coïncide avec le bon choix pour la couture. Les projections ayant été calées sur ERA5-Land, l'écart du modèle à cette réanalyse reste compris entre +0,02 et +0,20 °C sur les sites testés, contre −0,75 à +0,43 °C face à ERA5.

Les deux API rapportent la même altitude pour un point donné, dérivée du même modèle numérique de terrain. La jointure des deux requêtes se fait sur la seule date, sans réconciliation.

### Adresses et paramètres

| Usage | Adresse |
|---|---|
| Passé, réanalyses et IFS | `https://archive-api.open-meteo.com/v1/archive` |
| Futur | `https://climate-api.open-meteo.com/v1/climate` |
| Géocodage | `https://geocoding-api.open-meteo.com/v1/search` |

Les deux passés partagent la même adresse et ne se distinguent que par `models`.

Paramètres communs : `latitude`, `longitude`, `start_date`, `end_date` (format `YYYY-MM-DD`), `daily` (liste), `timezone`, `models` (liste). L'API Climate n'accepte qu'un seul modèle à la fois pour rester homogène avec le reste du dispositif.

**`timezone=auto`**, sans exception. Les deux API réagissent à ce paramètre et réagrègent les journées en conséquence : mesuré à Singapour, la série se décale d'un jour entier entre `GMT` et l'heure locale. Le choix est donc libre mais doit être unique — une couture ne tient que si ses deux côtés sont découpés à la même heure. Les journées locales s'imposent parce que l'application affiche un bulletin météorologique : un maximum courant de 9 h à 9 h, ce que `GMT` donnerait à Tokyo, ne signifie rien pour un lecteur. Le prix est une journée de 23 ou 25 heures deux fois l'an, ce qui est exactement ce que le lecteur a vécu. **La grille de calibration de la section 4 doit être calculée sous cette même convention**, et les biais mesurés en `GMT` dans la section 2 ne valent dès lors que comme ordres de grandeur.

Une requête peut donc appeler jusqu'à **quatre requêtes**, et seulement pour les segments qu'elle recoupe :

```
models=era5_land  &  daily=temperature_2m_max,temperature_2m_min,
                            temperature_2m_mean
models=era5       &  daily=precipitation_sum,snowfall_sum,cloud_cover_mean,
                            wind_speed_10m_max,wind_speed_10m_mean
models=ecmwf_ifs  &  daily=<l'ensemble>
models=MRI_AGCM3_2_S  &  daily=<l'ensemble>          (API Climate)
```

`temperature_2m_mean` est demandée parce que le critère de neige en dépend ; les quatre sources la servent, ERA5-Land compris. `rain_sum` n'est **pas** demandée : rien ne l'utilise, et elle porte les mêmes trous que la neige.

Unités renvoyées : températures en °C, précipitations en mm, **neige en cm**, nébulosité en pourcentage, vent en km/h. L'unité de la neige est une source d'erreur classique.

Aucune clé d'accès n'est requise pour un usage non commercial. Les limites de débit s'appliquent **par adresse IP**, ce qui fonde la répartition client / serveur exposée en section 4.

### Variables retenues

| Grandeur | Traitement |
|---|---|
| Températures min et max | directes sur les trois segments |
| Température moyenne | directe ; sert le critère de neige, n'est pas affichée |
| Précipitations | cumul journalier, direct sur les trois segments |
| Vitesse du vent, moyenne et maximale | directes sur les trois segments ; les deux sont affichées |
| Cumul de neige | **récupéré mais non lu** — étalon de calibration, voir plus bas |
| Pluie (`rain_sum`) | **écartée** — inutilisée, et trouée comme la neige |
| Direction du vent | **écartée** — valeurs nulles côté Climate |
| Aspect du ciel | **reconstruit**, cinq classes |

### Pourquoi l'aspect du ciel doit être reconstruit

Le `weather_code` d'Open-Meteo n'est pas un produit de réanalyse : c'est une variable dérivée, calculée heure par heure à partir de la nébulosité, des précipitations et de la neige, puis agrégée à la journée **par maximum** — la journée prend le code de son pire moment.

Deux obstacles interdisent de la réutiliser. D'une part elle est nulle côté Climate. D'autre part, l'API Climate ne livre que des agrégats journaliers : appliquée à ceux-ci, la règle d'Open-Meteo ne reproduit son propre résultat que dans 15 % des cas. Deux millimètres tombés en deux heures et les mêmes deux millimètres étalés sur vingt-quatre ne donnent pas le même code, et l'information infra-journalière qui les sépare n'existe pas côté futur.

Réduite à trois familles — sec, pluie, neige — la concordance remonte à 90,7 %. C'est ce signal grossier, et lui seul, qui survit au passage au pas journalier.

### Classe de ciel

Cinq classes, calculées par le même arbre de décision sur les deux régimes, à partir des seuls agrégats journaliers :

1. **Neige** — si cumul de précipitations ≥ 1 mm **et** température moyenne < 1,5 °C
2. **Pluie** — sinon, si cumul de précipitations ≥ 1 mm
3. **Couvert** — sinon, si nébulosité moyenne ≥ 70 %
4. **Nuageux** — sinon, si nébulosité moyenne ≥ 30 %
5. **Dégagé** — sinon

Les deux premières règles partagent la même porte à 1 mm et partitionnent donc le même ensemble de journées : parmi les jours humides, la température décide de la phase.

**Le cumul de neige n'entre pas dans la règle**, alors qu'il en était la base initiale. Le modèle climatique le sert par plages manquantes, ni saisonnières ni uniformes — 61 jours d'été chaque année à Marseille, la moitié de l'année à Christchurch, hiver austral compris, rien du tout à Ushuaia. La lecture « pas de neige en été » ne survit pas au passage de l'équateur, et la grille a vocation à s'étendre au monde. Comme le passé, lui, sert la neige fidèlement, s'en servir d'un seul côté déplacerait la couture au lieu de la supprimer : la phase est donc déduite de la même façon sur les trois segments.

Le seuil de 1,5 °C est calé sur 35 hivers à Strasbourg et Briançon, contre la profondeur réellement tombée. Il ne l'est pas contre le `weather_code`, qui est le maximum des 24 codes horaires et bascule sur une seule heure de neige : il surestime la neige de 16 points à Strasbourg et sature à Briançon, où 999 jours humides sur 1000 portent un code de neige.

Concordance obtenue : environ 90 % en plaine, 82 % à 1300 m. **La règle sous-appelle la neige en montagne par construction** — au-dessus de 1300 m elle tient au sol même les jours dont la moyenne dépasse 2 °C, parce qu'elle tombe la nuit ou plus haut que la station, et une moyenne journalière ne porte pas cette information. Aucun seuil unique ne convient aux deux sites.

Les seuils de nébulosité sont **provisoires** et doivent être calés sur la distribution observée, de sorte que la fréquence des classes sur la période historique demeure vraisemblable. Le seuil de neige l'est également : deux sites et une seule saison sont une base mince.

Aucune gradation d'intensité n'est proposée : les cumuls journaliers ne portent pas l'information nécessaire pour la fonder. Une bruine et un orage de quarante millimètres reçoivent donc la même classe — appauvrissement assumé, et à réexaminer si la restitution s'en trouve trop pauvre.

### Correction de la nébulosité

C'est la seule correction appliquée. Elle est nécessaire parce que la nébulosité détermine trois des cinq classes et que le modèle la sous-estime systématiquement, de 5,1 à 10,2 points sur les sites français testés. Appliquer les seuils bruts produirait un futur artificiellement ensoleillé.

La correction est calibrée sur la période de recouvrement, mois par mois et par lieu, par transposition de quantiles. La variante à privilégier est celle qui **préserve la tendance** du modèle : une transposition naïve forcerait la distribution future sur la distribution passée et effacerait précisément le signal que l'application cherche à montrer. Le choix de la méthode relève du régime de validation scientifique défini en section 1.

Cette correction est légitime parce que le biais est stable dans le temps : les valeurs du modèle sur 2041-2050 sont indiscernables de son propre historique.

Aucune autre correction n'est appliquée. En particulier, ni les extrêmes de température ni la durée des sécheresses ne sont retouchés, la mesure n'y ayant établi aucun déficit.

### Ordre des opérations

1. Géocodage de la localisation en coordonnées.
2. Découpage de la plage à la date du jour, calculée côté serveur en `Europe/Paris` : l'observation court jusqu'à ce soir inclus, la simulation commence demain. Ce fuseau ne sert qu'à fixer *quel jour on est* — l'agrégation des journées, elle, suit le lieu (`timezone=auto`).
3. Interrogation du passé ancien, deux requêtes, jusqu'à la veille au plus tard.
4. Jointure sur la date de ces deux requêtes, et retrait des journées de queue qu'aucune des deux ne sert encore.
5. Interrogation d'IFS du lendemain de cette borne jusqu'à aujourd'hui, si la plage va jusque-là.
6. Interrogation du modèle climatique à partir de demain, si la plage va au-delà.
7. Correction de la nébulosité sur le seul segment futur.
8. Application de la classe de ciel aux trois segments, par la même fonction.
9. Concaténation et tri chronologique.

L'étape 8 doit être servie par une fonction unique, appelée trois fois. Toute duplication de cette logique rouvrirait la porte à la divergence que la section entière vise à interdire.

L'étape 4 distingue deux sortes de valeur nulle, et c'est essentiel : une variable qu'une source ne sert jamais est une erreur, une journée qu'elle n'a pas encore rattrapée n'en est pas une. Seules les journées où *toutes* les variables manquent sont retirées, de sorte qu'une variable absente d'un bout à l'autre reste signalée au lieu d'être rognée en silence.

### Validation

- Absence de marche **aux deux coutures** : comparaison des niveaux et des variances de part et d'autre de chacune. `scripts/inspect_seam.py` les repère sans les supposer, en suivant le changement de source d'un jour au suivant.
- Continuité de la série : ni trou ni doublon aux raccords, et un jour porte les mêmes champs renseignés quelle que soit la source qui l'a servi.
- Vraisemblance de la distribution des classes de ciel, comparée à la distribution observée.
- Détection explicite des valeurs nulles. L'API Climate répond `HTTP 200` avec des valeurs nulles pour les variables qu'elle ne sert pas ; se fier au statut HTTP ne suffit pas.

### Limites du dispositif

Le passé ancien mélange deux réanalyses selon la variable : la température ne provient pas du même système physique que la nébulosité. Ce compromis coûtait peu tant que la classe de ciel ne lisait qu'ERA5 — nébulosité, précipitations et neige. **Le critère de neige y fait désormais entrer la température moyenne, donc ERA5-Land.** Sur le segment ancien, la règle 1 confronte ainsi deux systèmes distincts, quand les segments IFS et futur la calculent chacun à partir d'une source unique.

La portée reste bornée : la règle ne se déclenche que sur les jours humides et froids, et les deux réanalyses s'accordent à mieux d'un demi-degré en plaine. Mais l'asymétrie est réelle et n'existait pas dans la conception initiale. Elle disparaîtrait si ERA5-Land servait les précipitations, ce qu'il ne fait pas.

La symétrie géographique n'est en revanche pas acquise. Elle vaut pour la température, à 11 km contre 10 km, mais non pour le reste : ERA5 est à ~25 km, soit deux fois et demie plus grossier que la grille du futur. Les précipitations et la nébulosité du passé sont donc **moins finement résolues que celles du futur**, à rebours de l'intuition courante. Le segment IFS, à 9 km, est le plus fin des trois — la résolution n'est donc pas monotone le long de la série.

Deux conséquences du segment récent méritent d'être connues. **La valeur du jour courant est provisoire** : la journée n'étant pas finie, son agrégat comporte une part de prévision, et il bouge d'un passage du modèle au suivant — un maximum observé à Marseille est passé de 29,8 à 30,5 °C en quelques dizaines de minutes. **Et une journée récente change de source après coup** : servie par IFS aujourd'hui, elle le sera par la réanalyse dans cinq ou six jours, avec une valeur légèrement différente. Ces deux points commandent la politique de cache exposée plus bas.

### Mise en cache

Les deux API limitent le débit — la limite a été atteinte à plusieurs reprises pendant les travaux préparatoires. Une mise en cache est donc nécessaire.

Elle ne doit toutefois ni altérer la granularité temporelle des données ni introduire d'agrégation supplémentaire : conformément à la section 1, un tel choix relèverait du régime de validation scientifique et non du développement.

**La durée de conservation ne peut pas être uniforme.** Le passé ancien est figé et se garde indéfiniment ; le futur l'est tout autant, un modèle climatique ne changeant pas d'avis. Les jours récents, eux, bougent deux fois : le jour courant se précise d'un passage du modèle au suivant, et toute journée servie par IFS est remplacée par la réanalyse cinq à six jours plus tard. Servir une valeur périmée pour ces jours-là ferait réapparaître, dans le cache, la marche que le dispositif s'emploie à supprimer dans les données.

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

Chaque journée porte les températures minimale et maximale, le cumul de précipitations, les vitesses de vent moyenne et maximale, et un **pictogramme de la classe de ciel** :

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

**Le vent maximal ne doit pas être libellé « rafale ».** `wind_speed_10m_max` est le plus fort vent *établi* de la journée, moyenné sur l'intervalle du modèle. Une rafale est autre chose, et vaut couramment deux fois plus : mesuré à Pontarlier sur juin 2024, 36,8 km/h de rafale contre 14,4 km/h de vent maximal sous ERA5. Les libellés retenus sont « vent moyen » et « vent maximal ».

La rafale existe pourtant comme variable propre, `wind_gusts_10m_max`, et les trois segments la servent — ERA5, ECMWF IFS et `MRI_AGCM3_2_S`. Elle n'est pas retenue pour l'instant, et son adoption relèverait du régime de validation scientifique : une rafale est par nature un phénomène sous-maille, que la limite 6 de la section 2 place hors de portée d'un modèle à 20 km. La servir donnerait un chiffre juste de forme et faiblement fondé.

Enfin, conformément à la section 1, tout écran affichant une date future porte un avertissement explicite et visible.

### Grille de correction

Les coefficients de correction de nébulosité sont **précalculés hors ligne** et embarqués comme ressource serveur. À la requête, l'application repère les quatre nœuds entourant le point, interpole et applique — sans aucun appel externe.

La grille est définie sur un **réseau mondial fixe** au pas de 0,5°, aux multiples exacts depuis −180° et −90°. Ce point n'est pas négociable : caler l'origine sur la France imposerait de tout recalculer lors du premier élargissement.

Le remplissage est progressif et ordonné par densité de population décroissante — la France d'abord, puis l'Europe, puis les régions les plus peuplées. La collecte est ainsi interruptible et reprenable, et couvre l'essentiel des recherches réelles dès ses premières heures.

Hors de la zone couverte, l'application **refuse la recherche avec un message explicite**. Afficher des données non corrigées reviendrait à montrer un futur artificiellement ensoleillé, ce qui n'est pas neutre ; se rabattre sur le nœud le plus proche serait silencieux et trompeur.

Ce refus ne vaut toutefois que si la plage demandée **comporte un segment futur**. Une requête entièrement passée n'appelle aucun coefficient : la correction ne s'applique qu'aux projections. La refuser serait gratuit, et priverait sans motif un utilisateur de Santiago de l'histoire météorologique de sa ville.

La table porte ses propres métadonnées : emprise, maille, période de calibration, date de génération.

### Montée en charge

Le poste coûteux — l'interrogation des API météorologiques — est reporté sur les clients, ce qui répartit la charge et contourne la limitation par adresse IP.

Il ne reste côté serveur qu'un calcul sans état portant sur 90 lignes au plus, et une lecture de table en mémoire. Aucune base de données n'est nécessaire. La montée en charge se fait donc par simple multiplication des instances, derrière un frontend statique servi par CDN.

### Préparé sans être construit

**L'internationalisation** : tous les textes visibles sont extraits dans un dictionnaire dès le départ. L'opération est triviale maintenant et coûteuse plus tard.

**Le contrat JSON de sortie** : un tableau d'objets journaliers, stable et documenté. Un graphique de températures, un cumul de précipitations ou une carte s'y brancheront sans toucher au pipeline.

**Les pages explicatives** : statiques, elles ne demandent aucune infrastructure particulière.

### Envisagé : la comparaison à l'ancien climat

**Non retenu pour la première version.** Consigné ici parce que le dispositif s'y prête déjà et que quelques constats de mesure risquent sinon d'être perdus.

L'application affiche « 14 juillet 2046 : 21 °C / 39 °C ». C'est plus parlant qu'une anomalie globale, mais 39 °C ne dit quelque chose qu'à qui sait ce qu'était un 14 juillet auparavant — or c'est précisément ce que le lecteur vient chercher. La pédagogie est dans l'écart, pas dans la valeur.

Le principe envisagé : sur la page de résultats, **dès que la plage comporte un segment futur**, un bouton « comparer avec l'ancien climat » affiche sous la bande initiale les **mêmes dates du calendrier** d'une année ancienne, présentée dans le même format. La règle de déclenchement est celle qui gouverne déjà le refus hors grille, pour n'en avoir qu'une à retenir.

**L'année de référence est codée en dur, par grande région.** Une région de la taille de la France ou d'un État américain, avec sa propre année. Aucun calcul à la requête, aucun appel supplémentaire hors la récupération de la météo de cette année-là : une table figée, lue en mémoire, comme celle des coefficients de nébulosité.

Le découpage par grande région n'est pas une commodité. Une année ne peut pas être ordinaire partout : 1980 fut le plus froid des trente étés en France et le vingt-deuxième sur trente à Reykjavik. Le point serait la maille idéale, mais le choisir supposerait de rapatrier trente ans de données pour élire une année, ce que le report de la charge sur le navigateur interdit.

**Trois constats de mesure conditionnent le choix de l'année** (`scripts/model_selection/reference_year.py`, cinq sites français, écarts en écarts-types de la période) :

- **Une année choisie d'intuition se trompe lourdement.** 1980 est à −2,00 en été et −2,14 sur l'année : le plus froid des trente à Marseille, Strasbourg, Pontarlier et Chamonix, le deuxième à Brest. La comparaison y ajouterait un écart artificiel d'environ 2 °C, soit l'ordre de grandeur du réchauffement qu'elle prétend montrer. Symétriquement, 2003 est à +3,25 en été.
- **L'année doit être ordinaire sur plusieurs saisons à la fois.** Une moyenne annuelle centrée peut recouvrir un été chaud compensé par un hiver doux. Sur 1979-1994, la plus ordinaire est **1991** (+0,49 en été, −0,46 en hiver, +0,03 sur l'année) ; sur 1979-2008, **2004** (+0,08 / −0,06 / −0,03).
- **Une référence tardive dépense le signal avant de commencer.** Entre 1979-1988 et 1999-2008, les sites français se réchauffent de **+0,92 °C**. Une année de référence prise dans les années 2000 escamote près d'un degré de ce qu'il s'agit de montrer.

À privilégier, donc : la plus ordinaire de la période la plus ancienne exploitable — ERA5 avant 1979 étant l'extension arrière préliminaire, de qualité moindre.

**Deux exigences d'honnêteté** accompagnent la fonctionnalité, faute de quoi elle induit en erreur :

Le libellé doit dire que l'année a été **choisie pour être ordinaire** — « 1991, une année sans particularité » et non « 1991 ». Le tirage futur, lui, n'est pas sélectionné : il peut porter une canicule. Comparer un tirage libre à un tirage choisi pour sa sagesse laisserait croire que le passé n'avait pas d'extrêmes, alors que c'est la sélection qui les a écartés.

Et la sélection portant sur la seule température, la pluie de l'année retenue est quelconque. Mieux vaut l'assumer que le découvrir.

Enfin, deux bandes de quatre-vingt-dix cartes ne se comparent pas à l'œil. Une ligne de synthèse au-dessus — nombre de journées à 30 °C ou plus de part et d'autre, par exemple — porte ce que les bandes ne peuvent pas porter.

### Choix techniques

FastAPI plutôt que Flask : validation des entrées par Pydantic, documentation OpenAPI automatique, meilleur ajustement à une API JSON sans état.

JavaScript natif en modules ES, sans cadriciel. Deux pages ne le justifient pas, et l'absence de chaîne de compilation garde le projet abordable. Les frontières de modules sont posées de sorte qu'une migration reste possible si le site s'étoffe.
