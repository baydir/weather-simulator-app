# Reprise — moyennes de température sur deux décennies

## Demande et ordre de lecture validés

- Branche existante : `climate-explorer`. Préserver les changements non commités antérieurs.
- D'abord la comparaison des calendriers ; ensuite le nouveau bloc de moyennes,
  puis les détails météo de l'année initiale.
- Deux résumés : moyenne des maximales et moyenne des minimales sur les dix
  dernières périodes complètes et les dix prochaines périodes annuelles.
- Même période calendaire que la recherche. Année en cours exclue.
- Moyenne de chaque période annuelle, puis moyenne des années à poids égal.
- Un seul graphique chronologique, deux courbes (maximales/minimales), prolongées
  vers la simulation en pointillés. Pas de lissage ni d'estimation des jours absents.
- Une commande explicite lance la collecte. Reprise possible, progression visible,
  résultats reçus conservés, aucun réessai automatique après limitation.
- Cache navigateur des réponses brutes, retraitées par le serveur à chaque visite.
- Modèles, scénario, sources et correction scientifique existants inchangés.
- Commit et push sur la branche existante demandés ; extension à 1950–2050 reportée.

## Règle de couverture retenue

Après la proposition explicite et la demande de poursuivre : périodes complètes
uniquement, par variable ; dix moyennes annuelles complètes pour une moyenne
sur dix ans. Ne pas compléter les jours absents ni compenser une année absente
par une année supplémentaire. L'écart simulation moins passé est calculé côté serveur.

## Découpage technique

1. Calculs uniques en Python ; les deux moyennes annuelles accompagnent `/api/days`.
   La couverture se rapporte à la plage demandée, pas seulement à la plage servie.
2. Un endpoint agrège les résumés annuels et fournit aussi les écarts entre fenêtres.
   Aucune moyenne, différence ni règle d'arrondi nouvelle en JavaScript.
3. Réutiliser `shiftRange` et les bornes servies pour les années, les hivers et
   les bissextiles. Présenter les fenêtres exactes. Les années chargées manuellement
   et par le nouveau bloc partagent une même requête en cours et le même cache mémoire.
4. Récupération séquentielle, espacée ; arrêt après la période active ; HTTP 429
   suspend les appels sans boucle de réessai. Cache brut à taille bornée et tolérant
   au stockage désactivé ou saturé. Expiration d'origine conservée même lorsqu'une
   réponse récente devient ancienne selon un plan ultérieur.
5. Vue française après les calendriers : deux résumés, couverture, avertissement
   conditionné aux données simulées, graphique annuel commun, détail accessible.
6. Tests Python/JS hors réseau ; vérification Chromium avec réponses fictives et
   contrôle mobile. Python disponible : `.venv/bin/python`. Chrome installé ;
   Playwright présent, son Chromium dédié absent. Aucun quota météo à consommer.

## État

- Implémentation complète : moyennes annuelles dans `/api/days`, agrégation des deux
  fenêtres dans `/api/temperature-comparison`, nombre d'années dans `/api/config`.
- Les calendriers restent en premier. Les compteurs de chaleur existants sont
  visibles par défaut sous chaque calendrier ; le nouveau bloc suit la comparaison.
  Les courbes quotidiennes ont été retirées à la demande de l’utilisateur.
- Les années sont repérées par leur année de début. Pour le passé, on conserve les
  dix dernières périodes terminées dont l'année de début précède l'année courante.
  Les hivers traversant janvier sont donc traités sans introduire de jours futurs.
- Le nouveau graphique est unique : maximales et minimales annuelles, traits
  pleins puis pointillés selon `has_simulated`, interruption aux valeurs absentes.
  Le détail tabulaire donne les dates, valeurs et couvertures, et permet d'ajouter
  une année déjà reçue aux calendriers sans récupération météo supplémentaire.
- Cache brut borné à environ 1,5 million de caractères. Fraîcheur servie par le
  plan : quinze minutes pour les réponses récentes ; sans expiration pour les
  réponses stables. Une expiration d'origine ne devient jamais illimitée après coup.
- Aucun modèle, scénario, traitement de biais ou granularité quotidienne modifié.
- Vérification complète hors réseau avec Chrome réussie : ordre des sections,
  moyennes et données manquantes, arrêt/reprise, cache entre visites, sélection
  d'une année chargée, HTTP 429 sans réessai, absence d'erreur JS et débordement mobile.
- Vérifications sans appel météo réel. Aucun déploiement demandé.

## Vérification et fichiers utiles

- Tests : `.venv/bin/python -m pytest -q` — 238 tests réussis, suite JavaScript incluse ; `git diff --check` sans erreur.
- Navigateur : `CLIMATE_BROWSER_CHANNEL=chrome .venv/bin/python scripts/check_climate_comparison.py`.
  Ce script utilise un serveur local et peut nécessiter l'autorisation d'exécution
  hors sandbox. La première autorisation avait échoué pour limite d'utilisation ;
  les exécutions suivantes ont été autorisées et ont réussi.
- Captures **fictives** : `/tmp/weather-means-offline/desktop.png` et `mobile.png`.
- Calculs : `src/weather_simulator/domain/temperature_means.py`.
- Vue et orchestration : `web/static/js/climate-comparison.js`, `climate-controller.js`,
  `period-loader.js`, `weather-cache.js` et raccordement dans `results.js`.
- Copie des fichiers principaux avant ce travail :
  `/Users/baydir/.codex/visualizations/2026/10/05/01a10dcf-1a3f-7f11-af0f-be994975d300/means-baseline/`.

## Précautions pour reprendre

- Relire le dernier message utilisateur, puis `git status --short` et ce fichier.
- `docs/`, `AGENTS.md`, `CLAUDE.md` et dossiers de mesure protégés : pas de modification
  sans validation. Les changements préexistants dans `docs/` ne viennent pas de ce travail.
- L'ancienne frise de compteurs a été entièrement retirée : ne pas la réintroduire.
- La maquette aux données fictives est séparée de l'application :
  `/Users/baydir/.codex/visualizations/2026/10/05/01a10dcf-1a3f-7f11-af0f-be994975d300/temperature-period-sketch.html`.
