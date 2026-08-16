"""Génération de profils de démonstration supplémentaires.

Les seize candidats rédigés à la main dans `demo_data` couvrent bien les cas
d'usage, mais restent trop peu nombreux pour éprouver le classement, remplir
les rapports décisionnels ou donner à voir une plateforme en activité.

Ce module en produit une cinquantaine d'autres par composition. Le procédé
n'est pas un remplissage aléatoire : chaque profil est construit **à partir
du résultat attendu**. On décide d'abord qu'un candidat doit être excellent,
correct, limite ou hors sujet, puis on compose le document qui produit ce
résultat — compétences détenues, ancienneté, niveau de diplôme.

Cette construction descendante a une conséquence utile : le jeu obtenu sert
aussi de contrôle de cohérence. Si un profil déclaré excellent obtient une
note basse, c'est le moteur qu'il faut examiner, pas le profil.

Le tirage est reproductible : deux exécutions produisent les mêmes personnes.
"""

# --------------------------------------------------------------------------
# Offres supplémentaires
# --------------------------------------------------------------------------
#
# Elles etendent le domaine couvert au-dela de l'informatique : la plateforme
# n'est pas reservee aux metiers techniques, et le referentiel de competences
# comporte desormais un volet gestion et finance.

OFFRES_SUPPLEMENTAIRES = [
    {
        "title": "Développeur Java Spring",
        "description": (
            "Vous participez à la refonte de nos applications de gestion et à leur "
            "migration vers une architecture de services. Vous intervenez sur la "
            "conception, le développement et les tests."
        ),
        "required_skills": ["java", "spring", "sql"],
        "preferred_skills": ["docker", "agile", "ci/cd"],
        "min_experience_years": 4,
        "min_degree": "Bac+5",
        "status": "open",
        "location": "Rabat",
        "contract_type": "CDI",
        "remote_policy": "hybride",
        "salary_min": 16000,
        "salary_max": 24000,
    },
    {
        "title": "Comptable Général",
        "description": (
            "Vous assurez la tenue de la comptabilité générale, les déclarations "
            "fiscales et la préparation des états financiers. Vous êtes "
            "l'interlocuteur du commissaire aux comptes."
        ),
        "required_skills": ["comptabilite generale", "fiscalite", "excel"],
        "preferred_skills": ["sage", "audit"],
        "min_experience_years": 4,
        "min_degree": "Bac+3",
        "status": "open",
        "location": "Marrakech",
        "contract_type": "CDI",
        "remote_policy": "sur site",
        "salary_min": 10000,
        "salary_max": 15000,
    },
    {
        "title": "Contrôleur de Gestion",
        "description": (
            "Rattaché à la direction financière, vous produisez les analyses de "
            "coûts, le budget et les tableaux de bord de pilotage."
        ),
        "required_skills": ["controle de gestion", "excel", "erp"],
        "preferred_skills": ["power bi", "comptabilite generale"],
        "min_experience_years": 4,
        "min_degree": "Bac+5",
        "status": "open",
        "location": "Tanger",
        "contract_type": "CDI",
        "remote_policy": "sur site",
        "salary_min": 15000,
        "salary_max": 22000,
    },
    {
        "title": "Ingénieur Cybersécurité",
        "description": (
            "Vous auditez la sécurité de nos systèmes, conduisez les tests "
            "d'intrusion et accompagnez les équipes dans la correction des "
            "vulnérabilités."
        ),
        "required_skills": ["cybersecurite", "linux", "python"],
        "preferred_skills": ["aws", "docker"],
        "min_experience_years": 3,
        "min_degree": "Bac+5",
        "status": "open",
        "location": "Casablanca",
        "contract_type": "CDI",
        "remote_policy": "hybride",
        "salary_min": 18000,
        "salary_max": 28000,
    },
    {
        "title": "Développeur PHP Laravel",
        "description": (
            "Vous développez et maintenez les applications métier de nos clients, "
            "de la conception à la mise en production."
        ),
        "required_skills": ["php", "laravel", "mysql"],
        "preferred_skills": ["javascript", "git", "tests"],
        "min_experience_years": 2,
        "min_degree": "Bac+3",
        "status": "open",
        "location": "Fès",
        "contract_type": "CDI",
        "remote_policy": "sur site",
        "salary_min": 9000,
        "salary_max": 14000,
    },
    {
        "title": "Analyste Décisionnel",
        "description": (
            "Vous concevez les tableaux de bord de pilotage de l'entreprise et "
            "accompagnez les directions métier dans la lecture de leurs données."
        ),
        "required_skills": ["power bi", "sql", "excel"],
        "preferred_skills": ["python", "data science"],
        "min_experience_years": 3,
        "min_degree": "Bac+3",
        "status": "closed",     # offre pourvue : donne du relief aux statistiques
        "location": "Casablanca",
        "contract_type": "CDD",
        "remote_policy": "hybride",
        "salary_min": 12000,
        "salary_max": 18000,
    },
]


