"""Profils, offres et CV du jeu de démonstration.

Les données sont réalistes et cohérentes entre elles : chaque CV correspond
au profil qu'il décrit, ce qui permet de vérifier que le moteur d'analyse
attribue bien les scores attendus.
"""

# --------------------------------------------------------------------------
# Recruteurs
# --------------------------------------------------------------------------

RECRUTEURS = [
    {
        "full_name": "Sarah Lamrani",
        "email": "s.lamrani@bcskills.ma",
        "company": "BC Skills",
        "phone": "+212 522 45 67 89",
        "status": "active",
    },
    {
        "full_name": "Mehdi Bennani",
        "email": "m.bennani@technova.ma",
        "company": "TechNova",
        "phone": "+212 537 12 34 56",
        "status": "active",
    },
    # Compte laisse en attente : illustre l'ecran de validation
    {
        "full_name": "Imane Cherkaoui",
        "email": "i.cherkaoui@digitalfactory.ma",
        "company": "Digital Factory",
        "phone": "+212 661 78 90 12",
        "status": "pending",
    },
]


# --------------------------------------------------------------------------
# Offres d'emploi
# --------------------------------------------------------------------------

OFFRES = [
    {
        "title": "Développeur Python Senior",
        "description": (
            "Nous recherchons un développeur backend expérimenté pour concevoir et "
            "maintenir nos interfaces de programmation REST. Vous interviendrez sur "
            "l'architecture des services, la modélisation des données et les traitements "
            "de données à grande échelle. L'environnement est entièrement conteneurisé "
            "et s'appuie sur une chaîne d'intégration continue."
        ),
        "required_skills": ["python", "sql", "docker"],
        "preferred_skills": ["kubernetes", "machine learning", "ci/cd"],
        "min_experience_years": 3,
        "min_degree": "Bac+3",
        "location": "Casablanca",
        "contract_type": "CDI",
        "remote_policy": "Hybride",
        "salary_min": 18000,
        "salary_max": 26000,
    },
    {
        "title": "Développeur Frontend React",
        "description": (
            "Au sein de l'équipe produit, vous concevez les interfaces de nos "
            "applications web. Vous êtes attentif à l'expérience utilisateur, à "
            "l'accessibilité et à la performance des pages livrées."
        ),
        "required_skills": ["javascript", "react", "css"],
        "preferred_skills": ["typescript", "next.js", "tests"],
        "min_experience_years": 2,
        "min_degree": "Bac+3",
        "location": "Rabat",
        "contract_type": "CDI",
        "remote_policy": "Télétravail",
        "salary_min": 14000,
        "salary_max": 20000,
    },
    {
        "title": "Data Scientist",
        "description": (
            "Vous rejoignez notre pôle données pour concevoir des modèles prédictifs "
            "et industrialiser leur mise en production. Vous accompagnez les équipes "
            "métier dans l'interprétation des résultats et la définition des indicateurs."
        ),
        "required_skills": ["python", "machine learning", "sql"],
        "preferred_skills": ["deep learning", "nlp", "power bi"],
        "min_experience_years": 3,
        "min_degree": "Bac+5",
        "location": "Casablanca",
        "contract_type": "CDI",
        "remote_policy": "Sur site",
        "salary_min": 20000,
        "salary_max": 30000,
    },
    {
        "title": "Ingénieur DevOps",
        "description": (
            "Vous prenez en charge l'automatisation des déploiements, la supervision "
            "des environnements et la fiabilité de nos plateformes. Vous accompagnez "
            "les équipes de développement dans l'adoption des bonnes pratiques."
        ),
        "required_skills": ["docker", "kubernetes", "ci/cd", "linux"],
        "preferred_skills": ["aws", "python"],
        "min_experience_years": 4,
        "min_degree": "Bac+5",
        "location": "Casablanca",
        "contract_type": "CDI",
        "remote_policy": "Hybride",
        "salary_min": 22000,
        "salary_max": 32000,
    },
    {
        "title": "Développeur Full Stack — Stage",
        "description": (
            "Stage de fin d'études au sein de l'équipe technique. Vous participez au "
            "développement de nouvelles fonctionnalités, côté interface comme côté "
            "serveur, et êtes accompagné par un développeur confirmé."
        ),
        "required_skills": ["javascript", "python"],
        "preferred_skills": ["react", "flask", "git"],
        "min_experience_years": 0,
        "min_degree": "Bac+3",
        "location": "Rabat",
        "contract_type": "Stage",
        "remote_policy": "Sur site",
        "salary_min": 4000,
        "salary_max": 6000,
    },
    {
        "title": "Administrateur Base de Données",
        "description": (
            "Vous assurez l'exploitation, la sauvegarde et l'optimisation de nos bases "
            "de données. Vous intervenez sur les performances des requêtes et la "
            "sécurisation des accès."
        ),
        "required_skills": ["postgresql", "sql", "linux"],
        "preferred_skills": ["oracle", "docker"],
        "min_experience_years": 3,
        "min_degree": "Bac+3",
        "location": "Marrakech",
        "contract_type": "CDD",
        "remote_policy": "Sur site",
        "salary_min": 15000,
        "salary_max": 22000,
    },
]


