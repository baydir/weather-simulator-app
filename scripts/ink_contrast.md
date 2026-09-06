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
| la question | 11,2:1 | 11,3:1 | 11,3:1 |
| la promesse | 7,5:1 | 7,7:1 | 7,7:1 |
| l'étiquette *Lieu* | 7,1:1 | 7,4:1 | 7,4:1 |
| le champ *Lieu* | 6,4:1 | 6,7:1 | 6,7:1 |
| la bascule choisie | — | 9,3:1 | 7,5:1 |
| la bascule au repos | 7,1:1 | 7,5:1 | 8,0:1 |
| l'étiquette *Du* | — | 5,0:1 | — |
| le champ *Du* | — | **4,5:1** | — |
| l'étiquette *Saison* | — | — | 5,0:1 |
| le champ *Saison* | — | — | **4,5:1** |
| le bouton | — | 6,9:1 | 6,9:1 |
| l'avertissement | 5,7:1 | 5,9:1 | 5,9:1 |
| le lien documentation | 6,6:1 | 6,5:1 | 6,5:1 |

**Plancher : 4,5:1**, porté par les deux champs de date.

**Toute la table descend, et toujours pour la même raison.** Le pied a d'abord
gagné une note de trois lignes là où il en faisait une ; la note a ensuite gagné
sa période et la promesse une troisième ligne. La page grandit à chaque fois, le
dégradé — ancré au document — s'étire avec elle, et chaque encre finit par se
lire sur un fond plus sombre que celui contre lequel elle avait été choisie.
Aucune n'a été retouchée, sauf celle du lien.

**Le lien du pied est une ligne neuve de cette table, et il ne l'était pas par
hasard.** Il n'était mesuré nulle part : il avait pris l'encre sombre de la note
parce qu'il se posait à côté d'elle sur la bande orange, et il a glissé, note
après note, jusqu'au rouge sombre du bas. Relevé pour la première fois, il
sortait à **2,9:1** — sous les 4,5:1 qu'un texte demande et sous les 3:1 que
demande n'importe quelle marque. Ce qui échappe à la table échappe à la mesure,
et une ligne ajoutée le jour où l'on regarde est une ligne qui manquait depuis le
début.

**La correction est de mise en page et non d'encre** : la marge sous le pied
passe de 40 à 80 px, ce qui remonte la note et son lien sur la bande orange. Le
lien y lit 6,5:1, la note 5,9, et toute la table monte d'un demi-point au passage.
Les paliers ont été mesurés — 48 px donnent 3,5:1 au lien, 64 px 4,9 et 72 px 5,6 ;
au-delà de 80 le gain s'arrête, la page grandissant avec la marge et le dégradé
avec la page.

**Et cela ne tient qu'à cette fenêtre-là**, ce qui est le vrai constat de la
manœuvre. Voir la table des planchers ci-dessous : à 1280 × 720 et sur téléphone,
le pied tombe dans la bande sans encre et le lien y mesure 1,6:1 et 1,5:1, que la
marge vaille 40 px ou 80. **Aucune encre plate ne résout ce bloc** — le noir
plafonne à 4,0:1 dans cette bande et l'ivoire à 4,2 — et un blanc, qui passait
partout (5,7 à 10,0:1), fait une tache sur une page qui n'a pas d'autre blanc.
Ce qui le résoudrait est ce qui a résolu le bloc de comparaison sur l'autre page :
un sol opaque qui ne bouge pas → [`docs/application.md`](../docs/application.md).
**Arbitrage en attente.**

**La bande située entre 50 % et 65 % du dégradé ne porte aucune encre.** Le fond
y va de `#4b688b` à `#677390`, et à ces clartés le noir pur plafonne à 4,0:1 quand
l'ivoire de la page atteint 4,2. Ce n'est pas un choix de ton, c'est une hauteur :
le seul remède est que le formulaire n'y descende pas.

### Les autres tailles de fenêtre

La table n'est publiée que pour 1440 × 900. Planchers relevés ailleurs :

| Fenêtre | plancher | porté par |
|---|---|---|
| 1440 × 900 | **4,5:1** | les champs de date |
| 1280 × 720 | 1,6:1 | le lien documentation |
| 1440 × 1200 | 4,3:1 | le lien documentation |
| 390 × 844 | 1,5:1 | le lien documentation |

**Le lien du pied porte le plancher partout sauf sur la fenêtre de référence**, et
c'est la mesure qui a fait apparaître le problème plutôt que l'œil : sur la
fenêtre haute et sur téléphone, le pied se pose dans la bande sans encre du
dégradé, où l'encre sombre ne peut rien valoir. La marge de 80 px le sort de là
en 1440 × 900 seulement. En blanc, il mesurait 8,7:1, 7,9 et 10,0 à ces trois
tailles : c'est la seule encre plate qui passe partout, et elle a été écartée
pour l'œil, pas pour la mesure.

