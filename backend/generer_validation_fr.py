"""Construction du jeu de validation français.

    docker compose exec backend python generer_validation_fr.py

Ce jeu ne sert **jamais** à l'apprentissage. Il remplit deux fonctions
distinctes : vérifier que le modèle appris sur des documents anglais reste
opérant sur des documents français, et mesurer les indicateurs de
présélection annoncés au cahier des charges.

L'étiquette de chaque paire découle de la construction :

  * **Good Fit** — profil du domaine de l'offre, satisfaisant les exigences
    annoncées ;
  * **Potential Fit** — profil du même domaine, mais plus junior : expérience
    ou diplôme en deçà de ce que demande l'annonce. Un recruteur les
    regarderait ; un critère strictement appliqué les écarterait ;
  * **No Fit** — profil d'un autre domaine.

Cette convention est explicite et documentée. Elle ne prétend pas reproduire
un jugement de recruteur, seulement décrire des cas dont l'adéquation ne fait
pas débat.

Les profils « Potential Fit » sont écrits avec des écarts **variés** — un an,
deux ans, un niveau de diplôme, parfois les deux — précisément pour que la
mesure ne soit pas taillée à la mesure des règles qu'elle évalue.
"""
import itertools
import json
from pathlib import Path

DOSSIER = Path("/app/data")

# --------------------------------------------------------------------------
# Offres
# --------------------------------------------------------------------------

OFFRES = {
    "backend": """Développeur Backend Python Senior — Casablanca, CDI

Nous recherchons un développeur backend expérimenté pour concevoir et maintenir
nos interfaces de programmation REST. Vous interviendrez sur l'architecture des
services, la modélisation des données et les traitements à grande échelle.

Profil recherché :
- 5 ans d'expérience minimum en développement backend
- Maîtrise de Python et d'un framework web (Django, Flask ou FastAPI)
- Solide expérience des bases de données relationnelles, notamment PostgreSQL
- Pratique de la conteneurisation avec Docker et de l'intégration continue
- Diplôme Bac+5 en informatique ou équivalent

Compétences appréciées : Kubernetes, architectures distribuées, message brokers.""",

    "frontend": """Développeur Frontend React — Rabat, CDI, télétravail partiel

Au sein de l'équipe produit, vous concevez et réalisez les interfaces de nos
applications web. Vous êtes attentif à l'expérience utilisateur, à
l'accessibilité et aux performances.

Profil recherché :
- 3 ans d'expérience en développement frontend
- Maîtrise de JavaScript, React et des feuilles de style CSS
- Pratique des tests d'interface et de l'intégration continue
- Diplôme Bac+3 minimum

Compétences appréciées : TypeScript, Next.js, conception d'interfaces.""",

    "data": """Data Scientist — Casablanca, CDI

Vous rejoignez notre pôle données pour concevoir des modèles prédictifs et
industrialiser leur mise en production. Vous accompagnez les équipes métier
dans l'interprétation des résultats.

Profil recherché :
- 4 ans d'expérience en science des données
- Maîtrise de Python et des bibliothèques d'apprentissage automatique
- Solide pratique du SQL et de la manipulation de grands volumes
- Diplôme Bac+5, idéalement en statistiques ou en informatique

Compétences appréciées : apprentissage profond, traitement du langage, Power BI.""",

    "comptable": """Comptable Général — Marrakech, CDI

Vous assurez la tenue de la comptabilité générale, les déclarations fiscales et
la préparation des états financiers. Vous êtes l'interlocuteur privilégié du
commissaire aux comptes.

Profil recherché :
- 4 ans d'expérience en comptabilité générale
- Maîtrise des normes comptables marocaines et des déclarations fiscales
- Pratique d'un logiciel de comptabilité et d'Excel à un niveau avancé
- Diplôme Bac+3 minimum en comptabilité, finance ou gestion

Compétences appréciées : logiciel Sage, missions d'audit.""",

    "devops": """Ingénieur DevOps — Casablanca, CDI

Vous industrialisez le déploiement de nos applications et garantissez la
disponibilité des environnements de production.

Profil recherché :
- 4 ans d'expérience en exploitation ou en ingénierie de production
- Maîtrise de Docker, de Kubernetes et des systèmes Linux
- Automatisation des chaînes de livraison continue
- Diplôme Bac+5 en informatique ou équivalent

Compétences appréciées : cloud AWS, supervision, scripts Python.""",

    "java": """Développeur Java Spring — Rabat, CDI

Vous participez à la refonte de nos applications de gestion et à leur
migration vers une architecture de services.

Profil recherché :
- 4 ans d'expérience en développement Java
- Maîtrise du framework Spring et des bases de données relationnelles
- Bonne pratique du SQL et des tests automatisés
- Diplôme Bac+5 en informatique

Compétences appréciées : Docker, méthodes agiles, intégration continue.""",

    "bdd": """Administrateur de Bases de Données — Casablanca, CDI

Vous exploitez, sécurisez et optimisez les bases de données de l'entreprise.

Profil recherché :
- 3 ans d'expérience en administration de bases de données
- Maîtrise de PostgreSQL et d'Oracle
- Solide pratique du SQL et de l'optimisation de requêtes
- Diplôme Bac+3 minimum

Compétences appréciées : systèmes Linux, conteneurisation, supervision.""",

    "controle": """Contrôleur de Gestion — Tanger, CDI

Rattaché à la direction financière, vous produisez les analyses de coûts, le
budget et les tableaux de bord de pilotage.

Profil recherché :
- 4 ans d'expérience en contrôle de gestion
- Maîtrise d'Excel à un niveau avancé et d'un progiciel de gestion
- Pratique du reporting financier et de l'analyse des écarts
- Diplôme Bac+5 en finance, gestion ou école de commerce

Compétences appréciées : Power BI, comptabilité analytique.""",
}


