"""Tests du moteur de score et de la règle RG-01."""
from app.services.scoring import (
    AMPLITUDE_MODELE,
    SEUIL_RETENU,
    appliquer_regle_top,
    calculer_score,
)


class OffreFictive:
    """Double de test : évite de dépendre de la base pour tester le moteur."""

    def __init__(self, skills=None, exp=0, degree=None, titre="Poste"):
        self.required_skills = skills or []
        self.min_experience_years = exp
        self.min_degree = degree
        self.title = titre


def test_profil_parfait_obtient_un_score_eleve():
    offre = OffreFictive(["python", "sql"], exp=3, degree="Bac+3")
    profil = {"skills": ["python", "sql", "docker"], "experience_years": 5, "degree": "Bac+5"}

    score, details = calculer_score(profil, offre)

    assert score >= 90
    assert details["eliminatoires"] == []
    assert set(details["competences_trouvees"]) == {"python", "sql"}


def test_experience_tres_insuffisante_declenche_un_critere_eliminatoire():
    offre = OffreFictive(["python"], exp=5)
    profil = {"skills": ["python"], "experience_years": 1, "degree": "Bac+5"}

    score, details = calculer_score(profil, offre)

    assert score < SEUIL_RETENU
    assert len(details["eliminatoires"]) == 1
    # Le motif exact doit etre trace (exigence d'explicabilite)
    assert "1 an(s)" in details["eliminatoires"][0]
    assert "5 an(s)" in details["eliminatoires"][0]


# --------------------------------------------------------------------------
# Réserves : l'écart mesuré n'élimine pas, il se signale
# --------------------------------------------------------------------------

def test_experience_legerement_insuffisante_produit_une_reserve():
    """Quatre ans sur cinq demandés : un recruteur reçoit ce candidat."""
    offre = OffreFictive(["python"], exp=5, degree="Bac+5")
    profil = {"skills": ["python"], "experience_years": 4, "degree": "Bac+5"}

    score, details = calculer_score(profil, offre, similarite_semantique=0.5)

    assert details["eliminatoires"] == []
    assert len(details["reserves"]) == 1
    assert "4 an(s)" in details["reserves"][0]
    assert score >= SEUIL_RETENU


def test_diplome_compense_par_l_experience():
    """Transposition de la clause « ou expérience équivalente »."""
    offre = OffreFictive(["python"], exp=3, degree="Bac+5")
    profil = {"skills": ["python"], "experience_years": 8, "degree": "Bac+3"}

    _, details = calculer_score(profil, offre, similarite_semantique=0.5)

    assert details["eliminatoires"] == []
    assert any("compensé" in r for r in details["reserves"])


def test_competence_obligatoire_absente_reste_eliminatoire():
    """Une compétence indispensable ne se compense par rien."""
    offre = OffreFictive(["python", "kubernetes"], exp=2)
    profil = {"skills": ["python"], "experience_years": 10, "degree": "Doctorat"}

    score, details = calculer_score(profil, offre, similarite_semantique=0.9)

    assert score < SEUIL_RETENU
    assert any("kubernetes" in m for m in details["eliminatoires"])


def test_les_candidatures_ecartees_restent_ordonnees():
    """Le recruteur doit pouvoir prioriser un repêchage parmi les écartées."""
    offre = OffreFictive(["python", "sql", "docker"])
    proche = {"skills": ["python", "sql"], "experience_years": 5, "degree": "Bac+5"}
    lointain = {"skills": ["python"], "experience_years": 5, "degree": "Bac+5"}

    score_proche, _ = calculer_score(proche, offre, similarite_semantique=0.5)
    score_lointain, _ = calculer_score(lointain, offre, similarite_semantique=0.5)

    assert score_proche < SEUIL_RETENU
    assert score_lointain < score_proche


def test_diplome_tres_insuffisant_et_non_compense_est_trace():
    """Trois niveaux d'écart sans l'expérience qui les compenserait."""
    offre = OffreFictive(["python"], degree="Bac+5")
    profil = {"skills": ["python"], "experience_years": 2, "degree": "Bac+2"}

    _, details = calculer_score(profil, offre)

    assert any("Diplôme" in m for m in details["eliminatoires"])


def test_competences_manquantes_font_baisser_le_score():
    offre = OffreFictive(["python", "sql", "docker", "kubernetes"])
    profil = {"skills": ["python"], "experience_years": 0, "degree": None}

    score, details = calculer_score(profil, offre)

    assert details["competences_manquantes"] == ["sql", "docker", "kubernetes"]
    assert score < 60


# --------------------------------------------------------------------------
# Ajustement apporte par le modele appris
# --------------------------------------------------------------------------

def test_le_modele_ne_change_rien_lorsqu_il_est_indecis():
    """Une probabilité de 0,5 n'exprime aucun avis : le score doit être intact."""
    offre = OffreFictive(["python", "sql"], exp=3, degree="Bac+3")
    profil = {"skills": ["python", "sql"], "experience_years": 4, "degree": "Bac+5"}

    sans, _ = calculer_score(profil, offre)
    avec, details = calculer_score(profil, offre, probabilite_modele=0.5)

    assert avec == sans
    assert details["modele"]["ajustement"] == 0.0


def test_l_ajustement_du_modele_reste_borne():
    offre = OffreFictive(["python"], exp=1)
    profil = {"skills": ["python"], "experience_years": 3, "degree": "Bac+5"}

    reference, _ = calculer_score(profil, offre)
    favorable, details = calculer_score(profil, offre, probabilite_modele=1.0)
    defavorable, _ = calculer_score(profil, offre, probabilite_modele=0.0)

    assert abs(favorable - reference) <= AMPLITUDE_MODELE
    assert abs(defavorable - reference) <= AMPLITUDE_MODELE
    assert favorable >= reference >= defavorable
    assert details["modele"]["probabilite"] == 1.0


def test_le_modele_ne_rattrape_pas_une_candidature_ecartee_par_une_regle():
    """Les règles restent souveraines : aucun avis statistique ne les renverse."""
    offre = OffreFictive(["python", "kubernetes"], exp=5)
    profil = {"skills": ["python"], "experience_years": 1, "degree": None}

    score, details = calculer_score(profil, offre, probabilite_modele=1.0)

    assert score < SEUIL_RETENU
    assert details["modele"]["applique"] is False
    assert details["eliminatoires"]


def test_le_detail_du_modele_est_absent_sans_modele():
    offre = OffreFictive(["python"])
    profil = {"skills": ["python"], "experience_years": 2, "degree": "Bac+5"}

    _, details = calculer_score(profil, offre)

    assert "modele" not in details


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
