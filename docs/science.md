# Science — modèles, référence, limites

Ce que valent les données qu'on affiche, et pourquoi ces sources-là. Comment on
les récupère → [`donnees.md`](donnees.md) ; ce qu'on en dérive →
[`regles.md`](regles.md).

Les chiffres cités ici sont établis par `scripts/verification/` et
`scripts/model_selection/`, dont les `README.md` disent ce qui s'y démontre. Une
valeur contestée se remesure par le script, puis se corrige ici — jamais à côté.

---

## Les deux sources

Deux jeux exposés par Open-Meteo, retenus pour l'homogénéité de leur format et
l'absence de clé d'accès en usage non commercial :

- **Passé** — *Historical Weather API* : réanalyses ERA5 (0,25°, depuis 1940) et
  ERA5-Land (0,1°, depuis 1950).
- **Futur** — *Climate API* : modèles CMIP6 du protocole HighResMIP (Haarsma
  et al., 2016), corrigés de leur biais et ramenés à 10 km par Open-Meteo.

Couverture vérifiée le 31 juillet 2026 : l'historique va de 1940 à la veille du
jour courant, le climat de 1950 à 2050, hors bornes en HTTP 400.

---

## Le modèle retenu

Deux des sept sont écartés pour **indisponibilité**, non par arbitrage :
`CMCC_CM2_VHR4` ne fournit aucune nébulosité — c'est celui du prototype initial
— et `EC_Earth3P_HR` ne couvre pas 2050.

**`MRI_AGCM3_2_S` est retenu** parmi les cinq restants. Il demeure paramétrable,
sans valeur codée en dur.

### Comment ils ont été départagés

Dix sites de climats contrastés, 1979-2014, quinze mesures. Les deux bornes sont
contraintes : les runs historiques HighResMIP s'arrêtent fin 2014, au-delà de
quoi l'on confondrait le modèle avec son forçage ; et ERA5 avant 1979 est
l'extension arrière préliminaire, dont les faiblesses passeraient pour des
erreurs de modèle.

**Les deux critères annoncés au départ ont dû être abandonnés.** Le biais est
fixé d'avance — Open-Meteo ramène chaque modèle sur ERA5-Land, si bien que
comparer les moyennes aurait classé ses coefficients. Le RMSE suppose que les
deux séries décrivent les mêmes journées : elles ne les décrivent pas, la
corrélation jour à jour des anomalies valant 0,04 à Brest et 0,08 à Singapour.
Le modèle ne rejoue pas plus le 14 juillet 1994 qu'il ne prédira le 14 juillet
2046.

Ne subsiste que ce qu'une correction linéaire mensuelle laisse intact et qui ne
suppose aucune synchronie : la comparaison de deux **populations de journées**
sur 36 ans, sur les mêmes agrégats journaliers que ceux qu'on affiche.

- *Dispersion et persistance* — écarts-types des anomalies de température et de
  nébulosité, autocorrélation à j+1, amplitude du cycle saisonnier, longueur des
  séquences sèches et humides. Sur les **anomalies**, climatologie du jour
  retirée : sur les valeurs brutes, l'autocorrélation vaut 0,97 dans toute série
  qui a un été et un hiver, et mesurerait le cycle annuel.
- *Forme des distributions* — fréquence et intensité des jours humides, p99 des
  anomalies chaudes, p1 des froides, étendue interdécile de la nébulosité.

Le **niveau** de nébulosité est délibérément exclu : son biais est en partie
fabriqué par la correction d'Open-Meteo. Seule la largeur de la distribution est
lue, jamais son centre.

### Résultat

Rang moyen sur dix sites, 1 étant le plus proche de la réanalyse ; 3,00 serait
le hasard.

| Modèle | Dispersion | Forme | Ensemble |
|---|---|---|---|
| **MRI_AGCM3_2_S** | 2,52 | 2,38 | **2,46** |
| FGOALS_f3_H | 3,16 | 2,99 | 3,09 |
| HiRAM_SIT_HR | 3,00 | 3,23 | 3,09 |
| MPI_ESM1_2_XR | 3,08 | 3,17 | 3,11 |
| NICAM16_8S | 3,24 | 3,23 | 3,24 |

**L'argument décisif n'est pas la moyenne.** Les quatre autres sont
indiscernables entre eux, tous au niveau du hasard. Ce qui sépare
`MRI_AGCM3_2_S` est **l'absence de site défaillant** : premier ou deuxième sur
huit sites, dernier nulle part, son plus mauvais site le laissant à 3,10. Chacun
des quatre autres s'effondre quelque part — NICAM16_8S à 4,60 à Singapour,
MPI_ESM1_2_XR à 4,33 à Reykjavik, FGOALS_f3_H à 3,73 à Singapour, HiRAM_SIT_HR à
3,60 à Chamonix. Pour une application qui doit répondre en tout point du globe,
c'est la robustesse qui compte.