**L'avertissement mesure 6,6:1 ou mieux aux quatre tailles**, et c'est un
changement : il tombait à 3,7:1 sur la fenêtre haute, où il était le plancher. La note du pied
faisant maintenant trois lignes, la page dépasse la fenêtre de 1200 px au lieu
d'être étirée pour la remplir, et le pied retrouve le bas sombre du dégradé au
lieu de la bande claire. Le remède cherché était un arbitrage de mise en page ;
il est venu d'un changement de texte, ce qui n'était pas le plan.
→ [`docs/idees.md`](../docs/idees.md), dont le constat est à amender.

Le plancher reste ailleurs : **les champs de date**, à 3,8:1 sur fenêtre courte
et sur téléphone. Ceux-là ne sont pas une phrase que la règle 1 rend non
négociable, mais ils restent sous le seuil de 4,5:1.

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
| le lieu | 16,0:1 | 14,7:1 | 16,2:1 | 16,0:1 |
| la plage | 13,5:1 | 11,8:1 | 13,3:1 | 13,6:1 |
| nouvelle recherche | 15,4:1 | 14,3:1 | 14,5:1 | 15,4:1 |
| l'avertissement | 14,6:1 | 13,9:1 | 12,6:1 | 14,7:1 |
| le mois | 11,8:1 | 10,9:1 | 9,3:1 | 11,8:1 |
| le jour | 13,5:1 | 13,2:1 | 10,4:1 | 13,4:1 |
| les deux mesures | 16,9:1 | 15,3:1 | 18,1:1 | 17,4:1 |
| la couture | 12,3:1 | 12,6:1 | 8,9:1 | 12,0:1 |
| les repères du graphe | 14,6:1 | 12,5:1 | 15,7:1 | 15,1:1 |
| la couture du graphe | 16,9:1 | 15,3:1 | 18,1:1 | 17,4:1 |
| comparer | 14,6:1 | 12,5:1 | 15,7:1 | 15,1:1 |
| exporter | 7,9:1 | **6,7:1** | 8,4:1 | 8,1:1 |
| la provenance | 8,7:1 | 8,0:1 | 9,9:1 | 9,2:1 |

### 1280 × 720

Le dégradé étant ancré au document, une page raccourcie fait glisser chaque bloc
sur une autre portion. La page fait 1757 px au lieu de 1825, et tout se desserre
d'un cran :

| Texte | hiver | printemps | été | automne |
|---|---|---|---|---|
| le lieu | 16,1:1 | 14,8:1 | 16,5:1 | 16,1:1 |
| la plage | 13,6:1 | 11,9:1 | 13,5:1 | 13,7:1 |
| nouvelle recherche | 15,4:1 | 14,4:1 | 14,6:1 | 15,5:1 |
| l'avertissement | 14,8:1 | 14,0:1 | 13,0:1 | 14,8:1 |
| le mois | 12,1:1 | 11,0:1 | 9,7:1 | 12,2:1 |
| le jour | 13,8:1 | 13,4:1 | 10,9:1 | 13,8:1 |
| les deux mesures | 16,9:1 | 15,3:1 | 18,1:1 | 17,4:1 |
| la couture | 12,5:1 | 12,7:1 | 9,2:1 | 12,3:1 |
| les repères du graphe | 14,6:1 | 12,5:1 | 15,7:1 | 15,1:1 |
| la couture du graphe | 16,9:1 | 15,3:1 | 18,1:1 | 17,4:1 |
| comparer | 14,6:1 | 12,5:1 | 15,7:1 | 15,1:1 |
| exporter | 8,1:1 | **7,1:1** | 8,9:1 | 8,4:1 |
| la provenance | 8,9:1 | 8,3:1 | 10,2:1 | 9,5:1 |

**Plancher : 6,7:1 sur la fenêtre haute, 7,1 sur la courte**, porté par le bouton
*exporter mes données*, au printemps — l'avant-dernier texte de la page, donc
presque le plus bas sur le dégradé. C'est **la fenêtre courte qui donne les
meilleurs rapports**, la page y étant proportionnellement plus haute que le
dégradé qu'elle traverse.

**Le bouton a pris le plancher au dépliant en arrivant** : il se pose au-dessus
de lui, sur la même encre pâle, et son texte est plus petit d'un cran. Le
dépliant tenait 7,9:1 et passe à 8,0, poussé plus bas par la ligne qui vient de
s'insérer. Les deux restent loin des 4,5:1 qu'un texte demande.

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
