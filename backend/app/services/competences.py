"""Référentiel de compétences avec leurs variantes d'écriture.

Un même savoir-faire s'écrit de multiples façons dans les CV
(« JS », « JavaScript », « Java Script »). Ce dictionnaire ramène chaque
variante à une forme canonique, ce qui rend la comparaison avec les
compétences exigées par l'offre fiable et reproductible.
"""

# Forme canonique -> variantes rencontrees dans les CV
REFERENTIEL = {
    # Langages
    "python": ["python", "python3", "py"],
    "java": ["java", "java se", "java ee", "j2ee"],
    "javascript": ["javascript", "java script", "js", "ecmascript"],
    "typescript": ["typescript", "ts"],
    "php": ["php", "php7", "php8"],
    "c#": ["c#", "csharp", "c sharp", ".net"],
    "c++": ["c++", "cpp"],
    "sql": ["sql", "pl/sql", "t-sql", "requetes sql"],
    "r": ["langage r", "r studio", "rstudio"],

    # Frontend
    "react": ["react", "react.js", "reactjs"],
    "angular": ["angular", "angularjs", "angular 2"],
    "vue": ["vue", "vue.js", "vuejs"],
    "next.js": ["next.js", "nextjs", "next js"],
    "html": ["html", "html5"],
    "css": ["css", "css3", "sass", "scss", "tailwind"],

    # Backend et frameworks
    "django": ["django"],
    "flask": ["flask"],
    "fastapi": ["fastapi", "fast api"],
    "spring": ["spring", "spring boot", "springboot"],
    "node.js": ["node.js", "nodejs", "node js", "express"],
    "laravel": ["laravel"],

    # Donnees et IA
    "machine learning": [
        "machine learning", "apprentissage automatique", "ml", "scikit-learn", "sklearn",
    ],
    "deep learning": ["deep learning", "apprentissage profond", "tensorflow", "pytorch", "keras"],
    "nlp": ["nlp", "traitement du langage", "spacy", "nltk", "traitement automatique du langage"],
    "data science": ["data science", "science des donnees", "pandas", "numpy"],
    "power bi": ["power bi", "powerbi"],
    "tableau": ["tableau software", "tableau desktop"],

    # Bases de donnees
    "postgresql": ["postgresql", "postgres"],
    "mysql": ["mysql", "mariadb"],
    "mongodb": ["mongodb", "mongo"],
    "oracle": ["oracle", "oracle db"],
    "redis": ["redis"],

    # Infrastructure
    "docker": ["docker", "conteneurisation", "containerisation"],
    "kubernetes": ["kubernetes", "k8s"],
    "git": ["git", "github", "gitlab", "versioning"],
    "ci/cd": ["ci/cd", "cicd", "integration continue", "jenkins", "github actions"],
    "linux": ["linux", "ubuntu", "debian", "unix"],
    "aws": ["aws", "amazon web services"],
    "azure": ["azure", "microsoft azure"],

    # Methodes et transverses
    "agile": ["agile", "scrum", "kanban", "methode agile"],
    "uml": ["uml", "merise", "modelisation"],
    "api rest": ["api rest", "rest", "restful", "api"],
    "tests": ["tests unitaires", "pytest", "junit", "tdd", "qualite logicielle"],
    "cybersecurite": ["cybersecurite", "securite informatique", "pentest"],

    # Gestion, finance et bureautique
    #
    # La plateforme n'est pas reservee aux metiers informatiques : sans ces
    # entrees, une offre de comptable n'aurait aucune competence obligatoire
    # reconnue, et le moteur reporterait tout son poids sur les criteres
    # d'experience et de diplome.
    "comptabilite generale": [
        "comptabilite generale", "comptabilite", "tenue comptable",
        "ecritures comptables", "etats financiers", "bilan comptable",
    ],
    "fiscalite": [
        "fiscalite", "declarations fiscales", "declaration fiscale",
        "tva", "liasse fiscale", "impots",
    ],
    "controle de gestion": [
        "controle de gestion", "controle budgetaire", "reporting financier",
        "analyse des couts",
    ],
    "audit": ["audit", "audit financier", "audit interne", "commissariat aux comptes"],
    "paie": ["paie", "gestion de la paie", "bulletins de paie", "declarations sociales"],
    "excel": ["excel", "microsoft excel", "tableur", "tableaux croises dynamiques"],
    "erp": ["erp", "sap", "odoo", "progiciel de gestion"],
    "sage": ["sage", "sage comptabilite", "sage paie"],

    # Langues
    "anglais": ["anglais", "english"],
    "francais": ["francais", "french"],
    "arabe": ["arabe", "arabic"],
    "espagnol": ["espagnol", "spanish"],
}

# Index inverse : variante -> forme canonique (construit une seule fois)
INDEX_VARIANTES = {
    variante: canonique
    for canonique, variantes in REFERENTIEL.items()
    for variante in variantes
}

# Variantes triees par longueur decroissante : on repere « java script »
# avant « java », evitant les faux positifs.
VARIANTES_TRIEES = sorted(INDEX_VARIANTES, key=len, reverse=True)


def canoniser(competence):
    """Ramène une compétence à sa forme canonique (ou la renvoie nettoyée)."""
    c = (competence or "").strip().lower()
    return INDEX_VARIANTES.get(c, c)