# --------------------------------------------------------------------------
# Matière première des profils
# --------------------------------------------------------------------------

PRENOMS_M = [
    "Amine", "Bilal", "Chakib", "Driss", "El Mehdi", "Farid", "Ghali", "Hicham",
    "Ismail", "Jalal", "Khalid", "Marouane", "Nabil", "Othmane", "Rachid",
    "Soufiane", "Tarik", "Walid", "Yassir", "Zakaria",
]
PRENOMS_F = [
    "Amal", "Basma", "Chaimae", "Dounia", "Fadwa", "Hajar", "Ikram", "Jamila",
    "Kaoutar", "Lamia", "Malak", "Nawal", "Oumaima", "Rim", "Safaa", "Siham",
    "Wafaa", "Yousra", "Zineb", "Nisrine",
]
NOMS = [
    "Amrani", "Belkacem", "Chraibi", "Daoudi", "El Idrissi", "Fassi", "Guessous",
    "Hakimi", "Jaidi", "Kabbaj", "Lahlou", "Mekouar", "Nejjar", "Ouali",
    "Rifai", "Sbai", "Tazi", "Wahbi", "Yahyaoui", "Zouiten", "Berrada",
    "Cherkaoui", "Drissi", "Filali", "Haddad",
]

ENTREPRISES = [
    "Atlas Digital", "Novatech Maroc", "Groupe Sofimar", "Delta Consulting",
    "Medina Systems", "Cap Innovations", "Zenith Services", "Oriental Group",
    "Rive Sud Conseil", "Tanger Med Services", "Alpha Solutions", "Rif Technologies",
]

VILLES_ECOLES = [
    "Université Mohammed V", "Université Hassan II", "École Nationale Supérieure "
    "d'Informatique", "Université Cadi Ayyad", "Institut Supérieur de Gestion",
    "École Nationale de Commerce et de Gestion", "Université Ibn Zohr",
]