Les effondrements sont de vraies défaillances physiques : à Singapour,
FGOALS_f3_H et HiRAM_SIT_HR manquent 34,8 et 21,0 points de jours humides —
ils ne font pas la mousson, quand MRI_AGCM3_2_S s'écarte de 1,4 point ; et le
p99 de NICAM16_8S dépasse la référence de 7,2 °C à Bamako.

**Un défaut est commun aux cinq**, et ne peut donc pas départager : la nébulosité
change trop vite d'un jour au lendemain, son autocorrélation étant en retrait de
0,01 à 0,17 point sur presque tous les sites. Le ciel des modèles papillonne plus
que le vrai ; `MRI_AGCM3_2_S` est le moins atteint.

---

## Le scénario d'émissions

**Il n'y a pas de choix.** L'API n'expose aucun sélecteur : `scenario`, `ssp` et
`experiment` sont acceptés sans erreur et sans effet. La seule trajectoire
disponible approche RCP8.5, soit une hypothèse haute — conçue pour explorer un
futur à risque élevé et peu probable, non pour décrire la trajectoire attendue
(Hausfather & Peters, 2020). **Ce statut doit être explicite dans l'interface.**

---

## La correction de biais d'Open-Meteo

Le mécanisme conditionne tout ce qu'on peut mesurer sur ces sorties. Relevé dans
la documentation, puis vérifié en comparant la sortie servie à la sortie brute
(`disable_bias_correction=true`).

**Douze coefficients par variable et par point de grille** — un par mois du
calendrier, non par mois de la série. On moyenne les cinquante janviers du
modèle, les cinquante janviers d'ERA5-Land, et l'écart devient le coefficient de
janvier. Tout 17 janvier le reçoit, celui de 1963 comme celui de 2049.

| Variable | Écart, écart-type | Rapport, écart-type | Nature |
|---|---|---|---|
| Température maximale | ±0,05 °C | ±5,5 | **additive**, +2,2 à +3,0 °C |
| Précipitations | ±2,7 mm | ±0,001 | **multiplicative**, ×0,78 à ×0,83 |
| Vent moyen | ±4,5 km/h | ±0,003 | **multiplicative**, ×0,56 à ×0,59 |
| Nébulosité | ±2,3 pt | ±0,21 | **ni l'une ni l'autre** |

Additif pour une grandeur non bornée, multiplicatif pour une grandeur bornée à
zéro : la cohérence est celle qu'on attend.

**La correction est aussi la descente d'échelle.** Trois points distants de
12 km autour de Pontarlier portent des coefficients entièrement différents —
+3,02 °C en janvier, +0,90, −0,04 — quand le modèle brut leur donne
pratiquement la même valeur, tombant dans la même maille native de 20 km. Toute
l'information de relief entre 20 et 10 km est portée par le champ de
coefficients. **Désactiver la correction ne retire pas un décalage : cela rend
le modèle aveugle au terrain.**

**Trois propriétés commandent le reste du dispositif :**

- **La correction ne dépend pas de la valeur du jour.** La moyenne bouge, la
  variance et les extrêmes ne bougent pas — c'est ce qui fonde les critères de
  départage retenus plus haut.
- **Elle ne change pas dans le temps.** Mêmes coefficients en 1980 et en 2046 :
  la stationnarité du biais est mécanique, et la tendance survit, un décalage
  constant ne modifiant pas une pente.
- **Elle introduit douze petites marches par an**, à date fixe : 31 mars
  +2,94 °C à Pontarlier, 1ᵉʳ avril +2,51. Très inférieur au bruit quotidien,
  donc invisible sur une carte journalière — mais à garder en mémoire si une
  moyenne mensuelle venait à être affichée.

**La nébulosité fait exception, et c'est la variable la plus exposée du projet.**
Ni écart ni rapport constant : elle ne reçoit pas de correction linéaire simple
au pas journalier. L'explication la plus plausible — hypothèse, non fait établi
— est que la correction s'applique au pas horaire et que la nébulosité, seule
des quatre à être bornée des *deux* côtés, se fait rogner à 0 et à 100 avant
d'être remoyennée. Une température ne bute sur rien, une pluie multipliée par
0,8 n'atteint jamais zéro ; un ciel, si.

---

## Le statut de la référence

ERA5 n'est pas une mesure mais une **réanalyse** : un modèle météorologique
contraint par assimilation d'observations. Là où celles-ci sont denses, il s'en
approche ; ailleurs, il produit surtout du modèle. La distinction est
déterminante, car ERA5 sert de référence à toute évaluation menée ici : **ses
propres erreurs sont invisibles à nos comparaisons.**