# --------------------------------------------------------------------------
# CV
# --------------------------------------------------------------------------

def _cv(nom, titre, diplome, annee, postes, competences, langues,
        certifs=(), etablissement="Université Mohammed V"):
    lignes = [
        nom.upper(), titre,
        f"{nom.lower().replace(' ', '.')}@example.ma | +212 6 12 34 56 78",
        "", "EXPÉRIENCE PROFESSIONNELLE", "",
    ]
    for debut, fin, poste, entreprise, description in postes:
        lignes += [f"{debut} – {fin}", f"{poste} chez {entreprise}"]
        lignes += [f"  {p.strip()}." for p in description.split(". ") if p.strip()]
        lignes.append("")
    lignes += ["FORMATION", "", f"{annee} - {diplome}, {etablissement}", ""]
    if certifs:
        lignes += ["CERTIFICATIONS", ""] + list(certifs) + [""]
    lignes += ["COMPÉTENCES", "", competences, "", "LANGUES", ""] + langues
    return "\n".join(lignes)


FR_EN = ["Français : bilingue", "Anglais : courant"]
FR = ["Français : courant"]
FR_AR = ["Français : bilingue", "Arabe : langue maternelle"]

# Chaque entree : (domaine, etiquette, cle) -> texte du CV.
# La cle distingue plusieurs profils portant la meme etiquette.
CV = {}


def ajouter(domaine, label, cle, *args, **kwargs):
    CV[(domaine, label, cle)] = _cv(*args, **kwargs)