# Pour chaque offre : le vocabulaire du metier, decline par niveau de maitrise.
#
#   socle      : competences exigees par l'offre, detenues par un bon profil
#   avance     : competences valorisantes, propres aux meilleurs profils
#   partiel    : ce que retient un profil approchant, a qui il manque l'essentiel
#   etranger   : competences d'un tout autre metier
#   intitules  : intitules de poste plausibles, du plus junior au plus senior
#   missions   : phrases de description, employees pour composer l'experience
METIERS = {
    "Développeur Java Spring": {
        "socle": "Java, Spring, SQL, Git",
        "avance": "Docker, CI/CD, Agile, Tests, Oracle",
        "partiel": "Java, SQL, Git",
        "etranger": "Comptabilité générale, Excel, Fiscalité",
        "intitules": ["Développeur Java junior", "Développeur Java",
                      "Ingénieur études et développement", "Développeur Java Senior"],
        "missions": [
            "Développement d'applications Spring Boot adossées à une base relationnelle",
            "Migration progressive vers une architecture de services",
            "Écriture de tests unitaires et revue de code entre pairs",
            "Optimisation de requêtes SQL sur des volumes importants",
        ],
        "diplomes": ["Master en Génie Logiciel", "Master en Informatique",
                     "Licence en Informatique", "DUT Informatique"],
    },
    "Comptable Général": {
        "socle": "Comptabilité générale, Fiscalité, Excel",
        "avance": "Sage, Audit, Analyse financière",
        "partiel": "Comptabilité générale, Excel",
        "etranger": "Python, Docker, JavaScript",
        "intitules": ["Assistant comptable", "Comptable", "Comptable général",
                      "Chef comptable"],
        "missions": [
            "Tenue de la comptabilité générale et rapprochements bancaires",
            "Déclarations fiscales mensuelles et liasse fiscale annuelle",
            "Préparation des états financiers et relation avec le commissaire aux comptes",
            "Suivi des immobilisations et des provisions",
        ],
        "diplomes": ["Master en Finance et Comptabilité",
                     "Licence en Comptabilité et Finance", "Licence en Gestion",
                     "DUT Techniques de Commercialisation"],
    },
    "Contrôleur de Gestion": {
        "socle": "Contrôle de gestion, Excel, ERP",
        "avance": "Power BI, Comptabilité générale, Reporting financier",
        "partiel": "Excel, Comptabilité générale",
        "etranger": "React, CSS, JavaScript",
        "intitules": ["Assistant contrôle de gestion", "Analyste de gestion",
                      "Contrôleur de gestion", "Responsable du contrôle de gestion"],
        "missions": [
            "Élaboration du budget annuel et analyse des écarts",
            "Production des tableaux de bord de pilotage mensuels",
            "Analyse des coûts de production et des marges par activité",
            "Extractions du progiciel de gestion et fiabilisation des données",
        ],
        "diplomes": ["Master en Finance d'Entreprise", "Master en Contrôle de Gestion",
                     "Licence en Gestion", "Licence en Économie"],
    },
    "Ingénieur Cybersécurité": {
        "socle": "Cybersécurité, Linux, Python",
        "avance": "AWS, Docker, Tests",
        "partiel": "Linux, Python",
        "etranger": "Comptabilité générale, Excel",
        "intitules": ["Analyste sécurité", "Ingénieur sécurité",
                      "Ingénieur cybersécurité", "Responsable sécurité des systèmes"],
        "missions": [
            "Conduite de tests d'intrusion et rédaction des rapports d'audit",
            "Durcissement des serveurs Linux et supervision des accès",
            "Automatisation des contrôles de sécurité par scripts Python",
            "Accompagnement des équipes dans la correction des vulnérabilités",
        ],
        "diplomes": ["Master en Sécurité des Systèmes d'Information",
                     "Master en Réseaux et Systèmes", "Licence en Réseaux",
                     "DUT Réseaux et Télécommunications"],
    },
    "Développeur PHP Laravel": {
        "socle": "PHP, Laravel, MySQL",
        "avance": "JavaScript, Git, Tests, HTML, CSS",
        "partiel": "PHP, MySQL",
        "etranger": "Contrôle de gestion, Excel",
        "intitules": ["Développeur web junior", "Développeur PHP",
                      "Développeur web", "Développeur PHP Senior"],
        "missions": [
            "Développement d'applications métier avec Laravel et MySQL",
            "Intégration des maquettes et développement des interfaces",
            "Mise en production et maintenance corrective",
            "Écriture de tests et revue de code",
        ],
        "diplomes": ["Master en Informatique", "Licence en Informatique",
                     "DUT Informatique", "Licence Professionnelle en Développement Web"],
    },
    "Analyste Décisionnel": {
        "socle": "Power BI, SQL, Excel",
        "avance": "Python, Data Science, Machine Learning",
        "partiel": "Excel, SQL",
        "etranger": "Kubernetes, Docker, Linux",
        "intitules": ["Analyste junior", "Analyste décisionnel",
                      "Analyste BI", "Consultant décisionnel"],
        "missions": [
            "Construction de tableaux de bord Power BI pour les directions métier",
            "Requêtes SQL sur l'entrepôt de données et fiabilisation des indicateurs",
            "Automatisation des extractions et des rapports récurrents",
            "Accompagnement des utilisateurs dans la lecture des indicateurs",
        ],
        "diplomes": ["Master en Systèmes d'Information", "Master en Statistiques",
                     "Licence en Informatique", "Licence en Mathématiques Appliquées"],
    },
    # Metiers deja couverts par les offres d'origine : les profils generes
    # viennent s'ajouter aux candidats rediges a la main.
    "Développeur Python Senior": {
        "socle": "Python, SQL, Docker, Git",
        "avance": "Flask, PostgreSQL, CI/CD, Kubernetes, Django",
        "partiel": "Python, SQL",
        "etranger": "Comptabilité générale, Excel",
        "intitules": ["Développeur Python junior", "Développeur backend",
                      "Développeur Python", "Développeur Backend Senior"],
        "missions": [
            "Conception d'interfaces de programmation REST avec Flask",
            "Modélisation et optimisation de bases PostgreSQL",
            "Conteneurisation des services et intégration continue",
            "Traitement de volumes de données avec pandas",
        ],
        "diplomes": ["Master en Génie Logiciel", "Master en Informatique",
                     "Licence en Informatique", "DUT Informatique"],
    },
    "Développeur Frontend React": {
        "socle": "JavaScript, React, CSS, HTML",
        "avance": "TypeScript, Next.js, Tests, Git",
        "partiel": "HTML, CSS, JavaScript",
        "etranger": "Comptabilité générale, Fiscalité",
        "intitules": ["Intégrateur web", "Développeur frontend",
                      "Développeur React", "Développeur Frontend Senior"],
        "missions": [
            "Développement de composants React et intégration des maquettes",
            "Travail sur l'accessibilité et les performances des pages",
            "Mise en place de tests d'interface automatisés",
            "Refonte de la charte graphique en feuilles de style structurées",
        ],
        "diplomes": ["Master en Systèmes d'Information", "Licence en Informatique",
                     "Licence Professionnelle en Développement Web", "DUT Informatique"],
    },
    "Data Scientist": {
        "socle": "Python, Machine Learning, SQL",
        "avance": "Deep Learning, NLP, Power BI, Data Science",
        "partiel": "Python, SQL",
        "etranger": "Comptabilité générale, Excel",
        "intitules": ["Analyste de données", "Data analyst",
                      "Data scientist", "Data Scientist Senior"],
        "missions": [
            "Conception de modèles prédictifs et mise en production",
            "Traitement automatique du langage appliqué aux verbatims clients",
            "Requêtes SQL sur entrepôt de données volumineux",
            "Restitution des résultats aux directions métier",
        ],
        "diplomes": ["Master en Data Science", "Master en Statistiques",
                     "Licence en Mathématiques Appliquées", "Licence en Informatique"],
    },
    "Ingénieur DevOps": {
        "socle": "Docker, Kubernetes, Linux, CI/CD",
        "avance": "AWS, Python, Git",
        "partiel": "Linux, Docker",
        "etranger": "Comptabilité générale, Excel",
        "intitules": ["Administrateur systèmes", "Ingénieur systèmes",
                      "Ingénieur DevOps", "Ingénieur de production"],
        "missions": [
            "Exploitation de clusters Kubernetes en production",
            "Automatisation des déploiements et des sauvegardes",
            "Administration de serveurs Linux et supervision",
            "Construction des chaînes de livraison continue",
        ],
        "diplomes": ["Master en Réseaux et Systèmes", "Master en Informatique",
                     "Licence en Réseaux", "DUT Réseaux et Télécommunications"],
    },
    "Administrateur Base de Données": {
        "socle": "PostgreSQL, SQL, Oracle",
        "avance": "Linux, Docker, MySQL",
        "partiel": "SQL, MySQL",
        "etranger": "React, CSS",
        "intitules": ["Technicien base de données", "Développeur base de données",
                      "Administrateur de bases de données", "DBA Senior"],
        "missions": [
            "Administration de bases PostgreSQL et Oracle en production",
            "Optimisation de requêtes et supervision des performances",
            "Sauvegardes, réplication et plans de reprise d'activité",
            "Sécurisation des accès et gestion des habilitations",
        ],
        "diplomes": ["Master en Systèmes d'Information", "Master en Informatique",
                     "Licence en Informatique", "DUT Informatique"],
    },
}


