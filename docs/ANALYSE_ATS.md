# Sprint 3 — Analyse des CV selon les conventions ATS

## Le pipeline

```
CV déposé (PDF ou DOCX)
   │
   ├─ 1. Extraction        PDF natif → OCR Tesseract si scanné
   │                       DOCX : paragraphes + tableaux
   │
   ├─ 2. Parsing ATS       découpage en sections, puis reconstitution
   │                       d'un profil structuré normalisé
   │
   ├─ 3. Sémantique        proximité CV ↔ offre par plongements lexicaux
   │
   └─ 4. Score             obligatoires / souhaitées + règles + pondération
                           → note /100 entièrement justifiée
```

## Le profil structuré

Le schéma reprend les blocs de **JSON Resume**, format d'échange de fait dans
l'industrie du recrutement :

| Bloc | Contenu extrait |
|---|---|
| `basics` | nom, email, téléphone, LinkedIn |
| `work` | **par poste** : intitulé, entreprise, dates début/fin, durée en mois, en cours |
| `education` | niveau (Bac→Doctorat), établissement, année |
| `certificates` | intitulé, organisme (AWS, Scrum.org…), année |
| `languages` | langue et niveau ramené au **CECRL** (A1 → C2) |
| `skills` | compétences canoniques, langues exclues |
| `totalExperienceYears` | durée cumulée, sans double comptage des postes simultanés |
| `highestDegree` | niveau le plus élevé |

### Détection de sections

Le document est d'abord découpé (EXPÉRIENCE, FORMATION, COMPÉTENCES,
CERTIFICATIONS, LANGUES) à partir d'une liste d'intitulés français et anglais.
Cette étape conditionne la fiabilité du reste : une date lue dans la section
« formation » ne doit pas alimenter le calcul de l'expérience professionnelle.
Un CV sans aucun en-tête reste analysable grâce à un mode de repli.

## Qualification obligatoire / souhaitée

Comme tout ATS, une offre distingue deux niveaux d'exigence :

| Type | Effet |
|---|---|
| **Obligatoire** (`required_skills`) | Absence → candidature écartée, motif tracé |
| **Souhaitée** (`preferred_skills`) | Présence → bonus, jamais bloquante |

## Pondération du score

| Composante | Poids |
|---|---|
| Compétences obligatoires | 35 |
| Compétences souhaitées | 10 |
| Proximité sémantique | 25 |
| Années d'expérience | 20 |
| Niveau de diplôme | 10 |

Le poids d'une composante indisponible est redistribué sur les compétences
obligatoires : le total reste sur 100 et les candidatures demeurent
comparables entre elles.

Les **critères éliminatoires** (expérience, diplôme, compétence obligatoire
absente) plafonnent le score à 45, avec le motif exact conservé et affiché.

## Robustesse

Chaque brique lourde se charge paresseusement et dispose d'un repli :

| Composant absent | Comportement |
|---|---|
| spaCy | Normalisation simple (minuscules, sans accents) |
| Sentence Transformers | Similarité TF-IDF à pondération logarithmique |
| Tesseract | Seuls les documents avec couche texte sont analysés |
| python-docx | Seuls les PDF sont acceptés |
| Échec total | Candidature conservée, « sans score », saisie manuelle possible |

Une candidature n'est **jamais perdue** à cause d'un échec d'analyse.

## Vérification

**55 tests automatisés**, dont 30 pour ce sprint :

*Parsing ATS (16)* — identification des sections, coordonnées, reconstitution
de chaque poste avec entreprise et dates, durée par poste, non-addition des
périodes simultanées, diplômes, certifications avec organisme, niveaux CECRL,
exclusion des langues des compétences techniques, CV sans en-tête, document vide.

*Analyse et score (14)* — variantes d'écriture (JS / JavaScript), absence de
faux positifs sur les sigles courts, priorité de la mention explicite
d'expérience, classement correct d'un profil pertinent face à un hors-sujet,
total des composantes toujours égal à 100, traçage des motifs d'exclusion.

## Résultat sur un CV réel

```
SCORE : 81/100

  Compétences obligatoires          35/35     (python, sql, docker)
  Compétences souhaitées             7/10     (power bi, machine learning ; kubernetes absent)
  Proximité sémantique CV / offre    9/25
  Années d'expérience               20/20
  Niveau de diplôme                 10/10

Profil ATS : 2 postes, 7 ans, Bac+5, 2 langues
```

## Réutilisation au Sprint 4

`semantique.encoder()` produit les vecteurs qui alimenteront la recherche
documentaire du chatbot RAG : la moitié de l'infrastructure du Sprint 4
est déjà en place.
