# Assistant conversationnel RAG

## Architecture

```
Question du recruteur
   │
   ├─ 1. Récupération      index vectoriel → documents les plus proches
   │                       (offres, candidatures, aide en ligne)
   │
   ├─ 2. Faits chiffrés    requêtes SQL → volumes, moyennes, taux
   │                       (le modèle ne compte jamais lui-même)
   │
   ├─ 3. Génération        fournisseur disponible → réponse rédigée
   │
   └─ 4. Restitution       texte + tableau + lien + sources citées
```

## Les trois couches

| Module | Rôle |
|---|---|
| `rag/connaissance.py` | Transforme offres, candidatures et aide en documents autonomes |
| `rag/index.py` | Encode en vecteurs, recherche par similarité, invalidation automatique |
| `rag/generation.py` | Formule la réponse via le fournisseur disponible |
| `rag/assistant.py` | Orchestration + faits chiffrés + tableaux |

## Fournisseurs de génération

Essayés dans cet ordre, le premier opérationnel est retenu :

| Fournisseur | Activation | Caractéristiques |
|---|---|---|
| **Ollama** | Détecté automatiquement si le service tourne | Modèle local, aucune donnée ne sort, aucune clé |
| **API distante** | Si `LLM_API_KEY` est défini | Compatible interface OpenAI (Groq, Together…) |
| **Gabarits** | Toujours disponible | Aucune dépendance, réponses exactes mais non rédigées |

### Activer le modèle local (recommandé)

```bash
# Sur votre machine, hors conteneur
winget install Ollama.Ollama      # ou https://ollama.com/download
ollama pull qwen2.5:3b            # ~2 Go, fonctionne sur processeur
ollama serve
```

Le backend le détecte automatiquement via `host.docker.internal:11434`.
Variables ajustables : `OLLAMA_URL`, `OLLAMA_MODEL`.

### Activer un service distant

```bash
# Dans .env
LLM_API_KEY=votre_cle
LLM_API_URL=https://api.groq.com/openai/v1   # défaut
LLM_MODEL=llama-3.1-8b-instant               # défaut
```

## Pourquoi les chiffres ne viennent pas du modèle

Un modèle de langue reformule bien mais compte mal. Lui demander « combien de
candidatures dépassent le seuil » reviendrait à espérer qu'il additionne
correctement des dizaines de documents.

Les grandeurs sont donc calculées par requêtes SQL et injectées dans le contexte
comme des faits établis. Le générateur ne fait que les mettre en forme. Les
tableaux joints aux réponses proviennent également des données, jamais du texte
généré : ils font foi.

## Cloisonnement

Un recruteur n'interroge que ses propres offres et les candidatures associées ;
un administrateur dispose d'une vue d'ensemble. Le filtrage est appliqué à la
construction de l'index, pas après coup.

## Sources citées

Chaque réponse indique les documents consultés avec leur score de pertinence,
et un lien vers l'écran concerné. L'utilisateur peut donc vérifier l'origine de
ce qui lui est affirmé.

## Points d'accès

| Méthode | Chemin | Permission |
|---|---|---|
| POST | `/api/assistant/ask` | `use_chatbot` |
| GET | `/api/assistant/status` | `use_chatbot` |

## Vérification

15 tests couvrent : autonomie des documents, présence des motifs d'écartement,
pertinence de la recherche, reconstruction de l'index après modification,
exactitude des grandeurs chiffrées, cohérence des tableaux, citation des sources,
disponibilité permanente d'un fournisseur, et contrôle des permissions.
