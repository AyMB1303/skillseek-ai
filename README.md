# SkillSeek AI — Plateforme intelligente de gestion du recrutement

Projet de stage BC SKILLS (Juillet–Août 2026) — Aymen Benrbib, ESI (ISITD).

## Sprint 1 — Contenu livré

| Tâche | Où |
|---|---|
| S1-01 Structure repo | ce dossier (monorepo `backend/`, `frontend/` arrive au Sprint 2) |
| S1-02 Docker | `docker-compose.yml`, `backend/Dockerfile` |
| S1-03 CI/CD | `.github/workflows/ci.yml` |
| S1-04 Modélisation BDD | `backend/app/models/` + migrations Alembic |
| S1-05 Architecture Flask | `backend/app/` (Blueprints auth/users/offers/applications) |
| S1-06 Auth JWT | `backend/app/blueprints/auth.py` (access 15 min + refresh + blacklist) |
| S1-07 RBAC temps réel | `backend/app/middleware/permissions.py` |

## Démarrage rapide

```bash
# 1. Copier la configuration
cp .env.example .env        # (Windows : copy .env.example .env)

# 2. Lancer PostgreSQL + backend
docker compose up --build

# 3. Dans un autre terminal : créer les tables et les données initiales
docker compose exec backend flask db init      # première fois seulement
docker compose exec backend flask db migrate -m "initial schema"
docker compose exec backend flask db upgrade
docker compose exec backend flask seed

# L'API répond sur http://localhost:5000/api/health
```

Compte admin créé par le seed : `admin@skillseek.local` / `Admin@1234` (à changer).

## Tester l'API rapidement

```bash
# Connexion
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@skillseek.local","password":"Admin@1234"}'

# Utiliser le token retourné
curl http://localhost:5000/api/users -H "Authorization: Bearer <ACCESS_TOKEN>"
```

## Lancer les tests et le linting (comme la CI)

```bash
cd backend
pip install -r requirements.txt
flake8 app tests
pytest -v
```

## Architecture

```
skillseek-ai/
├── docker-compose.yml        # PostgreSQL + backend
├── .env.example              # variables d'environnement
├── .github/workflows/ci.yml  # lint + tests à chaque push
└── backend/
    ├── Dockerfile
    ├── requirements.txt
    ├── run.py                # point d'entrée
    ├── config.py             # config par environnement
    ├── app/
    │   ├── __init__.py       # factory create_app()
    │   ├── extensions.py     # db, migrate, jwt, bcrypt, cors
    │   ├── seeds.py          # commande `flask seed`
    │   ├── models/           # User, Role, Permission, JobOffer, Application, AiMetric, TokenBlocklist
    │   ├── blueprints/       # auth, users, offers, applications
    │   └── middleware/
    │       └── permissions.py  # @require_permission — vérif BDD à chaque requête
    └── tests/                # Pytest (auth + révocation temps réel)
```

## Points clés pour la soutenance

- **RBAC temps réel** : le JWT ne contient que l'identité ; les permissions sont relues en base à chaque requête sensible → une révocation par l'admin est effective immédiatement (RG-02 du cahier des charges).
- **Sécurité** : bcrypt pour les mots de passe, tokens 15 min + refresh, blacklist de tokens, SQLAlchemy (anti-injection).
- **CI** : chaque commit déclenche flake8 + Pytest ; un échec bloque le merge.
