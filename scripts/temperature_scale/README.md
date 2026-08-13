# Échelle de couleur des températures

Deux scripts. `collect.py` va chercher trente ans de températures françaises,
`scale.py` les lit et dit ce que chaque découpage capture.

```bash
./venv/bin/python scripts/temperature_scale/collect.py   # une fois, réseau
./venv/bin/python scripts/temperature_scale/scale.py     # hors réseau
```

Une requête par site, mise en cache dans `data/temperature_scale/`, hors dépôt.
**Douze villes, une par climat français** — l'océan, le nord, l'est continental,
la montagne, le sud-ouest, la Méditerranée et la Corse —, **1981-2010**,
ERA5-Land : 131 484 journées.

## Ce qu'il établit

**L'échelle est absolue.** La couleur ne dépend que de la température, jamais de
la date ni du lieu — janvier est froid et juillet est chaud, et l'échelle le dit,
comme le font les cartes météo grand public. Aucune normale n'entre donc dans le
calcul ; les normales servent à **placer les bornes**, pas à comparer.

**Ce que la France a connu.** Maximale : médiane 15,8 °C, p99 31,5, record 40,2 à
Bordeaux. Minimale : médiane 8,9, p99 22,1, minimum −26,3 à Briançon. Les deux
températures partagent une seule échelle, ce qui rend les deux nombres d'une
carte comparables — et envoie la minimale dans la moitié froide, où elle reste :
neuf nuits sur dix sont sous 15 °C.

**Pourquoi un pas de 5 °C et non de 10.** Mesuré sur les mêmes données, le nombre
de couleurs distinctes que montre une recherche de 47 jours — la longueur
courante :

| pas | Paris janvier | Paris juillet | Brest juillet | Strasbourg janvier |
|---|---|---|---|---|
| 10 °C | 2,4 | 2,8 | 2,0 | 2,7 |
| 5 °C | 3,6 | 4,0 | 2,7 | 4,0 |
| 2,5 °C | 6,4 | 6,8 | 4,6 | 6,9 |

À six couleurs — soit un pas de 10 °C — la bande entière est un aplat presque
uniforme : la couleur ne distingue plus rien à l'intérieur d'une recherche. Un
pas de 2,5 °C a été essayé et écarté pour la raison inverse : vingt-deux teintes
ne se nomment plus, et une échelle dont les paliers n'ont pas de nom est un
dégradé — il suggère une précision que des agrégats journaliers n'ont pas.

**Neuf bandes, de 5 à 40.** Faire courir l'échelle de 5 à 40 plutôt que de 0 à 35
place chaque couleur là où un lecteur français l'attend — le jaune sur 15-20,
l'orange sur 20-25, le rouge à partir de 25 — et laisse la bande haute à la
chaleur que seul le futur simulé atteint. Le prix est un bas d'échelle grossier :
tout ce qui est sous 5 °C porte une seule couleur, soit 7 % des maximales et 28 %
des minimales.

**Pourquoi la réanalyse et non les annales.** Une maille lisse les extrêmes :
aucune maille française de ces trente ans n'atteint 40 °C, là où les relevés de
station le font. Des bornes reprises d'un almanach seraient des couleurs que la
page ne pourrait pas afficher. C'est aussi ce qui rend la bande haute — 40 °C et
au-delà — atteignable par le futur simulé et par lui seul.

**Ce que la période de référence produit.** 1981-2010 est la normale OMM, et
c'est délibérément une référence froide pour un site qui montre l'avenir. À
Paris, d'après le modèle climatique :

| | 1981-2010 | 2036-2050 |
|---|---|---|
| ≥ 30 °C | 4,9 j/an | 21,1 j/an |
| ≥ 35 °C | 0,5 j/an | 5,3 j/an |
| ≥ 40 °C | 0,0 j/an | 0,5 j/an |

L'échelle rougit à mesure que le siècle avance, parce que la référence, elle, ne
bouge pas.

## Où la mesure ne porte pas

Elle ne dit pas où couper. Les bornes sont une convention de langue sur un
continu, exactement comme la frontière entre *nuageux* et *couvert* : la mesure
dit ce qui tombe de part et d'autre d'une ligne, jamais où la tracer.

Elle ne dit rien non plus des teintes. Celles-ci sont contraintes par la
lisibilité — la couleur est portée par les chiffres eux-mêmes, sur une carte
blanche — et c'est `scripts/ink_contrast.py` qui les mesure.
