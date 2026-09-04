# Les coutures, en image

Deux scripts. `collect.py` va chercher une longue série journalière et la pose
sur disque, `plot.py` en dessine une fenêtre autour d'aujourd'hui et dit quel jeu
de données a servi chaque jour.

```bash
./venv/bin/python scripts/model_seams/collect.py   # une fois, réseau
./venv/bin/python scripts/model_seams/plot.py      # hors réseau
```

Quatre requêtes, mises en cache dans `data/model_seams/`, hors dépôt. Le tracé
sort dans `shots/`, hors dépôt lui aussi. Matplotlib est optionnel :
`pip install -e ".[charts]"`.

**La figure de la page de documentation se régénère avec `--out`** :

```bash
./venv/bin/python scripts/model_seams/plot.py --out web/static/img/coutures.svg
```

Celle-là est versionnée et servie — d'où le chemin explicite : rien ne doit
atterrir sous `web/static/` par l'effet de bord d'un redessin. SVG et non PNG :
74 Ko contre 144, net à tout zoom, et matplotlib écrit son texte en tracés, donc
la figure ne dépend d'aucune police du lecteur.

Par défaut **Paris, de J-31 à J+51** — 83 jours, les deux températures. `--place`,
`--before`, `--after` déplacent tout cela.

## L'axe compte les jours, il ne porte aucune date

La figure est destinée à une page qui sera lue pendant des années. Un graphe dont
l'axe dit « 20 août », relu en janvier, est un graphe manifestement périmé.

Ce dont la figure parle, en revanche, ne bouge pas : **les réanalyses s'arrêtent
environ six jours en arrière, l'analyse d'ECMWF couvre le reste jusqu'à
aujourd'hui, sa prévision court une quinzaine, et le modèle climatique prend
tout ce qui suit.** Ces positions sont les mêmes chaque jour de chaque année,
et un axe relatif est ce qui les montre.

**Ce qui n'est pas invariant, c'est la météo elle-même**, et la figure le dit au
lieu de faire semblant : la courbe est une collecte particulière, un autre jour
dessinerait d'autres températures entre les mêmes coutures.

## Ce que la mesure établit

Relevé sur Paris, série collectée le 20 août 2026 :

| Jeu de données | Rôle | Plage servie | Jours |
|---|---|---|---|
| `era5_land` | réanalyse | J-31 → J-6 | 26 |
| `ecmwf_ifs` | analyse | J-5 → J+0 | 6 |
| `ecmwf_ifs025` | prévision | J+1 → J+14 | 14 |
| `MRI_AGCM3_2_S` | simulation | J+15 → J+51 | 37 |

**La borne de J-6 n'est pas un réglage.** C'est la latence des réanalyses, que
`plan.py` ne code nulle part : IFS est demandé sur toute la plage postérieure à
2017 et les réanalyses gagnent partout où elles ont servi, si bien que la couture
tombe là où elles se sont réellement arrêtées. Elle bouge donc d'un jour ou deux
selon la date, et la figure la montre où elle est.

**La fenêtre est une recherche qu'un visiteur peut faire.** 83 jours tiennent
dans les 92 que l'API autorise : ce n'est pas une vue de diagnostic sur quelque
chose d'inatteignable, c'est une recherche ordinaire qui traverse les quatre
sources.

**La collecte exécute le plan du navigateur.** `plan.fetch_series` est le chemin
hors ligne à travers les mêmes segments, les mêmes modèles et la même
arithmétique de couture que `/api/plan` sert à un visiteur — jusqu'à la chaîne de
requête, puisqu'il appelle les URL du plan et non des requêtes reconstruites.
L'image est donc une image de l'application.

**La bande du passé porte le nom du jeu qui a servi la température**, qui n'est
pas celui que l'enregistrement nomme. `source` y dit « reanalysis », et cela
recouvre deux jeux : les températures viennent d'ERA5-Land, tout le reste
d'ERA5. Sur un graphe de températures, nommer l'autre serait faux. Le nom est lu
dans le fichier collecté, jamais retapé dans le tracé.

## Ce qu'une fenêtre plus large fait voir

Hors figure, et reproductible :

```bash
./venv/bin/python scripts/model_seams/collect.py --from 2015-01-01 --to 2030-12-31
```

**La dispersion s'élargit en franchissant la couture** — une limite déjà consignée
dans [`docs/science.md`](../../docs/science.md), point 4 : la correction de biais
d'Open-Meteo porte sur la moyenne, pas sur la variance.

| Sur Paris | moyenne | écart-type | minimum | maximum |
|---|---|---|---|---|
| réanalyse, hiver (DJF) | 8,5 °C | 3,6 | −2,2 | 19,1 |
| simulation, hiver (DJF) | 7,5 °C | **4,6** | **−8,1** | 15,8 |
| réanalyse, été (JJA) | 25,0 °C | 4,4 | 13,4 | 40,3 |
| simulation, été (JJA) | 24,7 °C | **5,1** | 13,8 | **43,1** |

Les rapports d'écart-type valent 1,28 en hiver et 1,16 en été — **dans la
fourchette de 0,61 à 1,41 que `docs/science.md` publie**. La mesure ne révèle
donc rien de neuf : elle rend voyant ce qui était écrit.

**Ce que ces chiffres ne disent pas.** Ils comparent 11,6 ans de réanalyse à
4,3 ans de simulation, sur deux périodes différentes — ce n'est pas une
comparaison de variances à parité. Et la moyenne simulée est *inférieure* de
0,7 °C à la moyenne réanalysée, ce qui ne dit rien du réchauffement : quatre ans
d'une exécution unique sont dominés par la variabilité interne. Il faudrait des
décennies et plusieurs modèles pour en tirer une tendance, et le projet n'en
dispose que d'un → [`docs/science.md`](../../docs/science.md), point 6.
