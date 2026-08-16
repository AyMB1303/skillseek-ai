# Intégration et livraison continues

## Ce qui est en place

L'outillage est **GitHub Actions**, décrit dans `.github/workflows/ci.yml`.
La chaîne se déclenche à chaque poussée et à chaque demande de fusion sur
`main` et `dev`, et se lit en quatre travaux.

| Travail | Ce qu'il vérifie | Quand |
|---|---|---|
| `backend` | `flake8` sur `app` et `tests`, puis `pytest` | toujours |
| `frontend` | `npm ci`, `npm run lint`, `npm run build` | toujours |
| `images` | construction des deux images Docker ; publication sur GHCR | publication sur `main` seulement |
| `assemblage` | `docker compose up`, sonde de vie de l'API, migrations | `main` seulement |

Les deux premiers s'exécutent en parallèle ; les deux suivants attendent
qu'ils réussissent. L'ordre suit le coût : une faute de style se détecte en
trente secondes, une image se construit en plusieurs minutes.

## Choix expliqués

**Les tests n'ont besoin d'aucune base de données.** `TestingConfig` pointe
sur SQLite en mémoire. La chaîne démarre donc sans service PostgreSQL, ne peut
pas échouer pour une raison d'infrastructure, et chaque test repart d'un schéma
neuf. Le prix de ce choix est assumé : les particularités de PostgreSQL — types
`JSON`, contraintes `server_default` — ne sont pas couvertes par les tests, elles
le sont par le travail `assemblage` qui applique les migrations sur une vraie
base.

**Le registre est GHCR.** Il est inclus dans le dépôt GitHub, ne demande ni
compte tiers ni moyen de paiement, et l'authentification se fait avec le jeton
`GITHUB_TOKEN` fourni automatiquement à chaque exécution — aucun secret à
gérer. Chaque image reçoit deux étiquettes : `latest` et l'empreinte courte du
commit, ce qui permet de savoir exactement quel code tourne dans une image
donnée.

**Le cache de construction est porté par la chaîne** (`type=gha`). Sans lui,
l'image backend réinstallerait PyTorch, le modèle linguistique de spaCy et
celui des plongements à chaque exécution, soit plus de dix minutes. C'est aussi
la raison pour laquelle le travail `assemblage` est réservé à `main`.

**Les images sont construites même hors de `main`, mais pas publiées.** Une
demande de fusion valide ainsi ses Dockerfile sans polluer le registre, et une
contribution externe n'a pas besoin de droits d'écriture.

## Conteneurisation

Trois services dans `docker-compose.yml` : `db` (PostgreSQL 16), `backend`
(Flask) et `frontend` (Next.js). `docker compose up` suffit à lever la
plateforme entière ; aucune installation de Python ou de Node n'est requise sur
la machine hôte.

L'image du frontend est construite en **trois étapes**. Les dépendances sont
installées avant que le code ne soit copié, de sorte qu'une modification d'un
composant ne réinstalle pas les paquets. Seule la dernière étape devient
l'image finale : ni les sources, ni les outils de construction, ni le cache npm
n'y figurent. Next produit une sortie autonome (`output: "standalone"`), qui
n'embarque que les dépendances réellement atteintes par le code — quelques
dizaines de mégaoctets au lieu de plusieurs centaines. Le processus tourne sous
un compte sans privilèges.

Deux sondes de vie sont déclarées : PostgreSQL par `pg_isready`, l'API par un
appel à `/api/health`. Le frontend n'attend pas que l'API soit prête, seulement
qu'elle soit démarrée : une page qui s'affiche avec un message d'erreur vaut
mieux qu'une page qui ne s'affiche pas.

`NEXT_PUBLIC_API_URL` est un **argument de construction** et non une variable
d'exécution. Une variable `NEXT_PUBLIC_*` est inscrite dans le paquet envoyé au
navigateur au moment de la compilation ; la changer au démarrage du conteneur
n'aurait aucun effet.

## Ce qui n'est pas en place

Aucun **déploiement continu vers un environnement hébergé**. La chaîne
construit et publie des images ; elle ne les déploie nulle part, faute
d'infrastructure disponible dans le cadre du stage. Le pas manquant est
volontairement court : les images étant déjà versionnées sur un registre, un
déploiement se réduirait à un `docker compose pull && up -d` sur un serveur
cible.

Aucun **test de bout en bout** (Playwright ou Cypress). Les parcours critiques
sont couverts au niveau de l'API par les tests d'intégration, notamment le
cloisonnement entre recruteurs, mais aucun test ne pilote un navigateur.

Aucune **analyse de vulnérabilités** des dépendances ni des images.

## Commandes locales

```bash
docker compose up -d --build      # lève la plateforme entière
docker compose exec backend flask db upgrade
docker compose exec backend flask seed
docker compose exec backend pytest -q
docker compose exec backend flake8 app tests
cd frontend && npm run lint && npm run build
```