**Un seul contrôle externe a été mené, et il a trouvé un facteur deux.**
Confrontée aux normales publiées, la durée d'ensoleillement d'ERA5 donne
3 311 heures par an à Brest pour environ 1 700 réelles. Ce contrôle n'était pas
prévu : un chiffre a paru suspect. **Les autres variables n'ont subi aucun test
de ce genre** — les précipitations et le vent, affichés à l'utilisateur, ne sont
vérifiés que contre eux-mêmes. À traiter avant l'élargissement mondial.

### ERA5 et ECMWF IFS : deux instruments, non deux degrés de justesse

L'écart entre les deux n'est documenté nulle part sous forme chiffrée — la
littérature compare chaque système aux observations de surface, jamais l'un à
l'autre. Il a donc été mesuré ici (script 19), sur quatre sites français et sept
années. Trois mécanismes l'expliquent :

- **La résolution.** ERA5 tourne à 31 km avec le cycle 41r2 d'IFS figé en 2016,
  l'IFS opérationnel à 9 km. Une maille de 31 km centrée sur Pontarlier moyenne
  la vallée du Doubs avec les plateaux : au 1er janvier 2017, ERA5 y donne 0,2 °C
  contre 5,4 °C pour IFS. À Paris, sans relief à résoudre, les deux donnent
  0,9 °C. L'écart est géométrique, non physique.
- **La correction d'altitude d'ERA5-Land.** ERA5-Land n'est pas une réanalyse
  indépendante mais le modèle de surface rejoué à 11 km, corrigé par un gradient
  thermique quotidien (Muñoz-Sabater et al., 2021) — il corrige donc précisément
  le défaut qui fait diverger ERA5. D'où le classement observé sur la
  température : IFS ≈ ERA5-Land ≠ ERA5.
- **Les montées de version.** ERA5 rejoue quatre-vingts ans avec une seule
  version du modèle ; IFS change une à deux fois par an, et ECMWF annonce à
  chaque fois l'amélioration des champs de vent et de température près de la
  surface — soit exactement ceux sur lesquels les deux divergent le plus. **La
  série IFS porte ses propres ruptures internes.**

**Aucune des deux n'est « plus fausse » dans l'absolu.** Pour restituer un point
un jour donné, en terrain complexe surtout, IFS est meilleur : il voit le
relief. Pour comparer deux dates séparées de décennies, ERA5 est meilleur : il
ne change pas d'instrument en chemin. Open-Meteo tranche dans le même sens —
*« when studying climate change over decades, it is advisable to exclusively
utilise ERA5 or ERA5-Land »*.

Amplitude sur 2018-2024 : moins de 1 °C sur les températures, moins de 1 mm/jour
sur les précipitations, moins de 1 point de nébulosité hors montagne. **Deux
exceptions** — le vent décale de −3,1 à +3,3 km/h selon le site, avec changement
de signe, soit le quart de la valeur ; et la haute montagne dégrade tout, avec
−5,2 points de nébulosité et +1,8 °C à Chamonix. L'écart varie en outre avec la
saison, ce qui interdit de le corriger par un décalage unique.

---

## Limites

Ces mesures reposent sur un nombre restreint de sites. Elles établissent des
**motifs, non des amplitudes** valables en tout point.

**1. Aucun code météorologique pour le futur.** L'aspect du ciel doit être
reconstruit → [`regles.md`](regles.md).

**2. Nébulosité sous-estimée.** Le modèle est en retrait d'ERA5 sur tous les
sites testés — de −5,1 points à Pontarlier à −30,2 à Singapour. L'écart n'est ni
local ni imputable au relief, et il est stable dans le temps, ce qui le rend
calibrable. **Mais il n'est pas entièrement hérité du modèle : il est en partie
fabriqué par la correction d'Open-Meteo** — à Pontarlier, le brut est à
+0,5 point d'ERA5 et le corrigé à −8,8. La conclusion pratique ne change pas,
son origine oui.

Les réanalyses sont par ailleurs elles-mêmes en retrait des observations de
surface — constat établi en Méditerranée sur ERA-Interim et MERRA,
antérieurs à ERA5 (Enriquez-Alonso et al., 2015). L'extrapolation n'est pas
démontrée, mais si elle se vérifie, les deux erreurs s'additionnent.

**3. Précipitations lissées par ERA5.** La réanalyse surestime les pluies faibles
et le nombre de jours pluvieux, et sous-estime les épisodes intenses (Lavers
et al., 2022). Deux mécanismes : une maille de 30 km dilue par construction une
cellule convective de quelques kilomètres ; et la convection, non résolue, est
déclenchée trop souvent et trop longtemps à intensité trop faible (Chen et al.,
2021). **Les cumuls journaliers sont exploitables, les intensités ne le sont
pas.**