# Pour chaque niveau attendu : ancienneté visée par rapport à l'exigence de
# l'offre, et rang du diplôme.
#
# Le champ `competences` designe les blocs a reunir. Un excellent profil
# possede le socle **et** les competences avancees : ne lui donner que les
# secondes reviendrait a le priver des exigences obligatoires, donc a le faire
# eliminer — l'inverse de ce que son etiquette annonce.
NIVEAUX = {
    "excellent": {"marge_annees": (3, 6),   "rang_diplome": 0,
                  "competences": ("socle", "avance")},
    "bon":       {"marge_annees": (0, 2),   "rang_diplome": 1,
                  "competences": ("socle",)},
    "moyen":     {"marge_annees": (-2, -1), "rang_diplome": 2,
                  "competences": ("partiel",)},
    "ecarte":    {"marge_annees": (-4, -3), "rang_diplome": 3,
                  "competences": ()},          # profil d'un autre metier
}

# Profils d'un tout autre metier, employes pour les candidatures hors sujet.
# Une plateforme de recrutement en recoit constamment : les ignorer donnerait
# une image trop favorable du tri automatique.
PROFILS_ETRANGERS = [
    {
        "titre": "Assistant comptable",
        "competences": "Comptabilité générale, Excel, Fiscalité",
        "missions": ["Saisie des écritures comptables et rapprochements bancaires",
                     "Préparation des déclarations fiscales mensuelles"],
        "diplomes": ["Licence en Gestion", "DUT Techniques de Commercialisation"],
    },
    {
        "titre": "Chargé de communication",
        "competences": "Rédaction, Réseaux sociaux, Événementiel",
        "missions": ["Animation des réseaux sociaux et rédaction de contenus",
                     "Organisation d'événements et relations avec la presse"],
        "diplomes": ["Licence en Communication", "Master en Marketing"],
    },
    {
        "titre": "Technicien de maintenance",
        "competences": "Maintenance, Électromécanique, Hydraulique",
        "missions": ["Maintenance préventive des équipements de production",
                     "Diagnostic et réparation des pannes sur ligne"],
        "diplomes": ["Baccalauréat technique", "DUT Génie Mécanique"],
    },
    {
        "titre": "Chargé de recrutement",
        "competences": "Recrutement, Entretien, Sourcing",
        "missions": ["Sourcing de candidats et conduite des entretiens",
                     "Suivi des intégrations et reporting du vivier"],
        "diplomes": ["Licence en Ressources Humaines", "Master en Gestion des RH"],
    },
    {
        "titre": "Graphiste",
        "competences": "Illustration, Identité visuelle, Mise en page",
        "missions": ["Création d'identités visuelles et de supports imprimés",
                     "Déclinaison des chartes graphiques sur tous supports"],
        "diplomes": ["Licence en Arts Graphiques", "DUT Métiers du Multimédia"],
    },
]

