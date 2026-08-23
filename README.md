# SkillSeek AI

**Plateforme de présélection de candidatures dont chaque note est justifiable.**

[![CI/CD](https://github.com/AyMB1303/skillseek-ai/actions/workflows/ci.yml/badge.svg)](https://github.com/AyMB1303/skillseek-ai/actions/workflows/ci.yml)
![Tests](https://img.shields.io/badge/tests-192%20reussis-brightgreen)
![Python](https://img.shields.io/badge/python-3.12-blue)
![Next.js](https://img.shields.io/badge/next.js-14.2-black)
![Licence](https://img.shields.io/badge/licence-usage%20pédagogique-lightgrey)

[![Ouvrir dans GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/AyMB1303/skillseek-ai)

**Essayer sans rien installer :** le bouton ci-dessus lève la plateforme
entière dans le navigateur — base de données, API et interface — avec un jeu
de démonstration déjà chargé. Comptez une dizaine de minutes au premier
démarrage, le temps de construire les images. Ouvrez ensuite le port 3000
depuis l'onglet « Ports ».

Un recruteur reçoit deux cents candidatures pour un poste. Les outils courants
lui rendent un classement sans lui dire pourquoi. SkillSeek AI fait l'inverse :
il lit chaque CV, le confronte à l'offre, et **restitue le détail du calcul** —
quelles compétences ont été trouvées, lesquelles manquent, et ce qui a fait
écarter un dossier.

Le principe qui gouverne le projet : **le système propose, l'humain tranche.**
Aucune candidature n'est supprimée, toute décision est motivée, et une note
contestée peut être reconstituée six mois plus tard.

![Détail d'une note et du profil reconstitué](docs/captures/05_detail_score_profil_ats.jpg)

---

## Ce que fait la plateforme

**Pour le candidat.** Il déclare ses compétences, son expérience et son diplôme ;
les offres lui sont présentées par proximité décroissante avec son profil. Il
voit les **compétences qui lui manquent** pour chaque offre — la seule chose
qu'il puisse corriger. *Aucune note ne lui est jamais communiquée* : un chiffre
sans son barème invite au malentendu.

**Pour le recruteur.** Chaque candidature reçoit une note sur 100, décomposée en
cinq composantes traçables, accompagnée du motif d'écartement s'il y a lieu. Un
écran d'analyse mesure ensuite si le classement tient ses promesses, en
confrontant la note calculée *avant* l'entretien au verdict porté *après*.

**Pour l'administrateur.** Validation des comptes recruteurs, gestion des rôles
et permissions, journal d'audit immuable, corbeille réversible.

## Comment la note est calculée

| Composante | Poids |
|---|---|
| Compétences obligatoires | 35 |
| Compétences souhaitées | 10 |
| Proximité sémantique avec l'offre | 25 |
| Expérience | 20 |
| Diplôme | 10 |

Un modèle d'apprentissage supervisé ajuste ensuite la note de **±8 points au
maximum**. Il ne peut jamais rattraper une candidature écartée par une règle
explicite, et son absence n'empêche aucune analyse d'aboutir.

**Règle de présélection.** En dessous de 50, la candidature est écartée du
classement — jamais supprimée, et toujours repêchable. Parmi celles au-dessus,
les dix meilleures forment la présélection.

## Deux propriétés que le code garantit

**Le cloisonnement par périmètre.** Les permissions répondent à « ce rôle
peut-il consulter des candidatures ? ». Elles ne répondent pas à « celle-ci ? ».
Deux recruteurs ont exactement les mêmes droits ; ce qui les sépare est la
chaîne de propriété recruteur → offre → candidature → CV. La vérification est
centralisée dans `backend/app/services/acces.py`, et onze tests écrits **du
point de vue de l'attaquant** échouent si elle est omise.

**Les permissions en temps réel.** Elles sont relues en base à chaque requête
sensible. Retirer un droit prend effet immédiatement, sans attendre
l'expiration des sessions ouvertes. Le rôle administrateur ne bénéficie
d'aucun contournement.

---

## Démarrage local

```bash
git clone https://github.com/AyMB1303/skillseek-ai.git
cd skillseek-ai
cp .env.example .env          # Windows : copy .env.example .env

docker compose up -d --build
docker compose exec backend flask db upgrade
docker compose exec backend flask seed
docker compose exec backend flask demo --reset
```

L'interface répond sur **http://localhost:3000**, l'API sur
**http://localhost:5000/api**.

`docker-compose.override.yml` est chargé automatiquement : le frontend démarre
en rechargement à chaud et le backend en mode debug. Rien d'autre à lancer.

### Comptes de démonstration

| Rôle | Identifiant | Mot de passe |
|---|---|---|
| Candidat | `y.tazi@example.ma` | `Demo@1234` |
| Recruteur | `s.lamrani@bcskills.ma` | `Demo@1234` |
| Administrateur | `admin@skillseek.local` | `Admin@1234` |

### Tests

```bash
cd backend
pip install -r requirements.txt
flake8 app tests
pytest -q
```

---

## Architecture

```
backend/app/
  blueprints/     61 routes HTTP — reçoivent, délèguent, répondent
  services/       le raisonnement métier, sans dépendance à HTTP
  models/         une classe par table (SQLAlchemy)
  middleware/     contrôle des permissions
frontend/src/
  pages/          22 écrans (un fichier = une URL)
  components/     éléments partagés
  lib/            appels API, thème, animations
.github/workflows/
  ci.yml          7 travaux d'intégration continue
```

**La séparation `blueprints` / `services` est délibérée.** Les services ignorent
qu'HTTP existe : ils prennent des objets Python et en rendent. C'est ce qui
permet de tester le moteur de notation sans démarrer de serveur web.

### Pile technique

Flask 3 · SQLAlchemy · PostgreSQL 16 · Alembic · JWT · bcrypt
Next.js 14 · React 18 · Tailwind CSS
spaCy · sentence-transformers · scikit-learn · Tesseract OCR
Docker · GitHub Actions · Trivy · Bandit · Semgrep

### Chaîne d'intégration continue

Sept travaux à chaque poussée : analyse statique et tests du service
applicatif, analyse statique et construction de l'interface, audit des
dépendances des deux écosystèmes, analyse du dépôt (Trivy), **analyse de
sûreté du code** (Bandit et Semgrep), construction et publication des images
avec leur inventaire logiciel, et démarrage de la pile complète.

Les images sont étiquetées par l'empreinte du commit qui les a produites :
chaque état du code correspond à un artefact déployable et identifiable.

---

## État du projet

Le périmètre fonctionnel est **complet**. Ce qui manque relève de
l'exploitation, et figure ici sans être déguisé en perspective :

- **Déploiement non activé** — la procédure est écrite et versionnée, mais
  aucune infrastructure n'a été mise à disposition dans le cadre du stage. Le
  projet dispose donc d'une *livraison* continue, non d'un *déploiement*
  continu.
- **Pas de tests de bout en bout** en navigateur. Les parcours des trois profils
  sont vérifiés manuellement.
- **Audit de biais de portée limitée** — au plus deux points de variation
  mesurés, imputables à la similarité sémantique qui encode le document entier,
  identité comprise. Négligeable, mais réel : la formule « sans biais » serait
  fausse.

## Documentation

| Document | Contenu |
|---|---|
| [`docs/DEVOPS.md`](docs/DEVOPS.md) | conteneurisation, images, exploitation |
| [`docs/CI_CD.md`](docs/CI_CD.md) | détail des travaux d'intégration |
| [`docs/SCRIPT_DEMONSTRATION.md`](docs/SCRIPT_DEMONSTRATION.md) | déroulé d'une démonstration |
| `docs/Rapport_Avancement_Sprint*.pdf` | rapports d'avancement des quatre sprints |
| [`bi/GUIDE_POWER_BI.md`](bi/GUIDE_POWER_BI.md) | vues décisionnelles |

---

## Contexte

Projet de fin d'année (PFA) réalisé au sein de **BC SKILLS**, juillet–août 2026.

**Aymen Benrbib** — École des Sciences de l'Information (ESI), filière
Ingénierie des Systèmes d'Information et Transformation Digitale.

Développé sur quatre sprints : socle technique et sécurité, interface et
parcours métier, moteur d'analyse et de notation, apprentissage supervisé et
industrialisation.

Code publié à des fins pédagogiques et de démonstration.
