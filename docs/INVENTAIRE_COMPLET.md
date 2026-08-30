# Inventaire complet du travail réalisé

Établi le 30 août 2026 en parcourant le dépôt : routes, services, écrans,
tests, migrations, chaînes d'automatisation et livrables annexes. Ce document
sert à repérer ce que le rapport ne dit pas encore.

La colonne **Rapport** indique l'état de couverture :
**décrit** · **effleuré** · **absent**.

---

## 1. Ce que la plateforme fait, module par module

### 1.1 Authentification et gestion des comptes — `auth.py`, `users.py` (19 routes)

| Fonction | Détail | Rapport |
|---|---|---|
| Inscription et connexion | Jeton d'accès 15 min, jeton de renouvellement 7 jours | décrit |
| Liste de révocation de jetons | Table `token_blocklist` : invalider un jeton avant son expiration | effleuré |
| Verrou de compte | Après N échecs consécutifs, refus temporaire, titulaire prévenu. Le verrou porte sur le compte, pas sur l'adresse réseau | décrit |
| Validation des recruteurs | Un compte recruteur reste en attente jusqu'à approbation | décrit |
| **Qualification des demandes** | `qualification_recruteur.py` — faisceau d'indices présenté à l'administrateur : cohérence du domaine de courriel, de l'entreprise déclarée. Il **qualifie**, il ne décide pas | **absent** |
| Corbeille et restauration | Suppression logique, restauration, purge protégée | **absent** |
| Rôles et permissions | Matrice modifiable, effet immédiat (RG-02) | décrit |

### 1.2 Offres — `offers.py` (10 routes)

| Fonction | Détail | Rapport |
|---|---|---|
| Publication et modification | Compétences obligatoires et souhaitées, expérience, diplôme, contrat, télétravail, fourchette salariale | décrit |
| Recherche et filtre | Par intitulé, description, compétence | effleuré |
| Corbeille d'offres | Suppression logique, restauration | **absent** |

### 1.3 Candidatures et analyse — `applications.py` (6 routes)

| Fonction | Détail | Rapport |
|---|---|---|
| Dépôt de CV | PDF natif ou image | décrit |
| Lecture du document | `extraction.py`, `ats.py` — rubriques, coordonnées, périodes, diplômes, langues, certifications | décrit |
| OCR | Documents numérisés sans couche de texte | décrit |
| **Référentiel de compétences** | `competences.py` — forme canonique et variantes d'écriture rencontrées dans les CV | **absent** |
| Notation | `scoring.py` — cinq composantes, seuil 50, top 10 | décrit |
| Similarité sémantique | `semantique.py` — comparaison profil / offre au-delà des mots | décrit |
| Ajustement appris | `ml/` — borné à ±8 points | décrit |
| **Traçabilité de l'analyse** | `observabilite.py` — chronométrage et méthode d'extraction conservés avec chaque analyse | **absent** |
| **Empreinte du CV** | `cv_empreinte` — détecte le redépôt d'un document identique | **absent** |
| Ré-analyse | Avec message explicite si le document a disparu du disque | effleuré |

### 1.4 Détection d'anomalies — `fraude.py`, `signalements.py` (6 routes, 17 tests)

**Fonction entière absente du rapport.**

| Indice recherché | Détail |
|---|---|
| Uniformité des phrases | Un écart-type de longueur anormalement faible |
| Absence de résultat chiffré | Aucun pourcentage, montant, volume dans un texte long |
| Producteur du fichier | Métadonnées du PDF révélant un outil automatisé |
| Incohérences de dates | Périodes qui se chevauchent ou remontent trop loin |

Chaque indice produit un **signalement** doté d'une sévérité, d'une origine et
d'un statut. Le recruteur l'examine et le tranche — le système ne rejette
rien de lui-même. La table `signalements` conserve qui a signalé, qui a
examiné et quand.

### 1.5 Orientation du candidat — `orientation.py` (10 tests)

**Absent du rapport.** Le moteur de score sert d'abord à répondre à « ce
candidat correspond-il à cette offre ? ». Retourné, il répond à « quelles
offres correspondent à ce candidat ? » — et permet de recommander des offres
**avant toute candidature**, à partir du profil déclaré.