# ---------------------------------------------------------------- Backend
ajouter(
    "backend", "Good Fit", "a",
    "Youssef Tazi", "Ingénieur logiciel backend", "Master en Génie Logiciel", 2017,
    [("Janvier 2019", "Présent", "Développeur Backend Senior", "OCP Digital",
      "Conception et maintenance d'interfaces de programmation REST avec Flask et "
      "PostgreSQL. Mise en place de pipelines d'intégration continue avec Docker et "
      "GitHub Actions. Encadrement de trois développeurs et revue de code"),
     ("Septembre 2017", "Décembre 2018", "Développeur Python", "Atos Maroc",
      "Développement de traitements de données volumineux avec pandas. Optimisation "
      "de requêtes SQL sur des bases de plusieurs millions d'enregistrements")],
    "Python, SQL, PostgreSQL, Docker, Flask, Django, Git, CI/CD, Kubernetes, Linux",
    FR_EN, ["AWS Certified Developer Associate (2022)"],
)
ajouter(
    "backend", "Good Fit", "b",
    "Anas Kettani", "Développeur backend", "Master en Informatique", 2016,
    [("Mars 2018", "Présent", "Développeur Backend", "Inwi",
      "Développement de services FastAPI adossés à PostgreSQL. Conteneurisation des "
      "applications avec Docker et déploiement automatisé. Écriture de tests unitaires")],
    "Python, FastAPI, PostgreSQL, Docker, SQL, Git, CI/CD, Linux, Tests",
    FR_EN,
)
ajouter(
    "backend", "Potential Fit", "a",
    "Yasmine El Amrani", "Développeuse backend", "Licence en Informatique", 2022,
    [("Mars 2023", "Présent", "Développeuse Python", "Intelcia",
      "Développement de services web avec Django et PostgreSQL. Participation au "
      "déploiement conteneurisé des applications")],
    "Python, SQL, Django, PostgreSQL, Git, Docker",
    ["Français : courant", "Anglais : bon niveau"],
)
ajouter(
    "backend", "Potential Fit", "b",
    "Zakaria Naji", "Développeur Python", "Master en Informatique", 2020,
    [("Septembre 2022", "Présent", "Développeur Backend", "Sopra HR",
      "Développement d'interfaces REST avec Flask. Requêtes et optimisation "
      "PostgreSQL. Déploiement des services avec Docker")],
    "Python, Flask, PostgreSQL, SQL, Docker, Git",
    FR_EN,
)
ajouter(
    "backend", "No Fit", "a",
    "Nadia Bennis", "Chargée de communication", "Licence en Communication", 2021,
    [("Septembre 2021", "Présent", "Chargée de communication", "Agence Créative",
      "Animation des réseaux sociaux et rédaction de contenus éditoriaux. "
      "Organisation d'événements et relations avec la presse")],
    "Rédaction, Réseaux sociaux, Événementiel, Relations presse",
    ["Français : bilingue", "Anglais : intermédiaire"],
)

# --------------------------------------------------------------- Frontend
ajouter(
    "frontend", "Good Fit", "a",
    "Salma Idrissi", "Développeuse frontend", "Master en Systèmes d'Information", 2019,
    [("Février 2020", "Présent", "Développeuse Frontend Senior", "Capgemini Maroc",
      "Conception d'interfaces avec React et Next.js. Travail sur l'accessibilité et "
      "les performances des pages. Mise en place de tests d'interface automatisés")],
    "JavaScript, TypeScript, React, Next.js, CSS, HTML, Tests, Git",
    FR_EN,
)
ajouter(
    "frontend", "Good Fit", "b",
    "Ilyas Mansouri", "Développeur web", "Licence en Informatique", 2020,
    [("Juillet 2021", "Présent", "Développeur Frontend", "Dislog Group",
      "Développement d'applications React et intégration de maquettes. Écriture de "
      "feuilles de style CSS structurées. Tests de composants et revue de code")],
    "JavaScript, React, CSS, HTML, Tests, Git, TypeScript",
    FR,
)
ajouter(
    "frontend", "Potential Fit", "a",
    "Nada Bouzidi", "Intégratrice web", "DUT Informatique", 2023,
    [("Janvier 2024", "Présent", "Intégratrice Web", "Agence Pixel",
      "Intégration de maquettes en HTML et CSS. Premiers développements avec React")],
    "HTML, CSS, JavaScript, React",
    FR,
)
ajouter(
    "frontend", "Potential Fit", "b",
    "Sofia Naciri", "Développeuse junior", "Licence en Informatique", 2024,
    [("Septembre 2024", "Présent", "Développeuse Frontend Junior", "Startup Casa",
      "Développement de composants React et intégration CSS. Participation aux tests "
      "d'interface")],
    "JavaScript, React, CSS, HTML, Git",
    FR,
)
ajouter(
    "frontend", "No Fit", "a",
    "Rachid Alami", "Administrateur de bases de données",
    "Master en Systèmes d'Information", 2015,
    [("Février 2017", "Présent", "Administrateur BDD", "CNSS",
      "Exploitation et optimisation de bases PostgreSQL et Oracle. Sauvegardes, "
      "réplication et sécurisation des accès")],
    "PostgreSQL, Oracle, SQL, Linux, Docker",
    FR_EN,
)

