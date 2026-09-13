# Déploiement — hébergement, image, mise en ligne

Où le site tourne, et comment il y arrive. Ce qu'il sert →
[`application.md`](application.md) ; ce qu'il refuse de promettre →
[`projet.md`](projet.md).

Ce document porte les décisions arrêtées et l'état de leur exécution. Le chemin
qui y a mené est dans [`journal.md`](journal.md).

---

## Ce que le site demande à un hébergeur

Peu, et c'est le fait déterminant. L'inventaire tient en quatre points, dont
chacun retire une contrainte.

**Aucun état, aucune base de données.** Le serveur valide les entrées, applique
la correction de nébulosité, le bloc de transformation et les deux règles de
classe, puis rend du JSON. Deux requêtes n'ont rien en commun. La montée en
charge se fait par simple multiplication des instances, sans coordination entre
elles.

**Aucun secret.** Les données sont récupérées par le navigateur, géocodage
compris, parce que les limites d'Open-Meteo s'appliquent par adresse IP →
[`application.md`](application.md), *Répartition entre client et serveur*. Le
serveur n'appelle aucune API, ne détient aucune clé, et ne réclame donc aucune
variable d'environnement.

**Une ressource résidente de 3,9 Mo.** La table de correction est lue une fois
au démarrage, par `lifespan`, et non à la première visite. Un démarrage échoue
donc bruyamment plutôt que de servir une panne au premier visiteur.

Cette lecture a longtemps été présentée ici comme le poste qui pèse sur le
réveil à froid. **La mesure du 10 septembre 2026 dit le contraire** : elle coûte
81 ms sur un démarrage complet de 950. Le poste dominant est l'import de FastAPI
et de Pydantic, à 522 ms, c'est-à-dire une dépense que le code du projet ne
contrôle pas.

**Trois pages statiques servies par le même processus.** `web/` est monté par
`mount_web`. Rien n'impose de le séparer aujourd'hui ; un CDN placé devant reste
possible plus tard sans que le serveur change.

Il en découle qu'aucune fonctionnalité d'hébergeur n'est requise : ni disque
persistant, ni base, ni coffre à secrets, ni tâche de fond. Le choix se joue
donc ailleurs que sur la technique.

---

## L'hébergeur retenu

**Scaleway Serverless Containers**, région `fr-par`, à partir d'un Dockerfile.

Deux raisons, dont aucune n'est technique :

- **La juridiction.** Le projet est français et d'intérêt public ; l'hébergement
  l'est aussi.
- **L'échelle disponible dans le même compte.** Stockage objet et PostgreSQL
  managé attendent au même endroit le jour où le projet hébergerait ses propres
  séries plutôt que d'interroger Open-Meteo.

**Ce qui a été écarté.** Fly.io restait devant sur le confort d'exploitation et
sur la latence de réveil, et perd sur les deux points ci-dessus. Vercel a été
écarté malgré sa gratuité : sa configuration ne se transporte nulle part, ce qui
est exactement le défaut que la section suivante cherche à éviter.

---

## Le Dockerfile compte plus que l'hébergeur

C'est la pièce qui rend le choix réversible. Une application décrite par un
Dockerfile et n'exigeant ni état ni secret se déplace d'un hébergeur à l'autre
en une demi-journée ; une application décrite par les réglages d'une console ne
se déplace pas. L'arbitrage ci-dessus est donc tranché sans être définitif, et
il n'a pas à être rouvert pour rester révocable.

Conséquence de méthode : **rien de ce que l'image a besoin de savoir ne vit dans
la console de l'hébergeur.** Le port d'écoute est la seule chose que la
plateforme fournit, par la variable `PORT` ; l'image la lit et ne la fixe pas.

### Ce que l'image contient

`src/`, `web/`, `pyproject.toml`, et les trois dépendances d'exécution
déclarées : `fastapi`, `pydantic`, `uvicorn[standard]`. Les extras
`calibration`, `dev`, `screenshots` et `charts` restent dehors : rien de ce que
le serveur fait ne collecte, ne teste, ne photographie ni ne dessine.