# Repartition des niveaux au sein des candidatures d'une offre. L'ordre
# compte : les premiers elements sont ceux retenus lorsque le nombre de
# candidatures par offre est reduit, et chaque niveau doit y figurer.
REPARTITION = ["excellent", "bon", "moyen", "ecarte", "bon", "moyen", "ecarte"]

NIVEAUX_DIPLOME = ["Bac+5", "Bac+5", "Bac+3", "Bac+2"]

ANNEE_COURANTE = 2026


def _identite(aleatoire, utilises):
    """Tire un nom qui n'a pas déjà servi."""
    for _ in range(200):
        feminin = aleatoire.random() < 0.45
        prenom = aleatoire.choice(PRENOMS_F if feminin else PRENOMS_M)
        nom = aleatoire.choice(NOMS)
        complet = f"{prenom} {nom}"
        if complet not in utilises:
            utilises.add(complet)
            initiale = prenom[0].lower()
            cle = nom.lower().replace(" ", "").replace("'", "")
            return complet, f"{initiale}.{cle}@example.ma"
    raise RuntimeError("Réservoir de noms épuisé.")


def _postes(aleatoire, metier, annees, niveau):
    """Compose un parcours dont la durée totale vaut `annees`."""
    debut = ANNEE_COURANTE - annees
    intitules = metier["intitules"]

    # Un profil experimente affiche deux postes, un junior un seul.
    if annees >= 5:
        bascule = debut + max(2, annees // 2)
        rang = 3 if niveau == "excellent" else 2
        return [
            (f"Janvier {bascule}", "Présent", intitules[rang],
             aleatoire.choice(ENTREPRISES),
             ". ".join(aleatoire.sample(metier["missions"], 2)) + "."),
            (f"Septembre {debut}", f"Décembre {bascule - 1}",
             intitules[max(0, rang - 2)], aleatoire.choice(ENTREPRISES),
             aleatoire.choice(metier["missions"]) + "."),
        ]

    rang = 1 if niveau in ("excellent", "bon") else 0
    return [
        (f"{aleatoire.choice(['Janvier', 'Mars', 'Juin', 'Septembre'])} {debut}",
         "Présent", intitules[rang], aleatoire.choice(ENTREPRISES),
         ". ".join(aleatoire.sample(metier["missions"], 2)) + "."),
    ]


def _langues(aleatoire):
    langues = [("Français", aleatoire.choice(["bilingue", "courant"]))]
    langues.append(("Anglais", aleatoire.choice(["courant", "bon niveau",
                                                 "intermédiaire"])))
    if aleatoire.random() < 0.5:
        langues.append(("Arabe", "langue maternelle"))
    return langues


CERTIFICATIONS = {
    "excellent": [
        "AWS Certified Solutions Architect (2024)",
        "Microsoft Certified: Data Analyst Associate (2023)",
        "Certified Kubernetes Administrator (2024)",
        "Professional Scrum Master I - Scrum.org (2023)",
        "Oracle Certified Professional (2023)",
    ],
    "bon": ["Professional Scrum Master I - Scrum.org (2024)"],
}


# --------------------------------------------------------------------------
# Cas destinés aux contrôles d'anomalies
# --------------------------------------------------------------------------
#
# Sans dossiers douteux, l'ecran de controle resterait vide et la
# fonctionnalite indemontrable. Ces quatre cas couvrent les familles de
# controles, y compris un faux positif : il est important de montrer que le
# dispositif en produit, et qu'un recruteur doit pouvoir l'ecarter.

CAS_DOUTEUX = [
    {
        # Nom du document sans rapport avec celui du compte : usurpation type.
        "compte": "Bilal Sbai",
        "nom_document": "Youssef Tazi",
        "anomalie": "identite_divergente",
        "commentaire": "Le curriculum est au nom d'une autre personne.",
    },
    {
        # Ecart legitime : nom d'epouse. Le controle se declenche quand meme,
        # et c'est au recruteur d'ecarter le signalement.
        "compte": "Kaoutar Bennani",
        "nom_document": "Kaoutar Zniber",
        "anomalie": "identite_divergente_legitime",
        "commentaire": "Nom d'épouse : faux positif attendu, à écarter.",
    },
    {
        # Chronologie impossible : experience anterieure au diplome de 8 ans.
        "compte": "Othmane Rifai",
        "nom_document": "Othmane Rifai",
        "anomalie": "chronologie_incoherente",
        "commentaire": "Premier poste bien antérieur au diplôme.",
    },
]


def generer_cas_douteux(offres, aleatoire, noms_utilises=None):
    """Compose des candidatures destinées à déclencher les contrôles.

    Chaque cas est construit à partir de l'anomalie qu'il doit produire, ce
    qui rend l'écran de contrôle démontrable et vérifiable : on sait à
    l'avance ce qui doit apparaître.
    """
    utilises = noms_utilises if noms_utilises is not None else set()
    candidats = []

    for index, cas in enumerate(CAS_DOUTEUX):
        offre = offres[index % len(offres)]
        metier = METIERS.get(offre["title"])
        if metier is None:
            continue

        exigence = offre.get("min_experience_years") or 3
        annees = exigence + 2
        prenom = cas["compte"].split()[0].lower()
        courriel = f"{prenom[0]}.{cas['compte'].split()[-1].lower()}@example.ma"
        utilises.add(cas["compte"])

        postes = _postes(aleatoire, metier, annees, "bon")

        # Le diplome est place APRES le premier poste pour le cas chronologique.
        if cas["anomalie"] == "chronologie_incoherente":
            annee_diplome = ANNEE_COURANTE - annees + 8
        else:
            annee_diplome = ANNEE_COURANTE - annees - 1

        candidats.append({
            "full_name": cas["compte"],
            # Le nom porte par le document differe volontairement de celui du
            # compte : c'est ce que le controle d'identite doit relever.
            "nom_document": cas["nom_document"],
            "email": courriel,
            "offre": offre["title"],
            "qualite": "bon",
            "titre": postes[0][2],
            "diplome": metier["diplomes"][1],
            "niveau": NIVEAUX_DIPLOME[1],
            "annee_diplome": annee_diplome,
            "postes": postes,
            "competences": metier["socle"],
            "certifications": [],
            "langues": _langues(aleatoire),
            "etablissement": aleatoire.choice(VILLES_ECOLES),
            "_cas": cas["anomalie"],
            "_attendu": cas["commentaire"],
        })

    return candidats


def generer_candidats(offres, aleatoire, par_offre=5, noms_utilises=None):
    """Compose des candidats pour chaque offre, du profil idéal au hors sujet.

    `offres` : liste de dictionnaires d'offres (au moins `title`,
    `min_experience_years` et `min_degree`).
    """
    utilises = noms_utilises if noms_utilises is not None else set()
    candidats = []

    for offre in offres:
        metier = METIERS.get(offre["title"])
        if metier is None:
            continue

        exigence = offre.get("min_experience_years") or 2
        for index in range(par_offre):
            niveau = REPARTITION[index % len(REPARTITION)]
            reglage = NIVEAUX[niveau]
            rang = reglage["rang_diplome"]

            if niveau == "ecarte":
                # Le profil est ecarte par son metier, non par son manque de
                # zele : on lui laisse une anciennete credible ailleurs.
                etranger = aleatoire.choice(PROFILS_ETRANGERS)
                annees = max(2, exigence + aleatoire.randint(-1, 2))
                competences = etranger["competences"]
                diplome = aleatoire.choice(etranger["diplomes"])
                postes = [(
                    f"{aleatoire.choice(['Février', 'Mai', 'Octobre'])} "
                    f"{ANNEE_COURANTE - annees}", "Présent",
                    etranger["titre"], aleatoire.choice(ENTREPRISES),
                    ". ".join(etranger["missions"]) + ".",
                )]
            else:
                annees = max(1, exigence + aleatoire.randint(*reglage["marge_annees"]))
                competences = ", ".join(
                    metier[bloc] for bloc in reglage["competences"]
                )
                diplome = metier["diplomes"][rang]
                postes = _postes(aleatoire, metier, annees, niveau)

            nom, courriel = _identite(aleatoire, utilises)
            candidats.append({
                "full_name": nom,
                "email": courriel,
                "offre": offre["title"],
                "qualite": niveau,
                # L'intitule affiche en tete du document est celui du poste
                # occupe actuellement : le titre et le parcours ne peuvent
                # ainsi pas se contredire.
                "titre": postes[0][2],
                "diplome": diplome,
                "niveau": NIVEAUX_DIPLOME[rang],
                "annee_diplome": max(2010, ANNEE_COURANTE - annees - 1),
                "postes": postes,
                "competences": competences,
                "certifications": (
                    [aleatoire.choice(CERTIFICATIONS[niveau])]
                    if niveau in CERTIFICATIONS and aleatoire.random() < 0.7
                    else []
                ),
                "langues": _langues(aleatoire),
                "etablissement": aleatoire.choice(VILLES_ECOLES),
            })

    return candidats
