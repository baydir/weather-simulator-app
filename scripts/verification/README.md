# Scripts de vérification

Ces scripts établissent les faits chiffrés inscrits dans `CLAUDE.md`. Ils ont
été écrits pendant la phase de conception, avant tout code applicatif, pour que
les décisions des sections 2, 3 et 4 reposent sur des mesures et non sur des
suppositions.

Ils n'ont aucune dépendance : bibliothèque standard Python seule, `urllib`
suffit. Chacun s'exécute isolément.

```bash
python3 scripts/verification/09_weather_code_rule_and_daily_max.py
```

**Ils interrogent les API publiques d'Open-Meteo et sont donc lents.** Les plus
lourds prennent plusieurs minutes ; certains atteignent la limite de débit et
patientent. Ne pas les lancer en parallèle.

## Ce que chacun établit

| Script | Constat |
|---|---|
| `01_api_coverage_and_bounds.py` | Couverture des deux API, modèles acceptés, présence de `weather_code` dans l'historique |
| `02_climate_nulls_and_upper_bound.py` | L'API Climate renvoie `null` sans erreur ; borne haute au 31 décembre 2050 |
| `03_variable_availability_matrix.py` | Quelles variables portent réellement des valeurs, de chaque côté |
| `04_cloud_precipitation_consistency.py` | Cohérence entre nébulosité et précipitations dans les sorties de modèle |
| `05_model_coverage_audit.py` | `CMCC_CM2_VHR4` sans nébulosité ; `EC_Earth3P_HR` sans 2050 |
| `06_scenario_switch_test.py` | Aucun sélecteur de scénario : RCP8.5 est la seule trajectoire |
| `07_multisite_bias_audit.py` | Biais par variable et par site, six climats contrastés |
| `08_heatwaves_and_dry_spells.py` | Ni vagues de chaleur ni sécheresses sous-représentées |
| `09_weather_code_rule_and_daily_max.py` | Règle de dérivation reproduite à 100 % ; le code journalier est le **maximum** des 24 codes horaires |
| `10_wind_direction_and_elevation.py` | Direction du vent nulle côté Climate ; altitude identique entre les deux API |
| `11_archive_source_switch_2017.py` | L'endpoint par défaut change de réanalyse en 2017 |
| `12_era5land_vs_ifs_attribution.py` | L'écart ERA5-Land / IFS n'est pas altitudinal |
| `13_era5land_variable_gaps.py` | **ERA5-Land ne sert que la température** |
| `14_two_call_split_and_revised_cloud_bias.py` | Validation de la double requête ; biais de nébulosité contre ERA5 forcé |
| `15_cloud_bias_spatial_variation.py` | Le champ de biais est lisse : ≤ 1,6 point pour 3 500 m de dénivelé |
| `16_calibration_years_required.py` | 10 ans de calibration produisent une erreur du même ordre que la correction |
| `17_seam_reference_choice.py` | Le modèle est deux fois plus proche d'ERA5-Land que d'ERA5 |
| `18_payloads_geocoding_and_bulk.py` | Volumes, géocodage Open-Meteo, absence de CMIP6 sur le miroir AWS |
| `19_ifs_seam_2017.py` | `ecmwf_ifs` couvre 2017 → jour même, toutes variables ; amplitude de l'écart à ERA5 et ERA5-Land, et sa saisonnalité |
| `20_climate_snow_gaps.py` | La neige manque par plages, ni saisonnières ni uniformes — 61 jours d'été à Marseille, la moitié de l'année à Christchurch, rien à Ushuaia ; l'ampleur dépend aussi du modèle, `NICAM16_8S` seul étant complet |
| `21_snow_threshold.py` | Calage du critère neige sur 35 hivers à Strasbourg et Briançon ; le `weather_code` sature en altitude et ne peut servir de référence |

`reference/open_meteo_WeatherCode.swift` est une copie du fichier source
d'Open-Meteo dont la règle de dérivation a été transcrite dans le script 09.
Il est conservé pour que la transcription reste vérifiable.

## Réserves

Les scripts 17 et 18 ont été **reconstitués après coup** : les mesures d'origine
avaient été lancées en ligne de commande sans être enregistrées. Leur logique est
identique, mais leurs valeurs n'ont pas été rejouées telles quelles.

Le script 04 s'interrompt sur `CMCC_CM2_VHR4`, faute de données de nébulosité —
c'est précisément ainsi que cette absence a été découverte. Le script 06 atteint
la limite de débit sur ses derniers sites ; le script 07 en reprend la mesure
avec un espacement suffisant.

Les mesures portent sur un nombre restreint de sites et de périodes, ce que
`CLAUDE.md` signale explicitement. Elles établissent des motifs, non des
amplitudes valables en tout point.
