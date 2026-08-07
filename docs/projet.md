# Projet — ce qu'on fait et pourquoi

L'intention. Les règles opératoires qui en découlent sont dans
[`CLAUDE.md`](../CLAUDE.md).

---

## Objet

Weather Simulator App est une application web restituant, jour par jour, les
conditions météorologiques d'un lieu donné, **pour toute date comprise entre
1950 et 2050**.

L'utilisateur renseigne une localisation et une plage de dates. L'application
retourne pour chaque journée les températures minimale et maximale, l'aspect du
ciel et les précipitations, selon les modalités de présentation d'une
application météorologique grand public.

---

## Finalité

**Elle est pédagogique, non technique.**

Le changement climatique est habituellement communiqué au moyen de moyennes
globales et d'anomalies de température (« +2,7 °C à l'horizon 2100 »). Ces
grandeurs sont exactes mais agrégées : elles ne renseignent pas sur les
conditions concrètes rencontrées à une date et en un lieu déterminés.

Le projet repose sur l'hypothèse que **restituer les projections sous une forme
déjà familière — le bulletin météorologique quotidien — en améliore
l'appropriation** par un public non spécialiste. L'énoncé « 14 juillet 2046,
Paris : 21 °C / 39 °C, ciel dégagé, 0 mm » a un caractère concret que l'anomalie
globale n'a pas.

Le format d'application météorologique est donc un **choix fonctionnel, non un
habillage**. Toute décision de conception qui s'en écarte doit être justifiée au
regard de cet objectif.

---

## Pourquoi ce n'est pas une prévision

**Cette contrainte prime sur toutes les autres.**

Un modèle climatique ne prédit pas les conditions du 14 juillet 2046. Il produit
une trajectoire cohérente, c'est-à-dire une séquence de journées statistiquement
plausible dans un climat modifié. **La date affichée situe la journée dans une
saison et dans une décennie ; elle n'engage aucune exactitude sur cette
journée.**

L'application doit être suffisamment réaliste pour remplir sa fonction
pédagogique, et suffisamment explicite sur son statut pour ne pas induire en
erreur. Cet arbitrage se pose à chaque décision d'interface. Les trois règles
qui en découlent, applicables au code comme aux textes, sont dans
[`CLAUDE.md`](../CLAUDE.md).

---

## Public visé

Public francophone non spécialiste. **La compréhension de l'application ne doit
supposer aucune connaissance préalable des modèles climatiques.**

---

## Les deux régimes de données

Une requête peut couvrir simultanément le passé et le futur. L'application
combine alors deux sources de nature différente :

- **Passé** (1950 → date du jour) : observations issues de réanalyses
  météorologiques.
- **Futur** (date du jour → 2050) : sorties d'un modèle climatique.

Les deux proviennent d'Open-Meteo. Ce que valent ces sources →
[`science.md`](science.md) ; comment on construit une série homogène malgré le
changement de source → [`donnees.md`](donnees.md).
