"""Tests du pipeline d'analyse : extraction linguistique, sémantique, score."""
from app.services import nlp, semantique
from app.services.analyse import analyser_texte
from app.services.extraction import nettoyer

CV_DEVELOPPEUR = """
Aymen Benrbib — Ingénieur logiciel
Master en Ingénierie des Systèmes d'Information (Bac+5), 2024

EXPÉRIENCE
2019 - 2024 : Développeur Full Stack
  Conception d'API REST avec Flask et PostgreSQL
  Déploiement conteneurisé avec Docker, intégration continue
  Analyse de données et modèles de machine learning

COMPÉTENCES
Python, JavaScript, React, Flask, Docker, PostgreSQL, Git, SQL
Langues : Français, Anglais
"""

CV_COMMUNICATION = """
Sara Alaoui — Chargée de communication
Licence en communication (Bac+3), 2022

EXPÉRIENCE
2022 - 2024 : Community manager
  Animation des réseaux sociaux, rédaction de contenus éditoriaux
  Organisation d'événements et relations presse
"""


class OffreFictive:
    def __init__(self, titre, description, skills=None, exp=0, degree=None):
        self.title = titre
        self.description = description
        self.required_skills = skills or []
        self.min_experience_years = exp
        self.min_degree = degree


OFFRE_DEV = OffreFictive(
    "Développeur Python Senior",
    "Conception d'interfaces de programmation et de traitements de données. "
    "Environnement conteneurisé, intégration continue.",
    skills=["python", "sql", "docker"],
    exp=3,
    degree="Bac+3",
)


# ----------------------- Extraction linguistique -----------------------

def test_extraction_des_competences():
    competences = nlp.extraire_competences(CV_DEVELOPPEUR)
    for attendue in ("python", "docker", "postgresql", "flask", "react"):
        assert attendue in competences


def test_les_variantes_sont_ramenees_a_une_forme_unique():
    """« JS », « JavaScript » et « Java Script » désignent la même compétence."""
    for ecriture in ("Je maîtrise JS", "Développement JavaScript", "Java Script avancé"):
        assert "javascript" in nlp.extraire_competences(ecriture)


def test_pas_de_faux_positif_sur_les_sigles_courts():
    """Le langage R ne doit pas être détecté dans un texte quelconque."""
    assert "r" not in nlp.extraire_competences("Rédaction de rapports réguliers")


def test_extraction_du_diplome_le_plus_eleve():
    assert nlp.extraire_diplome(CV_DEVELOPPEUR) == "Bac+5"
    assert nlp.extraire_diplome(CV_COMMUNICATION) == "Bac+3"
    assert nlp.extraire_diplome("Aucun diplôme mentionné ici") is None


def test_experience_calculee_depuis_les_periodes():
    """2019-2024 doit donner 5 ans, sans double comptage."""
    assert nlp.extraire_experience(CV_DEVELOPPEUR) == 5


def test_experience_mention_explicite_prioritaire():
    texte = "7 ans d'expérience en développement. 2020 - 2022 : mission courte."
    assert nlp.extraire_experience(texte) == 7


def test_periodes_qui_se_chevauchent_ne_sont_pas_additionnees():
    texte = "2018 - 2022 : poste A. 2020 - 2022 : poste B en parallèle."
    assert nlp.extraire_experience(texte) == 4


# ----------------------- Similarité sémantique -----------------------

def test_le_cv_pertinent_est_plus_proche_que_le_cv_hors_sujet():
    texte_offre = semantique.texte_offre(OFFRE_DEV)
    proche, _ = semantique.similarite(CV_DEVELOPPEUR, texte_offre)
    loin, _ = semantique.similarite(CV_COMMUNICATION, texte_offre)
    assert proche > loin


def test_similarite_bornee_entre_zero_et_un():
    valeur, _ = semantique.similarite(CV_DEVELOPPEUR, semantique.texte_offre(OFFRE_DEV))
    assert 0.0 <= valeur <= 1.0


# ----------------------- Analyse complète -----------------------

def test_le_profil_pertinent_obtient_un_meilleur_score():
    score_dev, _ = analyser_texte(CV_DEVELOPPEUR, OFFRE_DEV)
    score_com, _ = analyser_texte(CV_COMMUNICATION, OFFRE_DEV)
    assert score_dev > score_com


def test_le_detail_du_calcul_est_fourni():
    """L'explicabilité est une exigence : chaque score doit être justifié."""
    _, details = analyser_texte(CV_DEVELOPPEUR, OFFRE_DEV)

    assert details["statut"] == "analysee"
    assert "profil_analyse" in details
    assert "similarite" in details
    libelles = [c["libelle"].lower() for c in details["composantes"]]
    assert any("compétences obligatoires" in lib for lib in libelles)
    assert any("sémantique" in lib for lib in libelles)
    # Le total des maxima reste sur 100 : les scores sont comparables
    assert sum(c["max"] for c in details["composantes"]) == 100


def test_le_critere_eliminatoire_est_trace_et_plafonne_le_score():
    offre = OffreFictive("Poste senior", "Description", skills=["python"], exp=10)
    score, details = analyser_texte(CV_DEVELOPPEUR, offre)

    assert score <= 45
    assert any("Expérience" in m for m in details["eliminatoires"])


# ----------------------- Nettoyage du texte -----------------------

def test_les_mots_coupes_en_fin_de_ligne_sont_recolles():
    assert "développement" in nettoyer("dévelop-\npement")


def test_les_espaces_multiples_sont_normalises():
    assert nettoyer("mot     suivant") == "mot suivant"
