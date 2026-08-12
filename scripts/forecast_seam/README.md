# La couture de prévision — étape 7

Ces scripts mesurent la seule jonction que l'ajout du segment de prévision
introduit : **l'analyse IFS de l'archive contre la prévision IFS**, sur les mêmes
journées.

| Module | Rôle |
|---|---|
| `config.py` | Les dix sites de l'étape 2, la fenêtre, les variables lues |
| `collect.py` | Deux requêtes par site. **Seul à toucher au réseau** |
| `analyse.py` | Les écarts, depuis le cache — se rejoue hors réseau |

## Usage

```bash
./venv/bin/python scripts/forecast_seam/collect.py   # lent, réseau, reprenable
./venv/bin/python scripts/forecast_seam/analyse.py   # depuis data/forecast_seam/
```

**La collecte de l'étape 4 doit être à l'arrêt.** Les deux mangent le même quota,
et l'archive répond `Hourly API request limit exceeded` bien avant que celle-ci
n'aboutisse.

```bash
pkill -f run_until_done
```

## Ce qui se mesure, et pourquoi ce n'est pas évident

La série ne gagne pas de couture ce soir : IFS traverse aujourd'hui sans
rupture, sur l'archive jusqu'à hier et sur la prévision ensuite. Mais ce ne sont
pas le même produit — `ecmwf_ifs` à 9 km est une **analyse**, `ecmwf_ifs025` à
0,25° une **intégration vers l'avant**. Une couture peut donc se cacher là où
l'architecture n'en annonce aucune.

Elle ne se lit pas en regardant de part et d'autre d'une date : les deux côtés
seraient alors des saisons différentes. Elle se lit en interrogeant les deux
sources sur **les mêmes journées** et en comparant leurs réponses. D'où le
recouvrement de quatre-vingt-douze jours.

## Deux questions, dans cet ordre

**1. Que renvoie l'endpoint de prévision pour une journée passée ?** Soit le
passage du modèle qui avait cours ce jour-là — une vraie prévision à courte
échéance —, soit une réanalyse recollée après coup. Dans le second cas toutes les
mesures qui suivent sous-estiment la couture, puisqu'elles comparent une analyse
à une analyse. Le diagnostic tient en une part : celle des journées où les deux
côtés donnent le **même chiffre exactement**. Près de 100 %, rien n'est mesuré.

**2. De combien décroche-t-elle ?** Biais, écart absolu moyen, pire journée, par
variable puis par site. Deux repères sont imprimés à côté, un chiffre de cette
nature ne voulant rien dire seul :

- **−1,8 à +0,9 °C** — la couture d'archive non documentée que le forçage de
  `models` sert à empêcher. Un écart de cet ordre est déjà jugé inacceptable.
- **8 à 11 points de nébulosité** — le déficit du modèle climatique, qui justifie
  à lui seul toute la grille de correction de l'étape 4.

## La limite qu'il faut annoncer plutôt que découvrir

**L'endpoint de prévision ne remonte pas au-delà de quatre-vingt-douze jours.**
Un passage mesure donc **une saison**, pas une année. Un étalement annuel suppose
des passages espacés dans le temps, et rien dans les chiffres produits ici ne le
signalera : ils auront l'air complets.

## Chiffres établis

*Mesure non encore passée sur les dix sites — la collecte de l'étape 4 occupe le
quota.* Le sondage qui a motivé l'étape, à titre indicatif et sans valeur de
mesure : Toulouse, dix journées communes, écart absolu moyen de **0,53 °C** en
température et **3,4 points** en nébulosité, altitude identique des deux côtés.
