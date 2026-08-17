# DevOps — chaîne, conteneurs, observabilité

Ce document décrit **ce qui existe et s'exécute**. Ce qui est écrit mais
inactif faute d'infrastructure est signalé comme tel, section par section.

## Vue d'ensemble

```
                          GitHub
                             │
                    push / pull request
                             │
                             ▼
              ┌──────────────────────────────┐
              │       GitHub Actions         │
              ├──────────────────────────────┤
              │  backend      flake8+pytest  │
              │  frontend     eslint+build   │   en parallèle
              │  dependances  pip-audit,npm  │
              │  securite     Trivy (dépôt)  │
              └──────────────┬───────────────┘
                             │  tous verts
                             ▼
              ┌──────────────────────────────┐
              │   images (matrice ×2)        │
              │   build → Trivy → SBOM       │
              └──────────────┬───────────────┘
                             │  branche main
                             ▼
                   GHCR  ghcr.io/<dépôt>/{backend,frontend}
                   étiquettes : latest · sha · vX.Y.Z
                             │
                             ▼
              ┌──────────────────────────────┐
              │  assemblage (main seulement) │
              │  compose up → /api/health    │
              │  → flask db upgrade          │
              └──────────────┬───────────────┘
                             │
                             ▼
                   Déploiement (inactif)
                   SSH → compose pull → up -d
                   → migrations → /api/ready
                   → retour arrière si échec
```

## 1. Intégration continue

`.github/workflows/ci.yml`, déclenchée sur `push` et `pull_request` vers
`main` et `dev`.

| Travail | Outils | Bloquant | Quand |
|---|---|---|---|
| `backend` | flake8, pytest (170 tests) | oui | toujours |
| `frontend` | ESLint, `next build` | oui | toujours |
| `dependances` | pip-audit, npm audit | non | toujours |
| `securite` | Trivy `fs` (vuln + secrets + config) | non | toujours |
| `images` | Buildx, Trivy `image`, Syft | oui | toujours (publication sur `main`) |
| `assemblage` | Docker Compose, migrations | oui | `main` seulement |

Les quatre premiers s'exécutent en parallèle. L'ordre suit le coût : une faute
de style se détecte en trente secondes, une image se construit en plusieurs
minutes.

**Une exécution est annulée si une nouvelle poussée arrive** sur la même
branche (`concurrency` + `cancel-in-progress`) : inutile de tester un commit
déjà remplacé.

## 2. Sécurité

**Trivy sur le dépôt** — cherche les dépendances vulnérables, les secrets
écrits en dur et les erreurs de configuration. Le second point compte autant
que le premier : une clé oubliée dans un fichier est la faille la plus banale
qui soit.

**Trivy sur chaque image** — analyse les paquets système de l'image
construite, avec `ignore-unfixed: true` : une faille sans correctif amont est
signalée mais ne fait pas échouer.

**Aucun de ces contrôles n'est bloquant, et c'est délibéré.** Une image de base
accumule toujours quelques vulnérabilités de niveau haut. Bloquer dessus
reviendrait à ne plus jamais livrer — et, très vite, à désactiver l'alerte.
Le seuil doit être relevé quand le projet passe en production réelle.

**Les résultats vont dans l'onglet « Security » du dépôt**, au format SARIF :
datés, dédoublonnés, suivis dans le temps. Ils ne sont pas noyés dans un
journal d'exécution.

**Audit des dépendances** — `pip-audit` sur `requirements.txt`, `npm audit
--audit-level=high` sur le frontend. Non bloquants : leur code de sortie est
absorbé et converti en avertissement. Un travail qui passe au vert tout en
affichant des annotations rouges est un tableau de bord qui se contredit, et
qu'on finit par ne plus lire.

**Dette connue** : l'action Trivy est référencée par `@master` et non par une
version figée. C'est l'usage documenté par le projet, mais épingler une
version publiée est meilleure pratique — à faire dès qu'une étiquette aura été
vérifiée dans la liste des versions de l'action.

## 3. Inventaire logiciel (SBOM)

Chaque image publiée reçoit un inventaire au format **SPDX JSON**, produit par
Syft et attaché à l'image (`sbom: true` dans Buildx) puis conservé comme
artefact pendant 90 jours.

Son intérêt est concret. Quand une faille sort sur une bibliothèque, la
question n'est pas « est-elle grave ? » mais « l'avons-nous ? ». Avec un
inventaire, la réponse prend quelques secondes ; sans, il faut reconstruire
l'image pour aller regarder.

Consultation : onglet *Actions* → exécution → *Artifacts* → `sbom-backend`.

## 4. Images et versions

Trois familles d'étiquettes, posées par `docker/metadata-action` :