# --------------------------------------------------------------------------
# Candidats
#
# `offre` designe l'intitule vise ; `qualite` indique le resultat attendu de
# l'analyse, ce qui permet de verifier la coherence du moteur de score.
# --------------------------------------------------------------------------

CANDIDATS = [
    # --- Développeur Python Senior ---
    {
        "full_name": "Youssef Tazi", "email": "y.tazi@example.ma",
        "offre": "Développeur Python Senior", "qualite": "excellent",
        "titre": "Ingénieur logiciel backend",
        "diplome": "Master en Génie Logiciel", "niveau": "Bac+5", "annee_diplome": 2018,
        "postes": [
            ("Janvier 2021", "Présent", "Développeur Backend Senior", "OCP Digital",
             "Conception d'API REST avec Flask et PostgreSQL. Mise en place de pipelines "
             "CI/CD avec Docker et GitHub Actions. Encadrement de trois développeurs."),
            ("Septembre 2018", "Décembre 2020", "Développeur Python", "Atos Maroc",
             "Développement de traitements de données avec pandas. Optimisation de requêtes SQL."),
        ],
        "competences": ("Python, SQL, Docker, Flask, PostgreSQL, Git, CI/CD, "
                        "Kubernetes, Machine Learning"),
        "certifications": ["AWS Certified Developer Associate (2023)"],
        "langues": [
            ("Français", "bilingue"), ("Anglais", "courant"),
            ("Arabe", "langue maternelle"),
        ],
    },
    {
        "full_name": "Yasmine El Amrani", "email": "y.elamrani@example.ma",
        "offre": "Développeur Python Senior", "qualite": "bon",
        "titre": "Développeuse backend",
        "diplome": "Licence en Informatique", "niveau": "Bac+3", "annee_diplome": 2019,
        "postes": [
            ("Mars 2020", "Présent", "Développeuse Python", "Intelcia",
             "Développement de services web avec Django et PostgreSQL. Déploiement Docker."),
        ],
        "competences": "Python, SQL, Docker, Django, PostgreSQL, Git",
        "certifications": [],
        "langues": [("Français", "courant"), ("Anglais", "bon niveau")],
    },
    {
        "full_name": "Karim Ouazzani", "email": "k.ouazzani@example.ma",
        "offre": "Développeur Python Senior", "qualite": "moyen",
        "titre": "Développeur web",
        "diplome": "Licence en Informatique", "niveau": "Bac+3", "annee_diplome": 2021,
        "postes": [
            ("Juin 2021", "Présent", "Développeur Web", "Webhelp",
             "Développement d'applications web avec PHP et MySQL. Notions de Python."),
        ],
        "competences": "PHP, MySQL, JavaScript, HTML, CSS, Python",
        "certifications": [],
        "langues": [("Français", "courant"), ("Anglais", "intermédiaire")],
    },
    {
        "full_name": "Omar Fassi", "email": "o.fassi@example.ma",
        "offre": "Développeur Python Senior", "qualite": "ecarte",
        "titre": "Développeur junior",
        "diplome": "Licence en Informatique", "niveau": "Bac+3", "annee_diplome": 2024,
        "postes": [
            ("Septembre 2024", "Présent", "Développeur Junior", "Startup Lab",
             "Premiers développements en Python et JavaScript."),
        ],
        "competences": "Python, JavaScript, HTML, CSS",
        "certifications": [],
        "langues": [("Français", "courant"), ("Anglais", "intermédiaire")],
    },
    # --- Développeur Frontend React ---
    {
        "full_name": "Salma Idrissi", "email": "s.idrissi@example.ma",
        "offre": "Développeur Frontend React", "qualite": "excellent",
        "titre": "Développeuse frontend",
        "diplome": "Master en Systèmes d'Information", "niveau": "Bac+5", "annee_diplome": 2019,
        "postes": [
            ("Février 2020", "Présent", "Développeuse Frontend Senior", "Capgemini Maroc",
             "Conception d'interfaces React et Next.js. Accessibilité et performance. "
             "Mise en place de tests unitaires."),
        ],
        "competences": "JavaScript, TypeScript, React, Next.js, CSS, HTML, Tests, Git",
        "certifications": [],
        "langues": [("Français", "bilingue"), ("Anglais", "courant")],
    },
    {
        "full_name": "Hamza Berrada", "email": "h.berrada@example.ma",
        "offre": "Développeur Frontend React", "qualite": "bon",
        "titre": "Développeur front-end",
        "diplome": "Licence Professionnelle en Développement Web", "niveau": "Bac+3",
        "annee_diplome": 2021,
        "postes": [
            ("Octobre 2021", "Présent", "Développeur Frontend", "Umanis",
             "Intégration d'interfaces avec React. Travail avec les équipes design."),
        ],
        "competences": "JavaScript, React, CSS, HTML, Git",
        "certifications": [],
        "langues": [("Français", "courant"), ("Anglais", "bon niveau")],
    },
    {
        "full_name": "Nada Bouzidi", "email": "n.bouzidi@example.ma",
        "offre": "Développeur Frontend React", "qualite": "moyen",
        "titre": "Intégratrice web",
        "diplome": "DUT Informatique", "niveau": "Bac+2", "annee_diplome": 2022,
        "postes": [
            ("Janvier 2022", "Présent", "Intégratrice Web", "Agence Pixel",
             "Intégration HTML et CSS de maquettes. Premières bases en JavaScript."),
        ],
        "competences": "HTML, CSS, JavaScript",
        "certifications": [],
        "langues": [("Français", "courant")],
    },
    # --- Data Scientist ---
    {
        "full_name": "Reda Alaoui", "email": "r.alaoui@example.ma",
        "offre": "Data Scientist", "qualite": "excellent",
        "titre": "Data scientist",
        "diplome": "Master en Data Science", "niveau": "Bac+5", "annee_diplome": 2018,
        "postes": [
            ("Janvier 2020", "Présent", "Data Scientist", "Attijariwafa Bank",
             "Conception de modèles de scoring. Traitement automatique du langage. "
             "Tableaux de bord Power BI pour les directions métier."),
            ("Septembre 2018", "Décembre 2019", "Analyste de données", "Deloitte",
             "Analyses statistiques et restitutions décisionnelles."),
        ],
        "competences": "Python, Machine Learning, SQL, Deep Learning, NLP, Power BI, Data Science",
        "certifications": ["Microsoft Certified: Azure Data Scientist Associate (2022)"],
        "langues": [("Français", "bilingue"), ("Anglais", "courant")],
    },
    {
        "full_name": "Ghita Sebti", "email": "g.sebti@example.ma",
        "offre": "Data Scientist", "qualite": "bon",
        "titre": "Analyste données",
        "diplome": "Master en Statistiques", "niveau": "Bac+5", "annee_diplome": 2020,
        "postes": [
            ("Mars 2021", "Présent", "Analyste Data", "Inwi",
             "Analyses prédictives et modélisation. Requêtes SQL sur entrepôt de données."),
        ],
        "competences": "Python, SQL, Machine Learning, Data Science",
        "certifications": [],
        "langues": [("Français", "courant"), ("Anglais", "bon niveau")],
    },
    {
        "full_name": "Anas Kettani", "email": "a.kettani@example.ma",
        "offre": "Data Scientist", "qualite": "ecarte",
        "titre": "Développeur",
        "diplome": "Licence en Informatique", "niveau": "Bac+3", "annee_diplome": 2022,
        "postes": [
            ("Juillet 2022", "Présent", "Développeur", "SQLI",
             "Développement d'applications de gestion."),
        ],
        "competences": "Java, SQL, Spring",
        "certifications": [],
        "langues": [("Français", "courant")],
    },
    # --- Ingénieur DevOps ---
    {
        "full_name": "Mohammed Benjelloun", "email": "m.benjelloun@example.ma",
        "offre": "Ingénieur DevOps", "qualite": "excellent",
        "titre": "Ingénieur DevOps",
        "diplome": "Master en Réseaux et Systèmes", "niveau": "Bac+5", "annee_diplome": 2017,
        "postes": [
            ("Janvier 2019", "Présent", "Ingénieur DevOps", "Maroc Telecom",
             "Orchestration Kubernetes, automatisation des déploiements, supervision. "
             "Migration d'infrastructures vers AWS."),
            ("Septembre 2017", "Décembre 2018", "Administrateur Systèmes", "CBI",
             "Administration de serveurs Linux et scripts d'automatisation."),
        ],
        "competences": "Docker, Kubernetes, CI/CD, Linux, AWS, Python, Git",
        "certifications": [
            "Certified Kubernetes Administrator (2021)",
            "AWS Certified Solutions Architect (2020)",
        ],
        "langues": [
            ("Français", "bilingue"), ("Anglais", "courant"),
            ("Arabe", "langue maternelle"),
        ],
    },
    {
        "full_name": "Sofia Naciri", "email": "s.naciri@example.ma",
        "offre": "Ingénieur DevOps", "qualite": "moyen",
        "titre": "Administratrice systèmes",
        "diplome": "Licence en Réseaux", "niveau": "Bac+3", "annee_diplome": 2020,
        "postes": [
            ("Mars 2021", "Présent", "Administratrice Systèmes", "Dell Technologies",
             "Administration Linux, sauvegardes, supervision des environnements."),
        ],
        "competences": "Linux, Docker, Git",
        "certifications": [],
        "langues": [("Français", "courant"), ("Anglais", "bon niveau")],
    },
    # --- Stage Full Stack ---
    {
        "full_name": "Ilyas Mansouri", "email": "i.mansouri@example.ma",
        "offre": "Développeur Full Stack — Stage", "qualite": "excellent",
        "titre": "Étudiant en ingénierie informatique",
        "diplome": "Licence en Ingénierie Informatique", "niveau": "Bac+3", "annee_diplome": 2025,
        "postes": [
            ("Juin 2024", "Août 2024", "Stagiaire Développeur", "Softcentre",
             "Développement d'une application web avec React et Flask. "
             "Utilisation de Git et des méthodes agiles."),
        ],
        "competences": "JavaScript, Python, React, Flask, Git, HTML, CSS",
        "certifications": [],
        "langues": [("Français", "courant"), ("Anglais", "bon niveau")],
    },
    {
        "full_name": "Meryem Chraibi", "email": "m.chraibi@example.ma",
        "offre": "Développeur Full Stack — Stage", "qualite": "bon",
        "titre": "Étudiante en informatique",
        "diplome": "Licence en Informatique", "niveau": "Bac+3", "annee_diplome": 2025,
        "postes": [
            ("Juillet 2024", "Septembre 2024", "Stagiaire", "Novec",
             "Participation au développement d'un outil interne en Python."),
        ],
        "competences": "Python, JavaScript, HTML, CSS, Git",
        "certifications": [],
        "langues": [("Français", "courant")],
    },
    # --- Administrateur BDD ---
    {
        "full_name": "Rachid Alami", "email": "r.alami@example.ma",
        "offre": "Administrateur Base de Données", "qualite": "excellent",
        "titre": "Administrateur de bases de données",
        "diplome": "Master en Systèmes d'Information", "niveau": "Bac+5", "annee_diplome": 2016,
        "postes": [
            ("Février 2018", "Présent", "Administrateur BDD", "CNSS",
             "Exploitation et optimisation de bases PostgreSQL et Oracle. "
             "Sauvegardes, réplication et sécurisation des accès."),
        ],
        "competences": "PostgreSQL, SQL, Linux, Oracle, Docker",
        "certifications": ["Oracle Database Administrator Certified Professional (2019)"],
        "langues": [("Français", "bilingue"), ("Anglais", "bon niveau")],
    },
    {
        "full_name": "Khadija Rami", "email": "k.rami@example.ma",
        "offre": "Administrateur Base de Données", "qualite": "bon",
        "titre": "Analyste bases de données",
        "diplome": "Licence en Informatique", "niveau": "Bac+3", "annee_diplome": 2020,
        "postes": [
            ("Septembre 2020", "Présent", "Analyste BDD", "Marsa Maroc",
             "Administration de bases PostgreSQL, écriture de requêtes complexes."),
        ],
        "competences": "PostgreSQL, SQL, Linux",
        "certifications": [],
        "langues": [("Français", "courant")],
    },
]


