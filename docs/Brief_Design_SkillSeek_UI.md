# Brief Design — SkillSeek AI (Frontend)

Plateforme web de recrutement assistée par IA. Ce document décrit **toutes les pages**, leurs composants et leurs états, pour générer les maquettes dans Claude Design. Le code final sera intégré en Next.js + Tailwind CSS, branché sur une API Flask (JWT).

---

## 1. Direction artistique

- **Thème : sombre, élégant, reposant** (exigence du cahier des charges — audité selon les critères ergonomiques de Bastien & Scapin : guidage clair, concision, gestion explicite des erreurs).
- **Palette suggérée :**
  - Fond principal : `#0B1220` (bleu nuit profond)
  - Surfaces/cartes : `#111A2E`, bordures subtiles `#1E2A44`
  - Accent principal : `#3B82F6` (bleu) — boutons primaires, liens, éléments actifs
  - Accent secondaire : `#22D3EE` (cyan) — graphiques, badges IA
  - Succès `#34D399`, Avertissement `#F59E0B`, Erreur `#F87171`
  - Texte : `#E5EAF3` (primaire), `#8B98B8` (secondaire)
- **Typographie :** Inter (ou similaire), titres semi-bold, corps 14–16px, hiérarchie très lisible.
- **Style :** SaaS moderne. Cartes arrondies (radius 12px), ombres douces, espaces généreux, micro-animations discrètes (hover, transitions 150ms). Pas de surcharge : chaque écran doit rester épuré (critère « concision »).
- **Logo :** "SkillSeek AI" en texte + icône loupe/étincelle, en haut de la sidebar.

## 2. Structure globale

