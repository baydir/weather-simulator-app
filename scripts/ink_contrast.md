# Contrastes des deux pages

Les tables qu'imprime [`ink_contrast.py`](ink_contrast.py). Elles vivent ici et
non dans `docs/application.md` : un chiffre reste attaché au script qui le
mesure, et celui-ci se remesure à chaque changement de mise en page.

```bash
./venv/bin/python scripts/ink_contrast.py              # la page de résultats, quatre saisons
./venv/bin/python scripts/ink_contrast.py --page home  # l'accueil, trois états du formulaire
```

Extra `screenshots` requis — la mesure passe par un vrai Chromium.

## Ce qui rend la mesure nécessaire

**Les deux pages portent un dégradé ancré au document**, non à la fenêtre. Fixé à
la fenêtre, la couleur sous un élément donné dépendrait de la hauteur d'écran du
lecteur : mesuré sous l'avertissement de l'accueil, le fond irait de `#d89470` sur
une fenêtre de 700 px à `#124a73` sur une de 2000. Ancré au document, c'est
`#e28f5b` à toutes les hauteurs, et l'encre se choisit au lieu de s'espérer.

La contrepartie est que **mise en page et lisibilité sont la même question** :
une page qui grandit d'une rangée de boutons fait glisser tout ce qui suit vers
une autre portion du dégradé. Resserrer l'accueil a déjà emporté l'étiquette
*Lieu* sous le seuil, à 4,4:1. Toute modification de l'une des deux pages est
donc une raison de relancer la commande.

**D'où viennent les deux moitiés de chaque rapport.** Les positions sont lues sur
un rendu réel — la page est servie, pilotée par un Chromium, interrogée sur
l'endroit où chaque élément se trouve et la couleur qu'il calcule. Le fond est
ensuite dérivé du dégradé lui-même : les arrêts sont relus dans la feuille de
style par `getComputedStyle`, jamais recopiés dans le script, et interpolés en
sRVB, ce que fait le navigateur d'un `linear-gradient` de couleurs opaques.

## L'accueil — 1440 × 900

Trois colonnes, une par état du formulaire : la page s'ouvre sans panneau, et la
hauteur du formulaire change selon celui qu'on déplie.

| Texte | rien d'ouvert | plage de dates | saison entière |
|---|---|---|---|
| la question | 11,2:1 | 11,2:1 | 11,2:1 |
| la promesse | 7,8:1 | 7,8:1 | 7,8:1 |
| l'étiquette *Lieu* | 7,8:1 | 7,8:1 | 7,8:1 |
| le champ *Lieu* | 7,0:1 | 7,0:1 | 7,0:1 |
| la bande choisie | — | 9,7:1 | 7,7:1 |
| la bande au repos | 9,7:1 | 7,7:1 | 8,2:1 |
| l'étiquette *Du* | — | 5,1:1 | — |
| le champ *Du* | — | 4,6:1 | — |
| l'étiquette *Saison* | — | — | 5,1:1 |
| le champ *Saison* | — | — | 4,6:1 |
| le bouton | — | 7,0:1 | 7,0:1 |
| l'avertissement | 5,9:1 | 5,9:1 | 5,9:1 |

**Plancher : 4,6:1**, porté par les deux champs de date.

**La bande située entre 50 % et 65 % du dégradé ne porte aucune encre.** Le fond
y va de `#4b688b` à `#677390`, et à ces clartés le noir pur plafonne à 4,0:1 quand
l'ivoire de la page atteint 4,2. Ce n'est pas un choix de ton, c'est une hauteur :
le seul remède est que le formulaire n'y descende pas.

### Les autres tailles de fenêtre

La table n'est publiée que pour 1440 × 900. Planchers relevés ailleurs :

| Fenêtre | plancher |
|---|---|
| 1440 × 900 | **4,6:1** |
| 1280 × 720 | 3,1:1 |
| 1440 × 1200 | 3,7:1 |
| 390 × 844 | 3,1:1 |

Sur une fenêtre haute, le plancher est **l'avertissement**, à 3,7:1 — la phrase
que la règle 1 rend non négociable, portée par la seule ligne de la page qui ne
puisse pas se déplacer. Le remède touche la composition de la page et **reste à
décider** → [`docs/idees.md`](../docs/idees.md).

## La page de résultats — 1440 × 960

**Une géométrie, quatre palettes.** La page mesurée est la vue `results` — dix
jours en arrière, quarante en avant —, qui porte un avertissement en haut et une
couture au milieu ; la saison est ensuite imposée sur le `body`, quatre fois. Ce
n'est pas un artifice : une plage à cheval sur aujourd'hui, en janvier, *est* une
page d'hiver avec avertissement et couture. C'est le seul moyen de comparer quatre
sols sur une même page, la saison d'une vraie couture dépendant du jour où l'on
mesure.