La note n'est jamais affichée : elle ordonne, elle ne se montre pas.

### 1.6 Retour au candidat — `retour_candidat.py`

**Absent du rapport.** Produit un retour factuel : compétences attendues et
non trouvées, sans jamais communiquer de note ni de rang. C'est la
contrepartie concrète du principe d'explicabilité côté candidat.

### 1.7 Évaluation après entretien — `evaluations.py` (4 routes)

| Fonction | Détail | Rapport |
|---|---|---|
| Saisie du verdict | Notes par critère, verdict, commentaire | décrit |
| Conservation du score système | `score_systeme` figé au moment de l'évaluation | effleuré |
| **Boucle d'apprentissage** | Ces évaluations alimentent le modèle d'ajustement | effleuré |

### 1.8 Analyse décisionnelle — `dashboard.py` (3 routes), écran `analyse.jsx` (8 tests)

**Effleuré.** Écran qui confronte la note calculée **avant** l'entretien au
verdict porté **après**. C'est la mesure de la qualité du classement
lui-même : le système se juge sur ses propres prédictions.

### 1.9 Assistant de recherche documentaire — `assistant.py` (2 routes, 31 tests)

| Fonction | Détail | Rapport |
|---|---|---|
| Deux domaines disjoints | Recrutement et administration, jamais croisés | décrit |
| Restriction au périmètre | Un recruteur n'interroge que ses propres dossiers | décrit |
| Modèle local, repli déterministe | Utilisable sans dépendance extérieure | décrit |
| **Mesure de performance** | 5 tests dédiés au temps de réponse | **absent** |

### 1.10 Notifications et journal — `notifications.py` (3 routes), `journal.py` (1 route)

| Fonction | Détail | Rapport |
|---|---|---|
| Notifications | Nouvelle candidature, changement de statut, compte validé | effleuré |
| Journal d'audit immuable | Auteur, action, objet, détail, horodatage | décrit |

### 1.11 Profil professionnel — `profile.py` (7 routes)

Profil déclaré par le candidat, servant à l'orientation. Dès qu'une
candidature est analysée, le profil **observé** issu du CV prend le relais :
l'observé l'emporte toujours sur le déclaré. **Effleuré.**

---

## 2. L'interface — 22 écrans

| Écran | Rapport |
|---|---|
| `connexion`, `inscription`, `index`, `404` | décrit |
| `offres/index`, `offres/[id]`, `offres/gestion` | décrit |
| `mes-candidatures`, `candidatures` | décrit |
| `mon-profil-pro`, `profil` | effleuré |
| `dashboard` | décrit |
| `analyse` — analyse décisionnelle | **absent** |
| `pipeline` — suivi du flux de candidatures | **absent** |
| `recherche` — recherche transverse | **absent** |
| `signalements` | **absent** |
| `assistant` | décrit |
| `admin/index`, `admin/utilisateurs`, `admin/roles` | décrit |
| `admin/recruteurs` | décrit |
| `admin/journal` | effleuré |
| `admin/corbeille` | **absent** |

### Composants transverses

| Composant | Rapport |
|---|---|
| `SaisieCompetences` — saisie avec suggestions du référentiel | effleuré |
| `VisiteGuidee` — visite guidée de l'interface | **absent** |
| `BasculeTheme` — thème clair et sombre | **absent** |
| `Layout`, `ui` — briques partagées | effleuré |

---

## 3. Les tests — 194, répartis par domaine

