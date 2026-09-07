# Idées — envisagé, non retenu

Ce qui a été examiné puis écarté, et ce qui reste ouvert. **Rien ici n'est
décidé.** Consigné pour que les constats de mesure ne se perdent pas et qu'on ne
refasse pas deux fois le même raisonnement.

Une piste qui finit par être retenue **quitte ce document** : ses constats
partent où ils font foi, et il ne reste ici qu'une note disant où, et ce que la
réalisation a démenti de ce qui avait été supposé. C'est arrivé une fois, à la
comparaison à l'ancien climat.

Tout ce qui touche aux données ou à la méthode relève de la validation
scientifique → [`CLAUDE.md`](../CLAUDE.md).

---

## Points restés ouverts

**Trois classes de ciel sec sont peut-être une de trop.** La nébulosité moyenne
journalière est une variable ambiguë — deux journées à 90 % peuvent recevoir de
29 % à 79 % de la lumière d'un ciel clair. Deux classes, ensoleillé et nuageux,
seraient plus défendables, au prix de la finesse d'affichage.
→ [`regles.md`](regles.md)

**Les rafales.** `wind_gusts_10m_max` existe comme variable propre et **les trois
segments la servent**. Elle n'est pas retenue : une rafale est par nature un
phénomène sous-maille, hors de portée d'un modèle à 20 km. La servir donnerait
un chiffre juste de forme et faiblement fondé. Son adoption relèverait de la
validation scientifique.

**L'accueil ne passe qu'à une taille de fenêtre.** La table de contraste n'est
publiée que pour 1440 × 900, où le plancher est de 4,6:1. Ailleurs il tombe à
3,1:1 en 1280 × 720 et à 3,7:1 en 1440 × 1200 — et sur cette dernière le texte en
cause est **l'avertissement**, la phrase que la règle 1 rend non négociable,
portée par la seule ligne de la page qui ne puisse pas se déplacer. Le dégradé
étant ancré au document, le remède touche la composition de la page elle-même :
c'est un arbitrage de mise en page, et il **reste à rendre**.
→ [`scripts/ink_contrast.md`](../scripts/ink_contrast.md)

---

## Classe de ciel apprise sur des observations réelles

**L'étape 3 a montré qu'aucun étalon interne à Open-Meteo ne convient** :
`sunshine_duration` est faux d'un facteur 1,3 à 2,0, et le `weather_code` est un
maximum horaire circulaire. Mais de vraies observations existent en dehors : les
relevés synoptiques de surface donnent la nébulosité totale **en octas, mesurée
plusieurs fois par jour** — Météo-France en open data pour la France, la NOAA
mondialement. C'est une observation, non une dérivation.

Un modèle ajusté sur cette cible, prenant en entrée les agrégats journaliers
disponibles sur les quatre segments, ferait mieux qu'un seuil unique. **La mesure
le montre déjà** : ajouter la seule **amplitude thermique** — un grand écart
entre minimale et maximale signe un ciel dégagé, le sol chauffant le jour et
rayonnant la nuit sans couverture — fait passer la variance expliquée de 0,50 à
0,64 à Strasbourg, de 0,30 à 0,52 à Bamako. Cette variable est servie par les
trois sources.

**Le plafond reste le même** : les entrées étant journalières côté futur, aucun
apprentissage ne récupère la structure interne d'une journée. Le gain porte sur
la discrimination *entre* journées de même nébulosité, jamais *à l'intérieur*
d'une journée.

**C'est un travail en soi**, de l'ampleur de l'étape 2 : seconde source avec sa
licence et son contrôle qualité, appariement station-maille — une station est un
point, ERA5 une maille de 25 km —, définition conventionnelle de « l'allure
dominante » à partir de relevés horaires, et un modèle ajusté devenant un
artefact embarqué, moins lisible qu'un arbre de décision sur des pages qui
doivent expliquer la méthode.

---

## Autres pistes

- **Enveloppe d'incertitude** fondée sur l'écart entre les cinq modèles
  éligibles, sans renoncer à l'affichage d'une trajectoire unique.
- **Comparaison aux projections régionalisées DRIAS** de Météo-France, mieux
  évaluées sur la France, et à la trajectoire de référence TRACC.
- **Ouverture à d'autres scénarios d'émissions**, ce qui suppose de changer de
  source : l'API Climate n'en expose qu'un.

---

## La comparaison à l'ancien climat — **faite**

**Elle n'est plus une idée.** Ce qui était consigné ici vit désormais dans
[`application.md`](application.md), section *Comparer à une autre année* : les
trois constats de mesure sur le choix de l'année, les deux exigences
d'honnêteté, et ce que le dessin en fait. Un fait vit dans un seul fichier.

**Ce que la réalisation a démenti de ce qui était écrit ici.** La forme prévue
était une seconde bande de quatre-vingt-dix cartes sous la première, doublée
d'une ligne de synthèse — le même paragraphe concédant que deux bandes de
quatre-vingt-dix cartes ne se comparent pas à l'œil. Elle est allée sur le
graphe, où la superposition *est* la comparaison, et la ligne de synthèse est
tombée avec le problème qu'elle devait résoudre : c'était une agrégation, que
[`application.md`](application.md) refuse à l'interface.

Deux autres suppositions sont tombées. Le déclenchement ne suit pas la
couverture de la grille : une plage passée n'exige aucune correction, donc la
comparaison marche partout dans le monde, et elle y est exacte là même où la
projection ne l'est pas, l'année comparée étant observée.
Et l'année n'est pas codée en dur par grande région : le menu s'ouvre sur celle
qui a été mesurée comme ordinaire et laisse choisir.

**Ce qui reste ouvert ici.** Le constat qui motivait le découpage régional tient
toujours — **une année ne peut pas être ordinaire partout**, 1980 ayant été le
plus froid des trente étés en France et le vingt-deuxième sur trente à
Reykjavik —, et la mesure n'a été faite que sur les cinq sites français.
L'étendre aux cinq autres sites de `scripts/model_selection/config.py` ne coûte
aucun réseau, le cache 1979-2014 étant sur disque ; c'est ce qui permettrait de
faire varier le défaut par région. C'est une étape de mesure, donc une étape en
soi, et elle relève de la validation scientifique.