# ------------------------------------------------------------------- Data
ajouter(
    "data", "Good Fit", "a",
    "Reda Alaoui", "Data scientist", "Master en Data Science", 2018,
    [("Janvier 2020", "Présent", "Data Scientist", "Attijariwafa Bank",
      "Conception de modèles de scoring et industrialisation en production. "
      "Traitement automatique du langage appliqué aux réclamations clients. "
      "Tableaux de bord Power BI pour les directions métier"),
     ("Septembre 2018", "Décembre 2019", "Analyste de données", "Deloitte",
      "Analyses statistiques et restitutions décisionnelles")],
    "Python, Machine Learning, SQL, Deep Learning, NLP, Power BI, pandas, scikit-learn",
    FR_EN, ["Microsoft Certified: Azure Data Scientist Associate (2021)"],
)
ajouter(
    "data", "Good Fit", "b",
    "Meryem Chraibi", "Data scientist", "Master en Statistiques Appliquées", 2019,
    [("Octobre 2020", "Présent", "Data Scientist", "Maroc Telecom",
      "Modèles de prédiction du départ des abonnés. Requêtes SQL sur entrepôt de "
      "données volumineux. Restitution des résultats aux directions métier")],
    "Python, Machine Learning, SQL, pandas, Power BI, Deep Learning",
    FR_EN,
)
ajouter(
    "data", "Potential Fit", "a",
    "Ghita Sebti", "Analyste de données", "Master en Statistiques", 2022,
    [("Mars 2023", "Présent", "Analyste Data", "Inwi",
      "Analyses prédictives et modélisation. Requêtes SQL sur entrepôt de données")],
    "Python, SQL, Machine Learning, pandas",
    ["Français : courant", "Anglais : bon niveau"],
)
ajouter(
    "data", "Potential Fit", "b",
    "Imane Cherkaoui", "Analyste décisionnel", "Licence en Mathématiques", 2021,
    [("Novembre 2022", "Présent", "Analyste BI", "Label Vie",
      "Construction de tableaux de bord Power BI. Requêtes SQL et premiers modèles "
      "d'apprentissage automatique en Python")],
    "SQL, Python, Power BI, Machine Learning",
    FR,
)
ajouter(
    "data", "No Fit", "a",
    "Hamza Berrada", "Technicien de maintenance", "Baccalauréat technique", 2019,
    [("Octobre 2019", "Présent", "Technicien de maintenance", "Groupe Industriel",
      "Maintenance préventive et corrective des équipements de production")],
    "Maintenance, Électromécanique, Hydraulique",
    FR,
)

# -------------------------------------------------------------- Comptable
ajouter(
    "comptable", "Good Fit", "a",
    "Khadija Rami", "Comptable générale", "Licence en Comptabilité et Finance", 2018,
    [("Septembre 2019", "Présent", "Comptable Générale", "Marsa Maroc",
      "Tenue de la comptabilité générale et déclarations fiscales mensuelles. "
      "Préparation des états financiers annuels et relation avec le commissaire "
      "aux comptes. Utilisation avancée d'Excel et du logiciel Sage")],
    "Comptabilité, Fiscalité, Excel, Sage, Analyse financière",
    FR_AR,
)
ajouter(
    "comptable", "Good Fit", "b",
    "Hicham Sabri", "Comptable", "Master en Finance et Comptabilité", 2017,
    [("Février 2019", "Présent", "Comptable Général", "Cabinet Fiduciaire Atlas",
      "Écritures comptables et liasse fiscale pour un portefeuille de clients. "
      "Déclarations de TVA et suivi des impôts. Travaux d'audit légal")],
    "Comptabilité générale, Fiscalité, Excel, Sage, Audit",
    FR_AR,
)
ajouter(
    "comptable", "Potential Fit", "a",
    "Omar Fassi", "Assistant comptable", "Licence en Gestion", 2023,
    [("Juillet 2023", "Présent", "Assistant Comptable", "Cabinet Conseil",
      "Saisie des écritures comptables et rapprochements bancaires")],
    "Comptabilité, Excel",
    FR,
)
ajouter(
    "comptable", "Potential Fit", "b",
    "Fatima Zahra Alaoui", "Comptable junior", "Licence en Comptabilité", 2022,
    [("Octobre 2023", "Présent", "Comptable Junior", "PME Distribution",
      "Tenue des écritures comptables courantes et préparation des déclarations "
      "fiscales sous la supervision du chef comptable. Travaux sur Excel et Sage")],
    "Comptabilité générale, Fiscalité, Excel, Sage",
    FR_AR,
)
ajouter(
    "comptable", "No Fit", "a",
    "Mohammed Benjelloun", "Ingénieur DevOps", "Master en Réseaux et Systèmes", 2016,
    [("Janvier 2018", "Présent", "Ingénieur DevOps", "Maroc Telecom",
      "Orchestration Kubernetes et automatisation des déploiements. Migration "
      "d'infrastructures vers le cloud")],
    "Docker, Kubernetes, CI/CD, Linux, AWS, Python",
    FR_EN, ["Certified Kubernetes Administrator (2021)"],
)

