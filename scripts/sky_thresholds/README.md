# Seuils de la classe de ciel — étape 3

Un seul script, `calibrate.py`. Il établit les chiffres de la section *Les
seuils de nébulosité* de `docs/regles.md`, et confirme les seuils de 30 % et
70 %.

```bash
python scripts/sky_thresholds/calibrate.py
```

Une requête par site, mise en cache dans `data/sky_thresholds/`, hors dépôt.
L'analyse se rejoue ensuite sans réseau. Dix sites, ceux de l'étape 2, 2005-2014,
ERA5 forcé.

## Ce qu'il établit

**Ce que reçoit chaque classe.** Sur les jours secs — les jours humides étant
déjà pris par les classes pluie et neige —, la lumière médiane atteignant le sol
vaut environ 90 %, 80 % et 60 % de celle d'un ciel clair. Trois paliers nets,
dans le même ordre aux dix sites.

**Ce que la moyenne journalière ne peut pas dire.** À nébulosité égale la
lumière reçue s'étale de 20 points (vers 30 % de nébulosité) à 49 points
(vers 90 %). Une matinée bouchée suivie d'un après-midi radieux porte le même
chiffre qu'une journée grise de bout en bout.

**Pourquoi les deux étalons évidents ne conviennent pas.** `sunshine_duration`
donne 1,3 à 2,0 fois les heures de soleil réelles, l'erreur croissant avec la
nébulosité. `weather_code` est le maximum de 24 codes horaires, déclare Marseille
couverte un jour sec sur deux, et dérive de la nébulosité même qu'on veut
seuiller.

**Ce que les autres variables récupèrent.** L'amplitude thermique fait gagner
0,04 à 0,22 de variance expliquée selon le site — la piste concrète pour un
modèle appris sur observations réelles, inscrit en *améliorations envisagées*.

**Où la mesure ne porte pas.** Près des pôles en hiver le ciel clair tend vers
zéro : 14,3 % des jours à Reykjavik, où la classe repose sur la seule
nébulosité.

## Réserve

L'étalon est le rayonnement d'ERA5, dont les cumuls annuels concordent avec les
valeurs publiées. Il reste une réanalyse, avec ses erreurs propres, invisibles à
cette comparaison — la réserve habituelle de `docs/science.md`.