| Étiquette | Signification |
|---|---|
| `latest` | dernier état de `main` |
| `sha-a1b2c3d` | un commit précis — **toujours présente** |
| `v1.2.0`, `v1.2` | version publiée, posée par une étiquette Git |

L'étiquette par empreinte est celle qui compte : elle répond sans ambiguïté à
« quelle version tourne en production ? », et elle rend le retour arrière
possible puisque chaque image reste dans le registre.

Publier une version :

```bash
git tag v1.0.0 && git push origin v1.0.0
```

### Optimisation des images

Le frontend est construit en **trois étapes** — dépendances, construction,
exécution. Les dépendances sont installées avant que le code ne soit copié,
donc modifier un composant ne réinstalle pas les paquets. Seule la dernière
étape devient l'image finale : ni sources, ni outils de construction, ni cache
npm. Next produit une sortie autonome (`output: "standalone"`) qui n'embarque
que les dépendances réellement atteintes. Le processus tourne sous un compte
sans privilèges (`nextjs`, uid 1001).

Le backend n'est pas multi-étapes, et c'est assumé : PyTorch, le modèle
linguistique de spaCy et celui des plongements sont nécessaires à l'exécution,
pas seulement à la construction. Le gain réel serait de quelques dizaines de
mégaoctets sur une image qui en pèse plusieurs centaines, au prix d'un
Dockerfile nettement moins lisible. Une variante processeur de PyTorch est en
revanche installée explicitement, ce qui évite environ 800 Mo de bibliothèques
CUDA inutiles sans carte graphique.

Le cache de construction est porté par la chaîne (`type=gha`). Sans lui, le
backend réinstallerait PyTorch et les modèles à chaque exécution, soit plus de
dix minutes.

## 5. Observabilité

### Sondes

| Route | Question | Usage |
|---|---|---|
| `/api/health` | le processus répond-il ? | redémarrage automatique |
| `/api/ready` | les dépendances répondent-elles ? | mise en service |

La distinction est celle qu'attend un orchestrateur. Un processus vivant mais
sans base de données ne doit pas recevoir de trafic ; le redémarrer n'y
changerait rien, alors qu'attendre, si. `/api/ready` renvoie **503** si la base
est injoignable, et rapporte l'état des modèles d'IA **sans les rendre
bloquants** : leur absence dégrade l'analyse, elle n'empêche pas de servir.

### Identifiant de requête

Chaque requête reçoit un identifiant, renvoyé dans l'en-tête `X-Request-ID` et
inscrit dans le journal avec la méthode, le chemin, le code de retour et la
durée. Un identifiant fourni par l'appelant est conservé — c'est ce qui
permettra de suivre un appel à travers plusieurs services.

Sans lui, un utilisateur qui signale « ça a planté » ne donne rien
d'exploitable. Avec lui, une recherche dans les journaux suffit.

### Mesure du traitement des CV

Chaque analyse chronomètre ses six étapes, et le résultat est joint au détail
du score (`score_details.mesures`) :

```json
{
  "etapes_ms": {
    "extraction": 412,
    "analyse_structurelle": 318,
    "similarite_semantique": 507,
    "modele_appris": 96,
    "calcul_du_score": 38,
    "controles_anomalies": 71
  },
  "total_ms": 1448,
  "etape_la_plus_longue": "similarite_semantique",
  "etapes_en_echec": []
}
```

Le coût se répartit très inégalement — la reconnaissance optique et les
plongements dominent. Quand une analyse prend huit secondes, savoir *laquelle*
des six étapes les a consommées change complètement ce qu'il faut corriger.
Une étape qui échoue est mesurée puis marquée : c'est précisément l'étape lente
qui casse qu'on cherche à voir.

### Traçabilité des analyses

Chaque analyse consigne ce qui l'a produite (`score_details.provenance`) :

```json
{
  "version_moteur": "ats-4.0",
  "modele_semantique": "paraphrase-multilingual-MiniLM-L12-v2",
  "methode_similarite": "plongements",
  "modele_appris": "rf-binaire-1.0",
  "commit": "a1b2c3d",
  "analyse_le": "2026-08-17T09:14:22Z"
}
```

Un score n'est comparable dans le temps que si l'on sait avec quoi il a été
calculé. Le moteur de règles évolue, le modèle est réentraîné. C'est ce bloc
qui permet de répondre à un candidat qui conteste : « voici exactement ce qui a
produit ce chiffre ». Le modèle de plongements n'est nommé que s'il a
réellement servi — le citer sur un repli lexical serait faux.

`commit` provient de `GIT_SHA`, injecté au déploiement. En développement, la
valeur est `developpement` plutôt qu'une empreinte inventée.

## 6. Maintenance des dépendances