# ----------------------------------------------------------------- DevOps
ajouter(
    "devops", "Good Fit", "a",
    "Karim Ouazzani", "Ingénieur DevOps", "Master en Réseaux et Systèmes", 2017,
    [("Mars 2019", "Présent", "Ingénieur DevOps", "OCP Group",
      "Exploitation de clusters Kubernetes en production. Automatisation des "
      "déploiements et des sauvegardes sur Linux. Chaînes de livraison continue et "
      "supervision des environnements")],
    "Docker, Kubernetes, Linux, CI/CD, AWS, Python, Git",
    FR_EN, ["Certified Kubernetes Administrator (2022)"],
)
ajouter(
    "devops", "Good Fit", "b",
    "Yassine Boukhris", "Ingénieur de production", "Master en Informatique", 2016,
    [("Janvier 2019", "Présent", "Ingénieur Production", "Banque Populaire",
      "Conteneurisation des applications avec Docker et orchestration Kubernetes. "
      "Administration de serveurs Linux et automatisation par scripts")],
    "Docker, Kubernetes, Linux, CI/CD, Python, AWS",
    FR_EN,
)
ajouter(
    "devops", "Potential Fit", "a",
    "Amine Rochdi", "Administrateur systèmes", "Licence en Réseaux", 2022,
    [("Septembre 2023", "Présent", "Administrateur Systèmes", "Hôpital Cheikh Zaid",
      "Administration de serveurs Linux et conteneurisation avec Docker. Découverte "
      "de Kubernetes sur les environnements de test")],
    "Linux, Docker, Kubernetes, Git",
    FR,
)
ajouter(
    "devops", "Potential Fit", "b",
    "Soukaina Berrada", "Ingénieure systèmes", "Master en Systèmes et Réseaux", 2021,
    [("Février 2023", "Présent", "Ingénieure Systèmes", "Wafa Assurance",
      "Déploiement conteneurisé avec Docker et Kubernetes. Administration Linux et "
      "automatisation des chaînes de livraison")],
    "Docker, Kubernetes, Linux, CI/CD",
    FR_EN,
)
ajouter(
    "devops", "No Fit", "a",
    "Leila Squalli", "Comptable", "Licence en Comptabilité", 2019,
    [("Mars 2020", "Présent", "Comptable", "Cabinet Comptable Rabat",
      "Tenue de la comptabilité générale et déclarations fiscales")],
    "Comptabilité générale, Fiscalité, Excel, Sage",
    FR_AR,
)

