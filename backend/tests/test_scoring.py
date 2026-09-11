"""Tests du moteur de score et de la règle RG-01."""
from app.services.scoring import (
    AMPLITUDE_MODELE,
    CREDIT_DECLAREE,
    POIDS_COMPETENCES,
    POIDS_SEMANTIQUE,
    POIDS_SOUHAITEES,
    SEUIL_RETENU,
    appliquer_regle_top,
    calculer_score,
    qualifier,
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


# ----------------------- Pondération par la preuve -----------------------
#
# Le défaut visé est celui qu'un jeu de validation trop facile ne révèle pas :
# un curriculum qui cite toutes les compétences exigées sans qu'aucune
# n'apparaisse dans le récit de ce qu'il a fait. Le moteur le notait comme un
# profil pleinement compétent.

class _Offre:
    """Offre minimale, à la forme attendue par le moteur."""

    def __init__(self, requises, annees=2, diplome="Bac+3"):
        self.required_skills = requises
        self.preferred_skills = []
        self.min_experience_years = annees
        self.min_degree = diplome
        self.description = ""
        self.title = "Poste"


def _profil(skills, etayees, annees=5, diplome="Bac+5"):
    return {
        "skills": skills,
        "skills_etayees": etayees,
        "experience_years": annees,
        "degree": diplome,
    }


def test_une_competence_pratiquee_vaut_plus_qu_une_competence_citee():
    """Le coefficient est calibré sur les cibles annoncées, pas sur le F1.

    Le balayage complet figure au rapport. Il montre un compromis régulier
    entre précision et rappel, et une seule valeur satisfait les deux
    objectifs du cahier des charges — 85 % de précision, 80 % de rappel. Le F1
    serait plus élevé sans aucune pénalité : c'est le respect de la
    spécification qui a décidé.

    Ce test échoue si quelqu'un modifie le coefficient sans refaire la mesure
    qui l'a fixé.
    """
    offre = _Offre(["python", "docker"])
    pratiquee, _ = calculer_score(
        _profil(["python", "docker"], ["python", "docker"]), offre
    )
    citee, _ = calculer_score(_profil(["python", "docker"], []), offre)
    assert pratiquee > citee
    # Une compétence citée conserve les trois quarts de sa valeur. L'écart est
    # donc borné par le quart du poids réellement porté par les compétences
    # obligatoires — poids qui absorbe ici celui des composantes absentes,
    # aucune similarité ni compétence souhaitée n'étant fournie.
    poids = POIDS_COMPETENCES + POIDS_SEMANTIQUE + POIDS_SOUHAITEES
    assert (pratiquee - citee) <= (1 - CREDIT_DECLAREE) * poids + 1


def test_un_profil_sans_information_d_etayage_n_est_pas_penalise():
    """Profil saisi à la main : aucun récit où chercher la preuve.

    Le doute ne se paie pas. Sans cette garde, toute saisie manuelle serait
    notée comme un curriculum entièrement déclaratif.
    """
    offre = _Offre(["python", "docker"])
    sans_info = {
        "skills": ["python", "docker"], "experience_years": 5, "degree": "Bac+5",
    }
    reference, _ = calculer_score(
        _profil(["python", "docker"], ["python", "docker"]), offre
    )
    mesure, _ = calculer_score(sans_info, offre)
    assert mesure == reference


def test_le_detail_nomme_les_competences_non_etayees():
    """L'écart de points doit être explicable, sinon il est arbitraire."""
    offre = _Offre(["python", "docker"])
    _, details = calculer_score(_profil(["python", "docker"], ["python"]), offre)
    assert details["competences_etayees"] == ["python"]
    assert details["competences_declarees"] == ["docker"]


def test_une_reserve_est_posee_quand_la_preuve_manque_majoritairement():
    offre = _Offre(["python", "docker", "sql"])
    _, details = calculer_score(
        _profil(["python", "docker", "sql"], ["python"]), offre
    )
    assert any("sans apparaître dans l'expérience" in r for r in details["reserves"])


def test_la_reserve_ne_transforme_pas_en_eliminatoire():
    """Une compétence citée n'est jamais niée : elle n'écarte pas."""
    offre = _Offre(["python", "docker", "sql"])
    _, details = calculer_score(_profil(["python", "docker", "sql"], []), offre)
    assert details["eliminatoires"] == []


# ----------------------- Échelle des diplômes -----------------------

def test_licence_et_master_sont_a_un_niveau_d_ecart():
    """Deux diplômes adjacents, quelles que soient les années qui les séparent.

    Le défaut corrigé ici ne se voyait nulle part : la distance entre diplômes
    était comptée en années d'études, si bien que Bac+3 pour un poste Bac+5
    valait un écart de 2, franchissait le seuil de la réserve et rendait la
    candidature éliminatoire. La branche « un niveau d'écart » était donc
    inatteignable pour le cas le plus courant qu'elle devait traiter — et le
    jeu de validation y perdait cinq candidatures légitimes.
    """
    offre = _Offre(["python"], annees=3, diplome="Bac+5")
    profil = _profil(["python"], ["python"], annees=3, diplome="Bac+3")
    _, details = calculer_score(profil, offre)
    assert details["eliminatoires"] == []
    assert any("un niveau d'écart" in r for r in details["reserves"])


def test_un_ecart_de_deux_diplomes_reste_eliminatoire():
    """La règle n'est pas supprimée, elle est mesurée dans la bonne unité."""
    offre = _Offre(["python"], annees=3, diplome="Bac+5")
    profil = _profil(["python"], ["python"], annees=3, diplome="Bac+2")
    _, details = calculer_score(profil, offre)
    assert details["eliminatoires"]


def test_l_experience_compense_toujours_un_diplome_manquant():
    offre = _Offre(["python"], annees=3, diplome="Bac+5")
    profil = _profil(["python"], ["python"], annees=9, diplome="Bac+3")
    _, details = calculer_score(profil, offre)
    assert details["eliminatoires"] == []
    assert any("compensé par" in r for r in details["reserves"])


# ----------------------- Référentiel des deux côtés -----------------------

def test_une_abreviation_dans_l_offre_reconnait_la_competence():
    """« K8s » exigé, « kubernetes » possédé : c'est la même compétence.

    Le référentiel n'était appliqué qu'au curriculum. Une offre rédigée avec
    les abréviations usuelles du métier — JS, K8s, Postgres, Spring Boot —
    ne trouvait donc jamais preneur : la compétence était déclarée absente,
    donc éliminatoire. Un recruteur écartait ainsi tous ses candidats sans
    qu'aucun message ne le signale.
    """
    offre = _Offre(["K8s", "JS"])
    profil = _profil(["kubernetes", "javascript"], ["kubernetes", "javascript"])
    score, details = calculer_score(profil, offre, similarite_semantique=0.8)
    assert details["competences_manquantes"] == []
    assert details["eliminatoires"] == []
    assert score >= SEUIL_RETENU


def test_une_competence_reellement_absente_reste_eliminatoire():
    """La normalisation ne rend pas le moteur permissif."""
    offre = _Offre(["Terraform"])
    profil = _profil(["kubernetes"], ["kubernetes"])
    _, details = calculer_score(profil, offre, similarite_semantique=0.8)
    assert details["eliminatoires"]


def test_la_competence_manquante_garde_le_libelle_du_recruteur():
    """Il doit se reconnaître dans la liste, pas y lire une forme interne."""
    offre = _Offre(["Terraform"])
    profil = _profil(["kubernetes"], ["kubernetes"])
    _, details = calculer_score(profil, offre)
    assert details["competences_manquantes"] == ["Terraform"]


def test_les_competences_souhaitees_passent_aussi_par_le_referentiel():
    offre = _Offre(["python"])
    offre.preferred_skills = ["K8s"]
    profil = _profil(["python", "kubernetes"], ["python", "kubernetes"])
    _, details = calculer_score(profil, offre)
    assert details["competences_souhaitees_trouvees"] == ["kubernetes"]


def test_deux_ans_sur_trois_reste_une_reserve():
    """La tolérance implémente enfin ce que sa documentation annonçait.

    Le commentaire de « TOLERANCE_EXPERIENCE » donnait « quatre ans sur six »
    comme limite du tolérable. À 0,7, ce cas précis tombait à 0,667, passait
    sous le seuil et devenait éliminatoire : l'exemple documenté était rejeté
    par la constante qu'il documentait. Deux tiers implémente l'intention.
    """
    offre = _Offre(["python"], annees=3, diplome="Bac+3")
    profil = _profil(["python"], ["python"], annees=2, diplome="Bac+5")
    _, details = calculer_score(profil, offre, similarite_semantique=0.6)
    assert details["eliminatoires"] == []
    assert any("2 an(s) pour 3" in r for r in details["reserves"])


def test_quatre_ans_sur_six_reste_une_reserve():
    offre = _Offre(["python"], annees=6, diplome="Bac+3")
    profil = _profil(["python"], ["python"], annees=4, diplome="Bac+5")
    _, details = calculer_score(profil, offre, similarite_semantique=0.6)
    assert details["eliminatoires"] == []


def test_un_manque_de_plus_d_un_tiers_reste_eliminatoire():
    """La règle n'est pas supprimée : au-delà d'un tiers, elle disqualifie."""
    offre = _Offre(["python"], annees=6, diplome="Bac+3")
    profil = _profil(["python"], ["python"], annees=3, diplome="Bac+5")
    _, details = calculer_score(profil, offre, similarite_semantique=0.6)
    assert details["eliminatoires"]


# ----------------------- Une mesure qui n'a pas eu lieu -----------------------
#
# Un CV dont l'expérience n'a pas pu être lue ne doit pas être écarté « pour
# 0 an d'expérience » : la plateforme opposerait alors au candidat une lacune
# de lecture présentée comme un fait établi sur lui. La candidature passe en
# réserve — elle appelle une vérification humaine, elle n'est pas tranchée.

def test_une_experience_non_determinee_n_ecarte_pas_la_candidature():
    offre = OffreFictive(["python"], exp=4)
    profil = {
        "skills": ["python"],
        "experience_years": 0,
        "experience_determinee": False,
        "degree": "Bac+5",
    }
    eliminatoires, reserves, mesures = qualifier(profil, offre)

    assert eliminatoires == []
    assert any("non déterminée" in r for r in reserves)
    assert mesures["experience_determinee"] is False
    assert mesures["annees_manquantes"] == 0


def test_une_experience_mesuree_a_zero_reste_eliminatoire():
    """Zéro an réellement lu dans le document garde sa conséquence."""
    offre = OffreFictive(["python"], exp=4)
    profil = {
        "skills": ["python"],
        "experience_years": 0,
        "experience_determinee": True,
        "degree": "Bac+5",
    }
    eliminatoires, _reserves, _mesures = qualifier(profil, offre)

    assert any("0 an(s)" in e for e in eliminatoires)


def test_un_profil_sans_mention_d_experience_est_tenu_pour_determine():
    """Saisie manuelle : une valeur fournie par le recruteur est voulue."""
    offre = OffreFictive(["python"], exp=4)
    profil = {"skills": ["python"], "experience_years": 0, "degree": "Bac+5"}
    eliminatoires, _reserves, _mesures = qualifier(profil, offre)

    assert any("0 an(s)" in e for e in eliminatoires)


def test_une_experience_non_determinee_n_ouvre_pas_l_equivalence_de_diplome():
    """On ne peut pas compenser un diplôme par une expérience non mesurée."""
    offre = OffreFictive(["python"], exp=2, degree="Bac+5")
    profil = {
        "skills": ["python"],
        "experience_years": 0,
        "experience_determinee": False,
        "degree": "Bac+3",
    }
    _elim, _res, mesures = qualifier(profil, offre)

    assert mesures["diplome_par_equivalence"] is False


def test_le_motif_de_rejet_dit_la_duree_reelle_et_non_zero_an():
    """« 0 an(s) » opposé à deux mois de stage est une demi-vérité."""
    offre = OffreFictive(["python"], exp=4)
    profil = {
        "skills": ["python"],
        "experience_years": 0,
        "experience_months": 2,
        "experience_determinee": True,
        "degree": "Bac+5",
    }
    eliminatoires, _reserves, _mesures = qualifier(profil, offre)

    assert any("2 mois" in e for e in eliminatoires)
    assert not any("0 an(s)" in e for e in eliminatoires)