Une fois la table témoin écartée, **la charge utile pèse 4,5 Mo**, dont 3,9 pour
la table de correction elle-même.

### Ce que le contexte de build contient, s'il n'est pas tenu

**874 Mo**, mesuré le 9 septembre 2026, pour 4,5 Mo utiles. Trois répertoires en
répondent, et aucun n'a sa place dans une image :

| Répertoire | Poids | Ce que c'est |
|---|---|---|
| `venv/` | 321 Mo | l'environnement local |
| `data/` | 320 Mo | les payloads bruts de la collecte |
| `.playwright/` | 199 Mo | le navigateur de `screenshots.py` et `ink_contrast.py` |

Sans `.dockerignore`, Docker transfère l'intégralité du répertoire au démon de
construction avant d'exécuter la première instruction, et un `COPY .`
l'embarquerait ensuite dans l'image. Chaque construction déplacerait donc 874 Mo
pour en installer 4,5. Le fichier n'est pas facultatif.

Il écarte également `shots/`, `design/`, `.git/`, `tests/`,
`scripts/`, les caches d'outillage, et la table témoin
`cloud_correction_placeholder.json`, qui est déjà refusée au démarrage mais n'a
aucune raison de voyager.

---

## Les trois pièges, mesurés avant d'écrire

Ils ont été rencontrés à l'instruction du 6 septembre 2026, et se redécouvriraient
autrement.

**`pip install -e .` est obligatoire dans l'image.** `app.py` résout les pages
par `Path(__file__).resolve().parents[3] / "web"`. Une installation ordinaire
déplace le paquet dans `site-packages`, où ce calcul ne désigne plus la racine
du dépôt : `mount_web` trouve un répertoire absent, rend `False`, et le serveur
démarre normalement en servant une 404 sur `/`. La panne est muette, et l'API
répond correctement pendant ce temps.

Vérifié le 9 septembre 2026 en installant le paquet sans `-e` dans un
environnement jetable : `/` rend 404, `/api/config` rend 200, et le journal ne
porte rien d'autre que la ligne de 404 elle-même. Le `Dockerfile` en fait donc
une assertion exécutée à la construction, plutôt qu'un commentaire à relire :
l'image ne se construit pas si les pages ne sont pas là où `app.py` les
cherche.

**Le `.dockerignore` est indispensable**, pour la raison chiffrée ci-dessus.

**La construction se fait en `--platform linux/amd64`.** Le poste de
développement est un Mac ARM ; une image construite sans ce drapeau ne démarre
pas chez l'hébergeur.

---

## Les décisions de mise en ligne

Arrêtées le 6 septembre 2026.

| Question | Décision |
|---|---|
| Hébergeur | Scaleway Serverless Containers, `fr-par`, par Dockerfile |
| Veille | **min-scale 0** au départ ; instance permanente seulement si le réveil à froid gêne, et mesuré une fois en ligne |
| Domaine | sous-domaine de l'hébergeur d'abord, domaine propre acheté ensuite |
| Visibilité | public et indexé, sous la réserve décrite ci-dessous |

**La veille se décide après la mesure, non avant.** Le démarrage de
l'application est chronométré, et il est court : 950 ms en natif, 1,6 s sous
émulation. Ce n'est pas encore le réveil à froid de l'hébergeur, qui ajoute
l'approvisionnement de l'instance et le chargement de l'image ; c'est la part
qui dépend du projet, et elle ne justifie pas à elle seule une instance
permanente. La décision reste donc suspendue à une mesure prise en ligne.

---

## Ce que cela coûte

Tarifs relevés le 10 septembre 2026 ; les calculs qui en découlent sont les
nôtres et se refont si les tarifs bougent.

Scaleway facture le temps pendant lequel un conteneur tourne, en mémoire et en
processeur. Les entrées et sorties réseau sont gratuites, le stockage éphémère
aussi. La franchise mensuelle est de **400 000 Go-seconde** et **200 000
vCPU-seconde**.

Rapportée à une taille plausible pour cette application, 512 Mo et un quart de
vCPU, cette franchise vaut **222 heures de conteneur allumé par mois**, soit
sept heures par jour. Avec min-scale 0, un conteneur ne tourne que pendant les
visites : il faudrait un trafic important pour en sortir.