# ------------------------------------------------------------------- Java
ajouter(
    "java", "Good Fit", "a",
    "Mehdi Ouazzani", "Développeur Java", "Master en Génie Logiciel", 2017,
    [("Janvier 2019", "Présent", "Développeur Java Senior", "Sopra Steria Maroc",
      "Développement d'applications Spring Boot adossées à Oracle. Migration vers une "
      "architecture de services. Tests automatisés et intégration continue")],
    "Java, Spring, SQL, Oracle, Docker, Tests, CI/CD, Git, Agile",
    FR_EN,
)
ajouter(
    "java", "Good Fit", "b",
    "Tarik Benslimane", "Ingénieur études et développement",
    "Master en Informatique", 2018,
    [("Septembre 2019", "Présent", "Développeur Java", "CIH Bank",
      "Applications de gestion en Java et Spring. Requêtes SQL complexes sur "
      "PostgreSQL. Écriture de tests unitaires et revue de code")],
    "Java, Spring, SQL, PostgreSQL, Tests, Git, Agile",
    FR_EN,
)
ajouter(
    "java", "Potential Fit", "a",
    "Oussama Idrissi", "Développeur Java junior", "Licence en Informatique", 2022,
    [("Novembre 2023", "Présent", "Développeur Java", "ESI Consulting",
      "Développement de modules Spring et requêtes SQL. Participation aux tests")],
    "Java, Spring, SQL, Git",
    FR,
)
ajouter(
    "java", "Potential Fit", "b",
    "Hind Belkadi", "Développeuse Java", "Master en Informatique", 2023,
    [("Mars 2024", "Présent", "Développeuse Java", "Atos Maroc",
      "Développement d'applications Spring Boot et requêtes SQL. Tests unitaires")],
    "Java, Spring, SQL, Tests, Git",
    FR_EN,
)
ajouter(
    "java", "No Fit", "a",
    "Samira Ouali", "Chargée de recrutement", "Licence en Ressources Humaines", 2020,
    [("Juin 2020", "Présent", "Chargée de recrutement", "Cabinet RH Casablanca",
      "Sourcing de candidats et conduite des entretiens. Suivi des intégrations")],
    "Recrutement, Entretien, Sourcing",
    FR,
)

# -------------------------------------------------------------------- BDD
ajouter(
    "bdd", "Good Fit", "a",
    "Rachid Alami", "Administrateur de bases de données",
    "Master en Systèmes d'Information", 2015,
    [("Février 2017", "Présent", "Administrateur BDD", "CNSS",
      "Exploitation et optimisation de bases PostgreSQL et Oracle. Sauvegardes, "
      "réplication et sécurisation des accès. Optimisation de requêtes SQL sur des "
      "volumes importants")],
    "PostgreSQL, Oracle, SQL, Linux, Docker",
    FR_EN,
)
ajouter(
    "bdd", "Good Fit", "b",
    "Nabil Chraibi", "Administrateur de données", "Licence en Informatique", 2018,
    [("Mai 2019", "Présent", "Administrateur BDD", "Royal Air Maroc",
      "Administration PostgreSQL et Oracle en production. Optimisation des requêtes "
      "SQL et supervision des performances. Sauvegardes et plans de reprise")],
    "PostgreSQL, Oracle, SQL, Linux",
    FR_AR,
)
ajouter(
    "bdd", "Potential Fit", "a",
    "Youssra Lahlou", "Technicienne base de données", "DUT Informatique", 2023,
    [("Février 2024", "Présent", "Technicienne BDD", "Groupe Ynna",
      "Exploitation de bases PostgreSQL et écriture de requêtes SQL. Découverte "
      "d'Oracle sur les environnements de test")],
    "PostgreSQL, SQL, Oracle, Linux",
    FR,
)
ajouter(
    "bdd", "Potential Fit", "b",
    "Adil Mernissi", "Développeur base de données", "Licence en Informatique", 2023,
    [("Septembre 2024", "Présent", "Développeur BDD", "Cabinet Data Conseil",
      "Écriture de requêtes SQL et procédures stockées PostgreSQL. Premiers travaux "
      "d'administration Oracle")],
    "SQL, PostgreSQL, Oracle",
    FR,
)
ajouter(
    "bdd", "No Fit", "a",
    "Meriem Tahiri", "Graphiste", "Licence en Arts Graphiques", 2021,
    [("Octobre 2021", "Présent", "Graphiste", "Studio Créatif",
      "Création d'identités visuelles et de supports de communication")],
    "Illustration, Identité visuelle, Mise en page",
    FR,
)

