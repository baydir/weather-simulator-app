# Choix du modèle climatique — étape 2

Ces scripts établissent les chiffres de la section *Comment les cinq ont été
départagés* de `CLAUDE.md`, et le choix de `MRI_AGCM3_2_S`.

Ils diffèrent de `scripts/verification/` sur deux points. Ils s'appuient sur le
paquet `weather_simulator` — construire les requêtes et détecter les valeurs
nulles est précisément ce que l'étape 1 a produit, et le refaire ici aurait
ouvert la porte à deux comportements divergents. Et ils **séparent la collecte
de l'analyse** : soixante-dix requêtes de 36 ans ne se rejouent pas à chaque
retouche d'une mesure.

## Les quatre modules

| Module | Rôle |
|---|---|
| `config.py` | Sites, période, emplacement du cache — et les raisons de chaque choix |
| `collect.py` | Les 70 requêtes, mises en cache sur disque. **Seul à toucher au réseau** |
| `load.py` | Relecture du cache, retrait de la climatologie du jour de l'année |
| `measures.py` | Les 15 mesures et leur mode de comparaison |
| `analyse.py` | Couverture, tables par mesure, classement moyen |
| `reference_year.py` | Quelle année ancienne tenir comme « ordinaire » (section 4) |

## Usage

```bash
python scripts/model_selection/collect.py      # long, réseau, reprenable
python scripts/model_selection/analyse.py      # instantané, hors réseau
python scripts/model_selection/reference_year.py
```

La collecte écrit dans `data/model_selection/`, hors dépôt. Elle saute ce qui
est déjà là : **on la relance autant de fois que nécessaire**, elle ne redemande
que les trous. C'est indispensable, les limites de débit d'Open-Meteo ayant été
atteintes à trois reprises pendant la collecte initiale — limite horaire, puis
limite journalière.

L'analyse ne classe que les sites où les cinq modèles ont répondu. Un site
partiel attribuerait aux modèles présents les premiers rangs quoi qu'ils
vaillent, et une collecte interrompue par la limite de débit trancherait la
comparaison en silence.

## Ce que chacun établit

- **`collect.py`** — rien en soi ; il constitue la matière. 10 sites × (5 modèles
  + 2 réanalyses de référence), 1979-2014, huit variables journalières.
- **`analyse.py`** — le classement, et deux constats de couverture : `FGOALS_f3_H`
  et `HiRAM_SIT_HR` ne servent jamais `wind_speed_10m_max` ; aux sites tropicaux
  les cinq servent 0 % de neige.
- **`reference_year.py`** — 1980 est le plus froid des trente étés en France
  (−2,00 écart-type), donc le pire choix possible d'année de comparaison ; 1991
  est la plus ordinaire de la période ancienne ; et la France s'est réchauffée
  de 0,92 °C entre 1979-1988 et 1999-2008.

## Réserves

La période 1979-2014 **chevauche intégralement** la fenêtre sur laquelle
Open-Meteo a ajusté ses coefficients de correction. Il n'existe pas de période
de réserve : la fenêtre porte sur cinquante ans et couvre tout le recouvrement
disponible. C'est la raison pour laquelle aucune moyenne n'est comparée — voir
`measures.py`, dont l'en-tête porte le raisonnement.

Dix sites restent un échantillon mince, et `CLAUDE.md` le signale de ses propres
mesures. Ils établissent des motifs, non des amplitudes valables en tout point.
