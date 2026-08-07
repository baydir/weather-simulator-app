# Grille de correction de nébulosité — étape 4

Ces scripts produisent la table embarquée comme ressource serveur. Ils
établissent les chiffres de la section *La grille de correction* de
`docs/application.md`.

| Module | Rôle |
|---|---|
| `nodes.py` | Géométrie du réseau à 0,5°, boîte française, tri terre/mer |
| `priority.py` | Ordre de collecte par population desservie |
| `collect.py` | Sonde d'altitude puis collecte des séries. **Seul à toucher au réseau** |
| `build.py` | Construit la table depuis le cache, ou une table provisoire |
| `run_until_done.sh` | Relance `collect.py` jusqu'à complétion, détaché |

## Usage

```bash
python scripts/calibration_grid/collect.py            # long, réseau, reprenable
python scripts/calibration_grid/build.py              # table depuis le cache
python scripts/calibration_grid/build.py --neutral    # table provisoire
```

La collecte écrit dans `data/calibration_grid/`, hors dépôt. **Elle se relance
autant de fois que nécessaire** : chaque nœud est écrit dès son arrivée et les
nœuds présents sont sautés. Pour la laisser tourner sans surveillance :

```bash
nohup ./scripts/calibration_grid/run_until_done.sh > /dev/null 2>&1 &
tail -f data/calibration_grid/collect.log
pkill -f run_until_done                               # arrêt
```

Un processus lancé ainsi survit à la fermeture du terminal. Il faut donc
l'arrêter explicitement — ne pas se fier à la disparition de la tâche qui l'a
lancé.

## Deux passes, et pourquoi

La **sonde d'altitude** demande un seul jour à chaque nœud de la boîte. ERA5
renvoyant zéro en mer, l'altitude sépare la terre de l'eau pour un coût
négligeable, et évite de collecter trente ans de données au large. Résultat :
704 nœuds dans la boîte, 475 terrestres, 594 à collecter une fois ajoutée la
couronne de mer touchant la terre.

La **collecte** ne porte que sur ces 594. Deux requêtes chacun : la réanalyse sur
1985-2014, et le modèle sur 1985-2050 d'un seul tenant — cette requête portant à
la fois le passé du modèle, qui le rend comparable à la référence, et son futur,
qui porte la tendance à ne pas écraser.

## Le débit, qui est la vraie contrainte

Environ **trente nœuds par heure**, soit une quinzaine à une vingtaine d'heures
pour la France. Le réseau ne compte que pour une heure là-dedans ; le reste est
l'attente du quota.

La documentation d'Open-Meteo annonce des limites qui impliqueraient quatre
nœuds par jour, deux cents fois moins que ce qu'on observe, et l'API n'expose
aucun en-tête de quota. Le débit ne se prédit pas, il se mesure. Raccourcir le
palier de reprise de 300 à 60 s a été testé : sans effet, le plafond est réel.

## La table provisoire

`--neutral` produit une table à correction identité couvrant toute la boîte,
pour que l'API et l'interface s'écrivent sans attendre la collecte.

**Elle ne doit jamais être servie.** Un futur non corrigé est un futur
artificiellement ensoleillé de 8 à 11 points de nébulosité, et trois des cinq
classes de ciel en dépendent. Les verrous qui l'en empêchent sont énumérés dans
[`docs/application.md`](../../docs/application.md) — le dernier étant que
l'application refuse de démarrer sur une telle table.