| Texte | hiver | printemps | été | automne |
|---|---|---|---|---|
| le lieu | 15,9:1 | 14,7:1 | 16,1:1 | 16,0:1 |
| la plage | 13,5:1 | 11,8:1 | 13,1:1 | 13,6:1 |
| nouvelle recherche | 15,3:1 | 14,3:1 | 14,2:1 | 15,3:1 |
| l'avertissement | 14,5:1 | 13,8:1 | 12,3:1 | 14,5:1 |
| le scénario | 12,3:1 | 11,1:1 | 10,1:1 | 12,4:1 |
| le mois | 11,7:1 | 10,8:1 | 9,1:1 | 11,7:1 |
| le jour | 13,3:1 | 13,1:1 | 10,2:1 | 13,2:1 |
| les deux mesures | 16,9:1 | 15,3:1 | 18,1:1 | 17,4:1 |
| la couture | 12,0:1 | 12,5:1 | 8,6:1 | 11,7:1 |
| les repères du graphe | 14,6:1 | 12,5:1 | 15,7:1 | 15,1:1 |
| la couture du graphe | 16,9:1 | 15,3:1 | 18,1:1 | 17,4:1 |
| comparer | 14,6:1 | 12,5:1 | 15,7:1 | 15,1:1 |
| la provenance | 8,6:1 | **7,9:1** | 9,8:1 | 9,2:1 |

### 1280 × 720

Le dégradé étant ancré au document, une page raccourcie fait glisser chaque bloc
sur une autre portion. La page fait 1637 px au lieu de 1705, et tout se desserre
d'un cran :

| Texte | hiver | printemps | été | automne |
|---|---|---|---|---|
| le lieu | 16,0:1 | 14,7:1 | 16,4:1 | 16,1:1 |
| la plage | 13,6:1 | 11,9:1 | 13,3:1 | 13,7:1 |
| nouvelle recherche | 15,3:1 | 14,3:1 | 14,4:1 | 15,4:1 |
| l'avertissement | 14,7:1 | 13,9:1 | 12,7:1 | 14,7:1 |
| le scénario | 12,4:1 | 11,2:1 | 10,4:1 | 12,5:1 |
| le mois | 12,0:1 | 11,0:1 | 9,5:1 | 12,1:1 |
| le jour | 13,6:1 | 13,3:1 | 10,7:1 | 13,6:1 |
| les deux mesures | 16,9:1 | 15,3:1 | 18,1:1 | 17,4:1 |
| la couture | 12,3:1 | 12,6:1 | 9,0:1 | 12,0:1 |
| les repères du graphe | 14,6:1 | 12,5:1 | 15,7:1 | 15,1:1 |
| la couture du graphe | 16,9:1 | 15,3:1 | 18,1:1 | 17,4:1 |
| comparer | 14,6:1 | 12,5:1 | 15,7:1 | 15,1:1 |
| la provenance | 8,9:1 | **8,2:1** | 10,1:1 | 9,4:1 |

**Plancher : 7,9:1 sur la fenêtre haute, 8,2 sur la courte**, porté par le
dépliant *d'où viennent ces journées*, au printemps — le dernier texte de la
page, donc le plus bas sur le dégradé. C'est **la fenêtre courte qui donne les
meilleurs rapports**, la page y étant proportionnellement plus haute que le
dégradé qu'elle traverse.

**Il a changé de porteur en montant**, quand le troisième panneau du graphe a
allongé la page de 1472 à 1705 px : l'étiquette de couture, qui le tenait à 7,7:1
en été, est poussée plus bas et passe à 8,6. Rien à en conclure de général — un
déplacement le long d'un dégradé se renverse au changement de mise en page
suivant.

**L'été est le plus sombre des quatre sols, et donc le plus tendu.** Les trois
autres descendent moins vite et laissent partout plus de marge ; c'est la page
dessinée sur la maquette qui fixe le plancher, pas celles qui en dérivent.

### Ce que les lignes recouvrent

**Le graphe n'a qu'une ligne alors qu'il écrit quatre choses** — la graduation,
les repères de date, les mois et le nom de l'année comparée. Ce sont une seule
encre sur un seul papier ; quatre lignes auraient publié quatre fois le même
nombre. La bascule *comparer* en a une à elle parce qu'elle est sur le papier du
graphe et non sur le ciel.

**Les deux lignes du graphe ne bougent pas d'un dixième d'une saison à l'autre**,
comme les cartes : elles sont sur le papier, qui ne tourne pas.

**Les deux températures ne sont pas des lignes de cette table.** Elles ne sont pas
sur la carte mais sur leur aplat de couleur ; mesurées contre la carte, le script
rapporte du blanc sur blanc à 1,0:1. Le rapport qui veut dire quelque chose est
celui de l'encre contre sa propre bande, et il est publié neuf fois par la table
de la rampe → [`docs/application.md`](../docs/application.md).

## Où le rapport ne suffit pas

Deux limites de la méthode, l'une et l'autre rencontrées en travaillant ces pages.

**Un rapport ne sait rien de la finesse des traits.** L'avertissement de l'accueil
mesurait 5,9:1 en italique et restait pénible à lire ; c'est ce qui a fait
renoncer à l'italique, non le contraste.

**Il est construit pour du texte sur un fond**, et n'a rien à dire de deux fonds
proches. Le panneau de candidats de l'accueil avait été essayé à 97 % d'opacité :
la date en dessous ressortait à 1,06:1 contre le panneau, ce que le rapport
déclare négligeable et que l'œil lit sans peine. Le panneau est plein pour cette
raison.

**Deux valeurs ne se lisent pas dans les tables ci-dessus** et sont mesurées à
part, chacune sur son propre fond :

| | |
|---|---|
| le marquage de segment des champs de date | 4,3:1 Firefox, 3,3:1 Chromium |
| le gris de l'année comparée, sur le papier du graphe | 3,44:1 |