`.github/dependabot.yml` : pip, npm, GitHub Actions et Docker. Une montée de
version ouvre une demande de fusion, sur laquelle la chaîne s'exécute
normalement — rien n'est fusionné sans preuve que rien ne casse.

Le rythme est hebdomadaire et plafonné à cinq demandes ouvertes. Un dépôt qui
en reçoit quinze par jour finit par les fermer sans les lire : la fréquence
décide si l'outil sert ou nuit.

Trois dépendances sont **exclues des montées majeures** : `numpy` doit rester
en 1.x (spaCy et thinc sont compilés contre cette version), `spacy` et `torch`
pour la même raison de compatibilité binaire.

## 7. Déploiement — **inactif**

`.github/workflows/deploiement.yml` décrit un déploiement réel : connexion SSH,
récupération des images depuis le registre, migrations, vérification, retour
arrière automatique en cas d'échec. `docker-compose.prod.yml` démarre les
images publiées au lieu de les reconstruire — reconstruire sur le serveur
reviendrait à déployer quelque chose que personne n'a testé.

**Rien de tout cela ne s'exécute aujourd'hui**, faute de serveur. Le workflow
échoue immédiatement avec un message explicite si les secrets sont absents,
plutôt que de faire semblant de réussir.

Pour l'activer — un VPS et quatre secrets suffisent :

```
SSH_HOTE             adresse du serveur
SSH_UTILISATEUR      compte de déploiement (pas root, membre du groupe docker)
SSH_CLE_PRIVEE       clé privée sans phrase de passe
CHEMIN_DEPLOIEMENT   répertoire contenant .env et docker-compose.prod.yml
```

Sur le serveur : Docker installé, le fichier `.env` renseigné, et
`docker-compose.prod.yml` copié.

### Différences entre environnements

Aucun code n'est dupliqué. Ce qui change tient dans `.env` et le fichier
compose : `FLASK_ENV`, `DATABASE_URL`, `FRONTEND_ORIGIN`, `IMAGE_TAG`. En
production la base **ne publie aucun port** — elle n'est joignable que depuis
le réseau interne.

### Retour arrière

Chaque image reste dans le registre : revenir en arrière consiste à remettre
en ligne une étiquette précédente. C'est la même opération qu'un déploiement,
ce qui est exactement l'intérêt — aucune procédure spéciale à se rappeler dans
l'urgence.

Automatique : si `/api/ready` ne répond pas après déploiement, le workflow
restaure la version notée avant bascule.

Manuel, sur le serveur :

```bash
cd /chemin/deploiement
sed -i 's|^IMAGE_TAG=.*|IMAGE_TAG=sha-abc1234|' .env
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

Ou depuis GitHub : *Actions* → *Déploiement* → *Run workflow* → saisir
l'étiquette voulue.

**Les migrations, elles, ne reviennent pas en arrière automatiquement.** Une
migration destructrice ne se rattrape pas en redémarrant une image : c'est la
raison pour laquelle les migrations du projet sont additives (ajout de colonnes
nullable ou avec `server_default`).

## 8. Protection de branche — à configurer à la main

Ces règles ne peuvent pas être posées depuis le dépôt : elles vivent dans les
paramètres GitHub. *Settings → Branches → Add rule* sur `main` :

- Require a pull request before merging
- Require status checks to pass : `Backend — lint et tests`,
  `Frontend — lint et build`, `Images Docker`
- Require branches to be up to date before merging
- Do not allow bypassing the above settings

Tant que ce n'est pas fait, rien n'empêche de pousser directement sur `main`.

## 9. Ce qui manque

**Tests de bout en bout.** Aucun test ne pilote un navigateur. Les parcours
critiques sont couverts au niveau de l'API — notamment le cloisonnement entre
recruteurs, onze tests écrits du point de vue de l'attaquant — mais l'interface
n'est validée que par sa compilation.

**Métriques exposées.** Les durées sont mesurées et journalisées, non exposées
sur un point d'accès Prometheus. C'est le prolongement naturel du module
`services/observabilite.py` : les mesures existent déjà, il manque le format et
la collecte.

**Environnement de pré-production distinct.** Le workflow prévoit la cible,
aucune infrastructure ne la porte.

## 10. Commandes

```bash
# Développement
docker compose up -d --build
docker compose exec backend flask db upgrade
docker compose exec backend flask seed

# Vérifications, identiques à celles de la chaîne
docker compose exec backend flake8 app tests
docker compose exec backend pytest -q
cd frontend && npm run lint && npm run build

# Sondes
curl localhost:5000/api/health
curl localhost:5000/api/ready

# Production (sur le serveur)
IMAGE_TAG=v1.0.0 docker compose -f docker-compose.prod.yml pull
IMAGE_TAG=v1.0.0 docker compose -f docker-compose.prod.yml up -d
```