def _telephone(email):
    """Numéro fictif stable, dérivé de l'adresse pour rester reproductible."""
    empreinte = sum(ord(c) for c in email)
    corps = f"{empreinte % 100:02d} {(empreinte // 7) % 100:02d} " \
            f"{(empreinte // 13) % 100:02d} {(empreinte // 29) % 100:02d}"
    return f"+212 6 {corps}"


def texte_cv(candidat):
    """Compose le contenu textuel d'un CV, structuré comme un document réel."""
    lignes = [
        # Le nom porte par le document peut differer de celui du compte : les
        # jeux de controle en ont besoin pour declencher le rapprochement
        # d'identite.
        candidat.get("nom_document", candidat["full_name"]).upper(),
        candidat["titre"],
        f"{candidat['email']} | {_telephone(candidat['email'])}",
        "",
        "EXPÉRIENCE PROFESSIONNELLE",
        "",
    ]

    for debut, fin, poste, entreprise, description in candidat["postes"]:
        lignes.append(f"{debut} – {fin}")
        lignes.append(f"{poste} chez {entreprise}")
        for phrase in description.split(". "):
            if phrase.strip():
                lignes.append(f"  {phrase.strip().rstrip('.')}.")
        lignes.append("")

    lignes += [
        "FORMATION",
        "",
        f"{candidat['annee_diplome']} - {candidat['diplome']}, "
        f"{candidat.get('etablissement', 'Université Mohammed V')}",
        "",
    ]

    if candidat["certifications"]:
        lignes += ["CERTIFICATIONS", ""]
        lignes += list(candidat["certifications"])
        lignes.append("")

    lignes += ["COMPÉTENCES", "", candidat["competences"], "", "LANGUES", ""]
    lignes += [f"{langue} : {niveau}" for langue, niveau in candidat["langues"]]

    return "\n".join(lignes)
