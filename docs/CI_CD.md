# Intégration et livraison continues

## Ce qui est en place

L'outillage est **GitHub Actions**, décrit dans `.github/workflows/ci.yml`.
La chaîne se déclenche à chaque poussée et à chaque demande de fusion sur
`main` et `dev`, et se lit en dix travaux répartis sur trois étages.

**Étage 1 — vérification.** Huit travaux en parallèle, tous rapides, chacun
répondant à une question que les autres ne posent pas.

| Travail | Ce qu'il vérifie | Question posée |
|---|---|---|
| `backend` | `flake8` puis `pytest` | le raisonnement métier est-il juste ? |
| `frontend` | `npm ci`, ESLint, Vitest, construction | l'interface se construit-elle ? |
| `dependances` | `pip-audit`, `npm audit` | mes dépendances ont-elles des failles connues ? |
| `infrastructure` | `terraform fmt`, `init`, `validate`, Trivy | l'infrastructure décrite est-elle valide ? |
| `orchestration` | `kubectl kustomize`, kubeconform, Trivy, admission sur cluster kind | les manifestes sont-ils acceptés par un vrai serveur d'API ? |
| `secrets` | Gitleaks sur l'historique Git complet | ai-je déjà publié un secret ? |
| `securite` | Trivy sur le système de fichiers | le dépôt contient-il une faille ou une clé ? |
| `sast` | Bandit, Semgrep | ai-je écrit du code intrinsèquement risqué ? |

**Étage 2 — images.** `images` construit les deux images Docker, les analyse
avec Trivy, produit un inventaire logiciel (SBOM) et ne publie que sur `main`
ou sur une étiquette de version.

**Étage 3 — assemblage.** `assemblage` lève la pile complète avec Compose,
applique les migrations sur une vraie base PostgreSQL, puis lance une analyse
dynamique OWASP ZAP contre l'interface en marche.

L'ordre suit le coût : une faute de style se détecte en trente secondes, une
image se construit en plusieurs minutes.

## Les cinq contrôles de sûreté

Ils ne se recouvrent pas, et l'ordre dans la chaîne suit le moment où leur
cible devient disponible — vérifier les secrets avant le code, le code avant
l'image, l'image avant l'application en marche.

| Étape | Contrôle | Outil |
|---|---|---|
| Après récupération du code | secrets dans l'historique Git | Gitleaks |
| Sur les sources | analyse statique (SAST) | Bandit, Semgrep, CodeQL |
| Sur le dépôt | dépendances vulnérables, clés en dur | Trivy `fs` |
| Sur `deploiement/` et `k8s/` | mauvaise configuration d'infrastructure | Trivy `config` |
| Après chaque construction | vulnérabilités de l'image | Trivy `image` |
| Sur la pile en exécution | analyse dynamique (DAST) | OWASP ZAP |

**Pourquoi le DAST en plus du SAST.** L'analyse statique lit le code sans
l'exécuter : elle reconnaît des motifs réputés dangereux, et ne voit donc
jamais ce qui n'existe qu'à l'exécution — un en-tête de sécurité absent, une
page d'erreur trop bavarde, un cookie sans attribut. ZAP fait l'inverse : il
ignore le code et interroge le service comme le ferait quelqu'un depuis
l'extérieur.

**Pourquoi Gitleaks en plus de Trivy.** Trivy cherche des secrets dans les
fichiers présents. Un secret supprimé, lui, reste dans l'historique : le
commit qui l'a introduit existe toujours. Gitleaks relit chaque commit depuis
le premier, ce qui répond à une question différente.

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