**Ce chiffre éclaire la décision de veille.** Une instance allumée en permanence
consommerait 730 heures par mois et coûterait donc, franchise déduite, environ
**6,40 € par mois**. Le confort d'un réveil instantané a un prix connu et
modeste ; la décision se prendra au vu de la mesure en ligne, sans que le coût
pèse d'un côté ou de l'autre.

Le registre d'images est gratuit jusqu'à 75 Go et l'image en occupe 0,19. **Un
point à vérifier avant de pousser** : cette gratuité paraît conditionnée à des
images publiques. Le code étant déjà public, la contrainte devrait être sans
effet ici, mais elle n'a pas été confirmée.

---

## Ce qui reste ouvert

**La condition attachée à l'indexation a perdu son objet.** La visibilité
publique était subordonnée à une relecture du message de refus hors grille. Ce
message n'existe plus : depuis le 7 septembre 2026, un lieu ne fait plus jamais
refuser une recherche → [`application.md`](application.md), *Hors de la zone
couverte*.

Ce qui a pris sa place est le régime dégradé lui-même. Hors de France, les
journées simulées sont servies brutes, ensoleillées de 8 à 11 points de trop, et
la bande s'éclaircit visiblement à la couture entre la prévision et la
simulation. **Aucun texte d'interface ne le dit aujourd'hui au visiteur**, alors
que le contrat porte déjà `grid: null` et permettrait de le dire.

La question à trancher est donc : la réserve tombe-t-elle, ou se reporte-t-elle
sur ce texte ? Le texte, s'il est écrit, sera de la main du porteur du projet.

---

## Ce que la construction a établi

Mesuré le 10 septembre 2026, Docker Desktop 4.90, sur M2 Pro.

| | |
|---|---|
| Construction `linux/amd64` | 23 s |
| Image, couches décompressées | 188 Mo, dont 43 de dépendances et 4,5 de projet |
| Contenu de `/app` | `pyproject.toml`, `src/`, `web/`, et rien d'autre |
| Démarrage, natif `arm64` | 950 ms |
| Démarrage, `amd64` émulé | 1,6 s |
| Arrêt sur `SIGTERM` | 448 ms |

**Trois suppositions sont tombées.** La construction `amd64` depuis un Mac ARM
devait être lente : elle prend vingt-trois secondes, les roues `manylinux`
étant téléchargées toutes faites et l'émulation ne servant qu'à exécuter `pip`.
Le découpage en deux constructions, une native pour vérifier et une croisée pour
publier, ne se justifie donc pas. Et Python 3.13 n'est plus un pari : l'image se
construit et les extras compilés d'`uvicorn` s'installent.

**Les deux protections tiennent.** La liste blanche du `.dockerignore` laisse
`/app` avec exactement trois entrées, la table témoin restant dehors. L'assertion
de l'installation éditable s'exécute à la construction et passe. Le processus
tourne sous le compte `app`, prend `PORT` dans son environnement, et reçoit
lui-même le signal d'arrêt en tant que PID 1.

---

## Les étapes

1. **Ce document et la carte de `CLAUDE.md`.** Validation requise. *Écrit.*
2. **`Dockerfile` et `.dockerignore`.** Autonomie de développement. *Fait.*
3. **Construction `linux/amd64` et conteneur essayé en local.** *Fait*, résultats
   ci-dessus.
4. **Registre et déploiement** en `fr-par`, min-scale 0. *En attente d'un compte
   Scaleway*, que seul le porteur du projet peut créer. Dans l'ordre : compte
   créé et vérifié, `brew install scw`, clé d'API produite dans la console, puis
   `scw init` **lancé dans un terminal personnel** et non dans une session
   d'assistance, la clé secrète n'ayant aucune raison d'être lue. Le reste
   s'enchaîne : espace de registre, poussée de l'image, création du conteneur.
5. **Mesure du réveil à froid** en ligne, qui tranche la question de la veille.
6. **Domaine propre**, puis indexation, une fois la réserve levée.
