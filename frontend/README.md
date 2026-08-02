# Frontend SkillSeek AI — Next.js

Interface web de la plateforme, connectée à l'API Flask.

## Démarrage

```bash
cd frontend
npm install
npm run dev          # http://localhost:3000
```

Le backend doit tourner en parallèle (`docker compose up` à la racine).
L'URL de l'API se règle via `NEXT_PUBLIC_API_URL` (défaut : `http://localhost:5000/api`).

## Écrans livrés (Sprint 2 — complet)

| Route | Rôle | Contenu |
|---|---|---|
| `/connexion` | public | Connexion, erreurs explicites, afficher/masquer le mot de passe |
| `/inscription` | public | Validation en direct, indicateur de force, consentement |
| `/dashboard` | recruteur | 4 KPI + entonnoir + courbe, **calculés par l'API** |
| `/candidatures` | recruteur | Onglets RG-01, tri, drawer d'explicabilité, actions de statut |
| `/offres/gestion` | recruteur | Liste, création réelle d'offre, ouverture/fermeture |
| `/assistant` | recruteur | Assistant interrogeant les vraies données, réponses avec tableaux |
| `/offres` | tous | Liste des offres, recherche et filtre par compétence |
| `/offres/[id]` | tous | Détail, critères, dépôt de CV (glisser-déposer, PDF ≤ 5 Mo) |
| `/mes-candidatures` | candidat | Suivi par stepper, sans score affiché |
| `/admin/utilisateurs` | admin | CRUD, changement de rôle, activation, suppression confirmée |
| `/admin/roles` | admin | Matrice de permissions, effet immédiat (RG-02) |
| `/profil` | tous | Identité, mot de passe, export et suppression des données |
| `/recherche` | tous | Recherche globale (⌘K), résultats groupés |
| `/404` | — | Page introuvable |

## Principes d'implémentation

- **Aucun élément décoratif** : chaque bouton déclenche une action réelle sur l'API.
- **Données calculées** : KPI, entonnoir et scores viennent de la base, jamais de valeurs écrites en dur.
- **Mise à jour optimiste** : les changements s'affichent immédiatement, avec « Annuler » pendant 5 s.
- **Accessibilité** : focus visible, cibles ≥ 40 px, libellés ARIA, navigation clavier (⌘K, Échap).
- **États systématiques** : chargement (skeletons), vide (avec action), erreur (avec bouton réessayer).

## Structure

```
src/
├── lib/
│   ├── api.js        # client HTTP, JWT, refresh automatique
│   ├── auth.js       # contexte d'authentification, garde de route par rôle
│   ├── scoring.js    # règle RG-01 et couleurs de score (miroir du serveur)
│   └── assistant.js  # moteur de réponses calculées sur les données réelles
├── components/
│   ├── Layout.jsx    # sidebar par rôle, header, notifications, menu profil
│   └── ui.jsx        # toasts, modale, drawer, états, badges
└── pages/            # une route = un fichier
```

## Note sur l'assistant RH

La version actuelle calcule ses réponses directement sur les données chargées depuis l'API
(volumes, scores moyens, entonnoir, meilleurs profils, candidatures en attente, comparaison d'offres).
Le Sprint 4 remplacera ce moteur par un LLM via LangChain en conservant la même interface
(`repondre(question, donnees)`), ce qui rendra la substitution transparente pour l'interface.
