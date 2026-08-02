"""Tests du moteur de score et de la règle RG-01."""
from app.services.scoring import SEUIL_RETENU, appliquer_regle_top, calculer_score


class OffreFictive:
    """Double de test : évite de dépendre de la base pour tester le moteur."""

    def __init__(self, skills=None, exp=0, degree=None):
        self.required_skills = skills or []
        self.min_experience_years = exp
        self.min_degree = degree


def test_profil_parfait_obtient_un_score_eleve():
    offre = OffreFictive(["python", "sql"], exp=3, degree="Bac+3")
    profil = {"skills": ["python", "sql", "docker"], "experience_years": 5, "degree": "Bac+5"}

    score, details = calculer_score(profil, offre)

    assert score >= 90
    assert details["eliminatoires"] == []
    assert set(details["competences_trouvees"]) == {"python", "sql"}


def test_experience_insuffisante_declenche_un_critere_eliminatoire():
    offre = OffreFictive(["python"], exp=5)
    profil = {"skills": ["python"], "experience_years": 1, "degree": "Bac+5"}

    score, details = calculer_score(profil, offre)

    assert score < SEUIL_RETENU
    assert len(details["eliminatoires"]) == 1
    # Le motif exact doit etre trace (exigence d'explicabilite)
    assert "1 an(s) < 5 an(s)" in details["eliminatoires"][0]


def test_diplome_insuffisant_est_trace():
    offre = OffreFictive(["python"], degree="Bac+5")
    profil = {"skills": ["python"], "experience_years": 10, "degree": "Bac+2"}

    _, details = calculer_score(profil, offre)

    assert any("Diplôme" in m for m in details["eliminatoires"])


def test_competences_manquantes_font_baisser_le_score():
    offre = OffreFictive(["python", "sql", "docker", "kubernetes"])
    profil = {"skills": ["python"], "experience_years": 0, "degree": None}

    score, details = calculer_score(profil, offre)

    assert details["competences_manquantes"] == ["sql", "docker", "kubernetes"]
    assert score < 60


class CandidatureFictive:
    def __init__(self, score):
        self.score = score


def test_regle_top_applique_le_seuil_et_le_plafond():
    # 12 candidatures au-dessus du seuil, 3 en dessous
    candidatures = [CandidatureFictive(50 + i) for i in range(12)]
    candidatures += [CandidatureFictive(s) for s in (10, 30, 49)]

    resultat = appliquer_regle_top(candidatures)

    assert len(resultat["top"]) == 10          # plafond respecte
    assert len(resultat["ecartees"]) == 3      # sous le seuil
    assert resultat["top"][0].score == 61      # trie par score decroissant


def test_regle_top_ne_remplit_pas_artificiellement():
    """Moins de 10 candidatures retenues : le Top ne contient que celles-ci."""
    candidatures = [CandidatureFictive(80), CandidatureFictive(60), CandidatureFictive(20)]

    resultat = appliquer_regle_top(candidatures)

    assert len(resultat["top"]) == 2
    assert len(resultat["ecartees"]) == 1
