# Les deux fontes

Embarquées dans le projet, servies depuis `/static/fonts/`. **Aucune requête
vers un tiers à l'affichage** : la page reste servable sous une politique de
sécurité stricte, et rien ne se décale au chargement faute d'une ressource
distante qui tarde.

Ce sont des fontes **variables** : un seul fichier porte toute la plage de
graisses, donc une requête au lieu de quatre, et aucune graisse synthétique.

| Fichier | Fonte | Emploi | Poids |
|---|---|---|---|
| `inter.woff2` | Inter | texte courant, formulaire, mesures | 47 Ko |
| `source-serif.woff2` | Source Serif 4 | titres | 119 Ko |

Sous-ensemble latin uniquement — le site est en français, et le jeu complet
pèserait plusieurs fois cela.

## Licence

Les deux sont publiées sous **SIL Open Font License 1.1**, qui autorise
l'usage, la modification et la redistribution, y compris embarquée dans un
site. Le texte de la licence :

- Inter — <https://github.com/rsms/inter/blob/master/LICENSE.txt>
- Source Serif 4 — <https://github.com/adobe-fonts/source-serif/blob/release/LICENSE.md>

## Les remplacer

Déposer le `.woff2` ici et changer la déclaration `@font-face` correspondante
dans `web/static/css/style.css`. Les règles de la feuille lisent les jetons
`--font` et `--font-display`, jamais un nom de fonte en dur.