| Fichier | Tests | Ce qu'il verrouille | Rapport |
|---|---|---|---|
| `test_fraude.py` | 17 | Détection d'anomalies | **absent** |
| `test_ats.py` | 16 | Lecture des documents | décrit |
| `test_assistant_rag.py` | 15 | Assistant, périmètre | décrit |
| `test_scoring.py` | 14 | Moteur de notation | décrit |
| `test_analyse.py` | 14 | Chaîne d'analyse complète | décrit |
| `test_validation_corbeille.py` | 14 | Corbeille, restauration, purge | **absent** |
| `test_qualification_recruteur.py` | 12 | Faisceau d'indices | **absent** |
| `test_cloisonnement.py` | 11 | **Écrits du point de vue de l'attaquant** | décrit |
| `test_assistant_administration.py` | 11 | Étanchéité des deux domaines | effleuré |
| `test_orientation.py` | 10 | Recommandation d'offres | **absent** |
| `test_observabilite.py` | 9 | Traçabilité du traitement | **absent** |
| `test_analyse_decisionnelle.py` | 8 | Écran d'analyse | **absent** |
| `test_auth.py` | 6 | Authentification | décrit |
| `test_notifications.py` | 5 | Notifications | effleuré |
| `test_prediction_modele.py` | 5 | Modèle d'ajustement | décrit |
| `test_offers.py` | 5 | Offres | décrit |
| `test_verrou_connexion.py` | 5 | Verrou de compte | décrit |
| `test_assistant_performance.py` | 5 | Temps de réponse | **absent** |
| `test_document_manquant.py` | 4 | Document absent du disque | effleuré |
| `test_permissions.py` | 3 | Permissions en temps réel | décrit |

---

## 4. L'industrialisation

| Élément | Détail | Rapport |
|---|---|---|
| Conteneurisation | 3 fichiers de composition : base, surcouche de développement, production | décrit |
| Surcouche de développement | Rechargement à chaud, `docker compose up -d` suffit | décrit |
| Image du service | Multi-étapes, compte sans privilèges, sonde de vivacité | décrit |
| Migrations | 11 migrations Alembic, chaîne linéaire | décrit |
| Jeu de démonstration | Commande `flask demo --reset`, régénérable, auto-réparant | effleuré |
| Chaîne d'intégration | 7 travaux | décrit |
| CodeQL | Suivi du flux de données, + hebdomadaire | décrit |
| SonarCloud | Couverture, duplication, fiabilité, sûreté — trois notes A | décrit |
| Déploiement | Étiquette de version → groupe de conteneurs → contrôle externe | décrit |
| **Codespaces** | Environnement complet dans le navigateur, sans installation | **absent** |
| Dependabot | Montées de version surveillées | **absent** |

---

## 5. Les livrables annexes

| Livrable | Détail | Rapport |
|---|---|---|
| **Décisionnel Power BI** | `bi/` — classeur `.pbix`, vues SQL dédiées, thème graphique, guide d'utilisation | **absent** |
| Exports | `generateur_pdf.py` — production de documents | **absent** |
| 4 rapports d'avancement | Un par itération | effleuré |
| Documentation technique | 6 documents : lecture des CV, assistant, CI/CD, DevOps, déploiement, script de démonstration | effleuré |
| README | Refondu, avec badges d'état | non applicable |

---

## 6. Ce qui manque au rapport — par ordre d'importance

1. **La détection d'anomalies et les signalements.** Un module complet,
   17 tests, 6 routes, une table. C'est la fonction la plus originale du
   projet après l'explicabilité, et elle n'apparaît nulle part.
2. **Le décisionnel Power BI.** Un livrable entier, avec classeur, vues SQL et
   guide. Absent.
3. **L'orientation du candidat et le retour factuel.** La réciproque du moteur
   de notation, et la contrepartie du principe d'explicabilité côté candidat.
4. **La qualification des demandes de compte recruteur.** 12 tests pour un
   module qui illustre bien la posture du projet : qualifier sans décider.
5. **La corbeille et la restauration.** 14 tests. C'est la réversibilité, un
   thème directement lié à la gouvernance de l'information.
6. **L'analyse décisionnelle.** Le système qui se juge sur ses propres
   prédictions — un argument fort à l'oral.
7. **L'observabilité et l'empreinte du CV.**
8. **Quatre écrans** : analyse, pipeline, recherche, signalements.
9. **Codespaces, visite guidée, thème clair et sombre.**

---

## 7. Suggestion de réorganisation

Le chapitre « Réalisation » ne présente aujourd'hui que la chaîne principale :
lecture du CV, notation, cloisonnement, assistant. Trois sections le
compléteraient sans le déséquilibrer :

- **Contrôler la sincérité des dossiers** — détection d'anomalies et
  signalements ;
- **Servir le candidat, pas seulement le recruteur** — orientation, retour
  factuel, compétences manquantes ;
- **Garder la main sur les données** — corbeille, journal, observabilité,
  qualification des demandes.

Et un chapitre court sur le **décisionnel**, entre la réalisation et
l'industrialisation.