# ---------------------------------------------------- Contrôle de gestion
ajouter(
    "controle", "Good Fit", "a",
    "Sanaa Bennani", "Contrôleuse de gestion", "Master en Finance d'Entreprise", 2017,
    [("Janvier 2019", "Présent", "Contrôleuse de Gestion", "Managem",
      "Élaboration du budget annuel et analyse des écarts. Production des tableaux "
      "de bord de pilotage sous Power BI et Excel. Exploitation du progiciel SAP")],
    "Contrôle de gestion, Excel, ERP, Power BI, Analyse des coûts, Reporting financier",
    FR_EN,
)
ajouter(
    "controle", "Good Fit", "b",
    "Driss Lamrani", "Contrôleur de gestion", "Master en Gestion", 2016,
    [("Mars 2018", "Présent", "Contrôleur de Gestion", "Cosumar",
      "Reporting financier mensuel et contrôle budgétaire. Analyse des coûts de "
      "production. Utilisation avancée d'Excel et du progiciel de gestion")],
    "Contrôle de gestion, Excel, ERP, Reporting financier, Comptabilité générale",
    FR_AR,
)
ajouter(
    "controle", "Potential Fit", "a",
    "Kenza Filali", "Analyste de gestion", "Master en Contrôle de Gestion", 2023,
    [("Septembre 2023", "Présent", "Analyste de Gestion", "Groupe Akwa",
      "Suivi budgétaire et production de tableaux de bord sous Excel. Utilisation "
      "du progiciel de gestion pour les extractions")],
    "Contrôle de gestion, Excel, ERP",
    FR_EN,
)
ajouter(
    "controle", "Potential Fit", "b",
    "Younes Skalli", "Assistant contrôle de gestion", "Licence en Gestion", 2022,
    [("Janvier 2023", "Présent", "Assistant Contrôle de Gestion", "Lesieur Cristal",
      "Contribution au reporting financier mensuel et au contrôle budgétaire. "
      "Travaux d'analyse des coûts sur Excel et extractions du progiciel")],
    "Contrôle de gestion, Excel, ERP, Reporting financier",
    FR,
)
ajouter(
    "controle", "No Fit", "a",
    "Walid Fadili", "Développeur frontend", "Licence en Informatique", 2021,
    [("Octobre 2021", "Présent", "Développeur Frontend", "Agence Web Rabat",
      "Développement d'interfaces React et intégration CSS")],
    "JavaScript, React, CSS, HTML, Git",
    FR,
)


# --------------------------------------------------------------------------

# Nombre d'offres etrangeres confrontees a chaque profil de reference. Toutes
# les permutations seraient possibles, mais elles gonfleraient la classe
# negative au point de rendre la mesure peu lisible.
CROISEMENTS_PAR_DOMAINE = 3


def main():
    cas = []

    # Paires construites : chaque CV face a l'offre de son domaine
    for (domaine, label, cle), texte_cv in CV.items():
        cas.append({
            "cv": texte_cv,
            "offre": OFFRES[domaine],
            "label": label,
            "domaine": domaine,
            "profil": cle,
            "origine": "paire construite",
        })

    # Paires croisees : un CV face a une offre d'un autre domaine est, par
    # construction, inadapte. Elles etoffent la classe « No Fit » sans
    # introduire d'ambiguite.
    autres = {d: [] for d in OFFRES}
    for a, b in itertools.permutations(OFFRES, 2):
        autres[a].append(b)

    for domaine_cv, domaines_offres in autres.items():
        texte_cv = CV.get((domaine_cv, "Good Fit", "a"))
        if not texte_cv:
            continue
        for domaine_offre in domaines_offres[:CROISEMENTS_PAR_DOMAINE]:
            cas.append({
                "cv": texte_cv,
                "offre": OFFRES[domaine_offre],
                "label": "No Fit",
                "domaine": f"{domaine_cv} vs {domaine_offre}",
                "profil": "a",
                "origine": "croisement de domaines",
            })

    DOSSIER.mkdir(parents=True, exist_ok=True)
    chemin = DOSSIER / "validation_francais.json"
    chemin.write_text(
        json.dumps(cas, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    positifs = sum(1 for c in cas if c["label"] != "No Fit")
    print(f"{len(cas)} appariements écrits dans {chemin}")
    print(f"  Domaines            : {len(OFFRES)}")
    print(f"  Curriculum vitæ     : {len(CV)}")
    print(f"  Profils à retenir   : {positifs}")
    print(f"  Profils à écarter   : {len(cas) - positifs}")
    for label in ("Good Fit", "Potential Fit", "No Fit"):
        print(f"    {label:16}: {sum(1 for c in cas if c['label'] == label)}")


if __name__ == "__main__":
    main()