- **Layout connecté :** sidebar fixe à gauche (navigation par rôle, voir §3), header en haut (titre de page, barre de recherche, cloche notifications, avatar + menu profil/déconnexion), contenu au centre.
- **Layout public** (non connecté) : pages centrées, carte sur fond dégradé sombre.
- **Responsive :** desktop d'abord (démo jury), mais sidebar repliable en icônes sur écran étroit.
- **États obligatoires pour chaque écran :** état vide (illustration + phrase + bouton d'action), état chargement (skeletons), état erreur (message clair en français + action de récupération — critère « gestion explicite des erreurs »).
- Langue de l'interface : **français**.

## 3. Navigation par rôle

| Rôle | Entrées sidebar |
|---|---|
| Candidat | Offres d'emploi, Mes candidatures, Mon profil |
| Recruteur | Dashboard, Mes offres, Candidatures, Assistant RH (chatbot), Mon profil |
| Administrateur | Dashboard admin, Utilisateurs, Rôles & permissions, Mon profil |

---

## 4. Pages publiques

### 4.1 Connexion (`/login`)
- Carte centrée : logo, titre « Bon retour », champ email, champ mot de passe (œil afficher/masquer), bouton « Se connecter » pleine largeur, lien « Créer un compte ».
- Erreur : bandeau rouge « Identifiants invalides » sous le titre (pas d'alerte navigateur).
- État chargement du bouton (spinner).

### 4.2 Inscription (`/register`)
- Champs : nom complet, email, mot de passe, confirmation.
- **Indicateur de force du mot de passe** en temps réel (règle : 8+ caractères, majuscule, minuscule, chiffre) avec liste de critères cochés au fur et à mesure (guidage).
- Mention : « En créant un compte, vous consentez à l'analyse automatisée de votre CV par notre IA. » + lien.
- Succès → redirection connexion avec toast « Compte créé ».

---

## 5. Espace Candidat

### 5.1 Liste des offres (`/offers`)
- Grille de cartes offre : titre du poste, extrait de description (2 lignes max), chips des compétences demandées, badge expérience minimale (« 3+ ans »), date de publication, bouton « Voir l'offre ».
- Barre de recherche + filtre par compétence.
- État vide : « Aucune offre disponible pour le moment. »

### 5.2 Détail d'une offre (`/offers/[id]`)
- En-tête : titre, date, chips compétences, critères requis (diplôme minimal, années d'expérience) présentés comme une checklist visuelle.
- Description complète.
- **Zone de candidature :** drag & drop de CV (PDF uniquement, max 5 Mo) avec aperçu du fichier choisi, bouton « Postuler ».
- Si déjà postulé : bandeau « Vous avez postulé le {date} » + statut actuel, bouton désactivé.
- Erreurs upload explicites : « Format non accepté : seuls les PDF sont autorisés », « Fichier trop volumineux (max 5 Mo) ».

### 5.3 Mes candidatures (`/my-applications`)
- Liste de cartes : poste, date de candidature, **stepper horizontal de statut** : Reçue → En cours d'étude → Entretien → Décision (acceptée en vert / non retenue en gris neutre, jamais de rouge agressif).
- Le candidat ne voit PAS son score IA (choix produit).
- État vide : illustration + « Vous n'avez pas encore postulé » + bouton vers les offres.

---

## 6. Espace Recruteur

### 6.1 Dashboard (`/dashboard`) — ÉCRAN VITRINE, le plus soigné
- Rangée de 4 **cartes KPI** : Candidatures reçues, Présélectionnés IA, Entretiens, Recrutés — chacune avec valeur, delta vs mois précédent (petite flèche), mini-sparkline.
- **Entonnoir de recrutement central** (élément signature) : 4 niveaux avec dégradé bleu→cyan, valeur + taux de conversion entre chaque niveau.
- Graphique linéaire « Candidatures sur 30 jours ».
- Tableau « Dernières candidatures » : candidat, poste, date, **badge score /100** (vert ≥ 70, orange 50–69, gris < 50), statut, action « Voir ».
- Sélecteur de période (7j / 30j / 90j) et filtre par offre.

### 6.2 Mes offres (`/offers/manage`)
- Tableau : titre, statut (Ouverte/Fermée en toggle), nb candidatures, score moyen, date, actions (modifier, voir candidatures).
- Bouton « + Nouvelle offre » → **modal ou page de création** : titre, description (éditeur simple), compétences (input à chips), expérience minimale (stepper numérique), diplôme minimal (select), bouton « Publier ».

### 6.3 Candidatures d'une offre (`/offers/[id]/applications`) — ÉCRAN CLÉ IA
- En-tête : rappel de l'offre + stats rapides.
- **Onglets : « Top 10 IA » (défaut) / « Toutes » / « Écartées (<50) »** — traduit la règle RG-01 du cahier des charges.
- Liste classée par score : avatar/initiales, nom, score en **jauge circulaire /100**, chips des compétences correspondantes (vertes) et manquantes (grises), statut, date.
- **Panneau latéral au clic (drawer) — explicabilité :** détail du score (similarité sémantique, entités extraites : compétences, années d'expérience, diplôme), motif exact si écarté par une règle éliminatoire (ex. « Expérience 1 an < 3 ans requis »), bouton « Voir le CV » (viewer PDF), et actions : « Convoquer en entretien », « Accepter », « Ne pas retenir », **« Repêcher »** (pour une candidature écartée — supervision humaine, RG-01.4).
- Chaque changement de statut → toast de confirmation avec « Annuler » (5 s).

### 6.4 Assistant RH — Chatbot (`/assistant`)
- Interface de chat pleine page : historique des conversations dans un volet gauche repliable, zone de messages au centre, input en bas avec bouton envoyer.
- Bulles : questions du recruteur à droite (accent bleu), réponses de l'IA à gauche sur carte sombre avec avatar étincelle.
- Les réponses peuvent contenir des **tableaux** (ex. liste de candidats) et des **mini-graphiques** — prévoir ces deux rendus.
- **Suggestions de questions** au premier lancement (chips cliquables) : « Combien de candidats ont plus de 5 ans d'expérience ? », « Quel est le score moyen sur l'offre Développeur Python ? », « Montre-moi le funnel de ce mois ».
- Indicateur « L'assistant écrit… » (3 points animés).
- Bandeau discret : « Les réponses sont générées par IA à partir de vos données de recrutement. »

---

## 7. Espace Administrateur

### 7.1 Utilisateurs (`/admin/users`)
- Tableau : avatar/initiales, nom, email, badge rôle (couleur par rôle), statut actif (toggle), date de création, actions (modifier, désactiver, supprimer avec modal de confirmation « Cette action est définitive »).
- Bouton « + Nouvel utilisateur » → modal : nom, email, mot de passe, rôle (select).
- Recherche + filtre par rôle.

### 7.2 Rôles & permissions (`/admin/roles`)
- Vue en deux colonnes : liste des rôles à gauche (admin, recruteur, candidat + rôles personnalisés, bouton « + Nouveau rôle »), et à droite la **matrice de permissions** du rôle sélectionné : liste de toggles (Gérer les utilisateurs, Gérer les rôles, Gérer les offres, Voir les candidatures, Gérer les candidatures, Tableau de bord, Assistant RH), chacun avec une description en dessous.
- Bandeau d'information : « Les modifications prennent effet immédiatement pour tous les utilisateurs de ce rôle. » (RG-02)
- Bouton « Enregistrer » avec confirmation toast.

---

## 8. Pages communes

### 8.1 Mon profil (`/profile`)
- Carte identité : avatar (initiales), nom, email, badge rôle, date d'inscription.
- Formulaire : modifier le nom ; changer le mot de passe (ancien, nouveau, confirmation, avec le même indicateur de force qu'à l'inscription).
- Pour le candidat : section « Mon CV » (dernier CV déposé, remplacer).
- Section « Mes données » (RGPD/loi 09-08) : bouton « Télécharger mes données », bouton « Supprimer mon compte » (modal de confirmation stricte).

### 8.2 Divers
- Page 404 : illustration sombre + « Page introuvable » + bouton retour.
- Toasts de notification globaux (succès/erreur) en haut à droite.
- Modal de session expirée : « Votre session a expiré, veuillez vous reconnecter. »

---

## 9. Ordre de génération conseillé dans Claude Design

1. Dashboard recruteur (fixe le style de toute l'app)
2. Candidatures d'une offre + drawer d'explicabilité
3. Assistant RH (chatbot)
4. Login + Inscription
5. Espace candidat (offres, détail + upload, mes candidatures)
6. Admin (utilisateurs, rôles & permissions)
7. Profil + états vides/erreurs