**4. Correction de biais restreinte à la moyenne.** Les écarts de moyenne sur la
température restent sous 0,35 °C, tandis que les rapports d'écart-type
s'échelonnent de 0,61 à 1,41 selon la variable et le site.

**5. Extrêmes et sécheresses : aucun déficit constaté.** Contrairement à ce qu'on
pouvait craindre, le modèle produit *davantage* de jours chauds, de vagues de
chaleur et de sécheresses longues que l'observation, et reproduit
l'autocorrélation à 0,01 près. Deux réserves : le test chevauche la période
d'ajustement des coefficients, donc flatte le modèle ; et il ne dit rien de
l'amplification future, invérifiable par nature. **Aucune correction n'est
appliquée** — en introduire une là où la mesure n'établit pas de déficit
reviendrait à injecter une erreur.

**6. Modèle unique et phénomènes non résolus.** Une seule sortie interdit toute
estimation de l'incertitude inter-modèles — or aux échéances proches, celle-ci
l'emporte sur l'incertitude de scénario (Hawkins & Sutton, 2009) : le choix du
modèle pèse ici davantage que celui de la trajectoire d'émissions. Et malgré une
grille à 10 km, la résolution effective reste celle de la maille d'origine :
orages, brouillards de vallée et effets de relief fins ne sont pas représentés.
**La descente d'échelle recale et redistribue, elle n'ajoute pas
d'information.**

**7. Asymétrie de résolution temporelle.** Historique horaire, projections
journalières seulement : c'est la contrainte structurante de toute la chaîne →
[`donnees.md`](donnees.md).

**8. Neige servie par plages manquantes.** Ni saisonnières ni uniformes : 61 jours
chaque été à Marseille et Brest, la moitié de l'année à Christchurch, aucun à
Ushuaia. Aux sites tropicaux, les cinq modèles servent 0 % — là où la neige n'a
pas d'objet, la variable est absente plutôt que nulle, ce qui n'est pas une
défaillance. Ailleurs, de 50 à 100 % selon le modèle et le lieu. Sans
conséquence sur le choix du modèle : la classe de ciel ne lit plus la neige.

---

## Références

- Cannon, A. J., Sobie, S. R. & Murdock, T. Q. (2015). Bias correction of GCM
  precipitation by quantile mapping. *Journal of Climate*, 28, 6938-6959.
  [10.1175/JCLI-D-14-00754.1](https://doi.org/10.1175/JCLI-D-14-00754.1)
- Chen, D., Dai, A. & Hall, A. (2021). The convective-to-total precipitation
  ratio and the « drizzling » bias in climate models. *JGR: Atmospheres*.
  [10.1029/2020JD034198](https://doi.org/10.1029/2020JD034198) — *porte sur
  CMIP5, non sur ERA5.*
- Enriquez-Alonso, A. et al. (2015). Cloud cover climatologies in the
  Mediterranean. *Climate Dynamics*.
  [10.1007/s00382-015-2834-4](https://doi.org/10.1007/s00382-015-2834-4)
- Haarsma, R. J. et al. (2016). HighResMIP v1.0 for CMIP6. *Geoscientific Model
  Development*, 9, 4185-4208.
  [10.5194/gmd-9-4185-2016](https://doi.org/10.5194/gmd-9-4185-2016)
- Hausfather, Z. & Peters, G. P. (2020). Emissions – the « business as usual »
  story is misleading. *Nature*, 577, 618-620.
  [10.1038/d41586-020-00177-3](https://doi.org/10.1038/d41586-020-00177-3)
- Hawkins, E. & Sutton, R. (2009). The potential to narrow uncertainty in
  regional climate predictions. *BAMS*, 90, 1095-1107.
  [10.1175/2009BAMS2607.1](https://doi.org/10.1175/2009BAMS2607.1)
- Lavers, D. A. et al. (2022). An evaluation of ERA5 precipitation for climate
  monitoring. *QJRMS*, 148. [10.1002/qj.4351](https://doi.org/10.1002/qj.4351)
- Muñoz-Sabater, J. et al. (2021). ERA5-Land. *Earth System Science Data*, 13,
  4349-4383. [10.5194/essd-13-4349-2021](https://doi.org/10.5194/essd-13-4349-2021)
- ECMWF (2024). IFS upgrade improves near-surface wind and temperature
  forecasts. *ECMWF Newsletter* 181.
  [ecmwf.int](https://www.ecmwf.int/en/newsletter/181/earth-system-science/ifs-upgrade-improves-near-surface-wind-and-temperature)
- Open-Meteo. *Historical Weather API — documentation*.
  [open-meteo.com](https://open-meteo.com/en/docs/historical-weather-api)
