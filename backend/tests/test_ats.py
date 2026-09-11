"""Tests du parsing ATS : sections, identité, expériences, formations, langues."""
from app.services import ats

CV_COMPLET = """AYMEN BENRBIB
Ingénieur en systèmes d'information
aymen.benrbib@example.com | +212 6 12 34 56 78 | linkedin.com/in/aymenbenrbib
Rabat, Maroc

EXPÉRIENCE PROFESSIONNELLE

Janvier 2022 – Présent
Développeur Full Stack Senior chez TechCorp Maroc
  Conception d'API REST avec Flask et PostgreSQL
  Mise en place de pipelines CI/CD

Septembre 2019 – Décembre 2021
Développeur Python chez DataSoft
  Traitements de données avec pandas

FORMATION

2024 - Master en Ingénierie des Systèmes d'Information, École des Sciences de l'Information
2019 - Licence en Informatique, Université Mohammed V

CERTIFICATIONS
AWS Certified Developer Associate (2023)
Professional Scrum Master I - Scrum.org (2022)

COMPÉTENCES
Python, JavaScript, React, Flask, Docker, PostgreSQL, Git

LANGUES
Français : bilingue
Anglais : courant
Arabe : langue maternelle
"""


# ----------------------- Découpage en sections -----------------------

def test_les_sections_du_cv_sont_identifiees():
    sections = ats.decouper_en_sections(CV_COMPLET)
    for attendue in ("experience", "formation", "certifications", "competences", "langues"):
        assert attendue in sections and sections[attendue]


def test_l_entete_contient_les_coordonnees():
    sections = ats.decouper_en_sections(CV_COMPLET)
    assert "@" in sections["entete"]


def test_une_ligne_ordinaire_n_est_pas_prise_pour_un_en_tete():
    assert ats._identifier_section("J'ai acquis une solide expérience en gestion") is None
    assert ats._identifier_section("EXPÉRIENCE PROFESSIONNELLE") == ("experience", "")


def test_un_en_tete_suivi_de_son_contenu_ouvre_bien_la_rubrique():
    """« Langues : Français (courant) » sur une seule ligne, CV compact."""
    section, reste = ats._identifier_section("Langues : Français (courant), Anglais (B2)")
    assert section == "langues"
    assert reste == "Français (courant), Anglais (B2)"


def test_une_rubrique_narrative_ne_s_ouvre_pas_en_ligne():
    """« Projet : … » décrit un projet, il n'ouvre pas la rubrique Projets."""
    assert ats._identifier_section("Projet : refonte du portail client") is None


# ----------------------- Identité -----------------------

def test_extraction_des_coordonnees():
    identite = ats.analyser_cv(CV_COMPLET)["basics"]
    assert identite["name"] == "AYMEN BENRBIB"
    assert identite["email"] == "aymen.benrbib@example.com"
    assert identite["linkedin"] == "aymenbenrbib"
    assert identite["phone"] and "212" in identite["phone"]


def test_une_annee_n_est_pas_confondue_avec_un_numero():
    identite = ats.extraire_identite("Youssef Tazi\nDiplômé en 2024\ny@mail.ma")
    assert identite["phone"] is None


# ----------------------- Expériences -----------------------

def test_chaque_poste_est_reconstitue():
    postes = ats.analyser_cv(CV_COMPLET)["work"]
    assert len(postes) == 2

    recent = postes[0]
    assert recent["position"] == "Développeur Full Stack Senior"
    assert recent["company"] == "TechCorp Maroc"
    assert recent["startDate"] == "2022-01"
    assert recent["current"] is True

    precedent = postes[1]
    assert precedent["company"] == "DataSoft"
    assert precedent["startDate"] == "2019-09"
    assert precedent["endDate"] == "2021-12"


def test_la_duree_de_chaque_poste_est_calculee():
    postes = ats.analyser_cv(CV_COMPLET)["work"]
    # Septembre 2019 -> decembre 2021 = 27 mois
    assert postes[1]["months"] == 27


def test_les_postes_simultanes_ne_sont_pas_additionnes():
    experiences = [
        {"startDate": "2018-01", "endDate": "2022-01", "current": False},
        {"startDate": "2020-01", "endDate": "2022-01", "current": False},
    ]
    assert ats.annees_experience(experiences) == 4


# ----------------------- Formation -----------------------

def test_les_diplomes_sont_reconstitues():
    formations = ats.analyser_cv(CV_COMPLET)["education"]
    niveaux = [f["level"] for f in formations]
    assert "Bac+5" in niveaux and "Bac+3" in niveaux


def test_le_niveau_le_plus_eleve_est_retenu():
    assert ats.analyser_cv(CV_COMPLET)["highestDegree"] == "Bac+5"


# ----------------------- Certifications -----------------------

def test_les_certifications_et_leurs_organismes_sont_extraits():
    certifications = ats.analyser_cv(CV_COMPLET)["certificates"]
    assert len(certifications) == 2
    organismes = [c["issuer"] for c in certifications]
    assert "aws" in organismes and "scrum.org" in organismes
    assert certifications[0]["date"] == "2023"


# ----------------------- Langues -----------------------

def test_les_niveaux_de_langue_suivent_le_cadre_europeen():
    langues = {li["language"]: li["fluency"] for li in ats.analyser_cv(CV_COMPLET)["languages"]}
    assert langues["Français"] == "C2"      # bilingue
    assert langues["Anglais"] == "C1"       # courant
    assert langues["Arabe"] == "C2"         # langue maternelle


def test_aucune_langue_n_est_inventee_faute_de_rubrique():
    """Un CV sans rubrique « Langues » ne doit en déclarer aucune.

    Le repli sur le document entier faisait apparaître des langues citées
    incidemment — dans un nom d'employeur ou d'école — que le candidat n'a
    jamais revendiquées, et que le recruteur ne retrouvait pas dans le CV.
    """
    cv = (
        "Aymen Benrbib\n"
        "Ingénieur en Systèmes d'Information\n\n"
        "EXPÉRIENCE PROFESSIONNELLE\n"
        "Stagiaire chez Banque Arabe pour le Développement — 2024\n\n"
        "COMPÉTENCES TECHNIQUES\n"
        "Langages : Python, SQL, Java, JavaScript / TypeScript, PHP\n"
    )
    assert ats.analyser_cv(cv)["languages"] == []


def test_chaque_langue_recoit_son_propre_niveau_sur_une_ligne_unique():
    """Une rubrique tenant en une ligne ne doit pas niveler les langues."""
    cv = "LANGUES : Français (courant), Anglais (B2), Arabe (langue maternelle)\n"
    langues = {li["language"]: li["fluency"] for li in ats.analyser_cv(cv)["languages"]}
    assert langues == {"Français": "C1", "Anglais": "B2", "Arabe": "C2"}


def test_le_telephone_est_releve_meme_colle_a_l_adresse_electronique():
    """« +212 6 37 72 13 28 aymen@exemple.ma » : un seul espace les sépare."""
    identite = ats.extraire_identite(
        "Aymen Benrbib\n+212 6 37 72 13 28 aymen@exemple.ma\nRabat, Maroc\n"
    )
    assert identite["phone"] == "+212 6 37 72 13 28"
    assert identite["email"] == "aymen@exemple.ma"


def test_le_masculin_maternel_vaut_le_feminin_maternelle():
    """« Arabe (Maternel) » : le CV accorde avec la langue, pas avec « langue »."""
    cv = "LANGUES\nArabe (Maternel) · Français (Courant) · Anglais (Courant)\n"
    langues = {li["language"]: li["fluency"] for li in ats.analyser_cv(cv)["languages"]}
    assert langues == {"Arabe": "C2", "Français": "C1", "Anglais": "C1"}


def test_une_rubrique_de_langages_de_programmation_n_est_pas_une_rubrique_de_langues():
    cv = "COMPÉTENCES\nLangages : Python, Java, Scala\n"
    assert ats.analyser_cv(cv)["languages"] == []


def test_les_langues_ne_figurent_pas_parmi_les_competences_techniques():
    profil = ats.analyser_cv(CV_COMPLET)
    assert "francais" not in profil["skills"]
    assert "anglais" not in profil["skills"]


# ----------------------- Adaptation au moteur de score -----------------------

def test_le_profil_est_converti_pour_le_moteur_de_score():
    profil = ats.vers_profil_scoring(ats.analyser_cv(CV_COMPLET))
    assert set(profil) == {
        "skills", "skills_etayees", "experience_years",
        "experience_determinee", "experience_months", "degree",
    }
    assert profil["degree"] == "Bac+5"
    assert profil["experience_years"] >= 5
    assert profil["experience_determinee"] is True
    assert "python" in profil["skills"]


# ----------------------- Ce que le document ne dit pas -----------------------
#
# Une rubrique vide et une rubrique absente portent deux informations
# differentes. Les confondre laisse le recruteur devant un profil muet, sans
# moyen de savoir si le candidat n'a rien declare ou si l'analyse n'a rien su
# lire — et c'est precisement la ou son jugement doit pouvoir s'exercer.

def test_les_rubriques_absentes_du_document_sont_signalees():
    cv = (
        "Aymen Benrbib\n"
        "aymen@exemple.ma\n\n"
        "FORMATION\n"
        "Diplôme d'Ingénieur — École des Sciences de l'Information, Rabat, 2024\n"
    )
    rubriques = ats.analyser_cv(cv)["rubriques"]
    assert rubriques["formation"]["presente"] is True
    assert rubriques["langues"]["presente"] is False
    assert rubriques["certifications"]["presente"] is False


def test_une_rubrique_annoncee_mais_illisible_se_distingue_d_une_rubrique_absente():
    """Présente sans élément : le document l'annonce, l'analyse n'a rien tiré."""
    cv = "CERTIFICATIONS\n—\n"
    rubriques = ats.analyser_cv(cv)["rubriques"]
    assert rubriques["certifications"]["presente"] is True
    assert rubriques["certifications"]["elements"] == 0


def test_un_stage_de_deux_mois_ne_s_ecrit_pas_zero_an():
    """L'arrondi à l'année efface ce qui distingue un débutant d'un néant."""
    cv = (
        "Aymen Benrbib\n\n"
        "EXPÉRIENCE PROFESSIONNELLE\n"
        "Stagiaire Développeur Fullstack Juillet 2025 – Août 2025\n"
        "Groupe OCP · Safi, Maroc\n"
    )
    profil = ats.analyser_cv(cv)
    assert profil["totalExperienceYears"] == 0
    assert profil["totalExperienceMonths"] >= 1
    assert profil["experienceDeterminee"] is True


def test_une_experience_illisible_ne_se_confond_pas_avec_une_absence_d_experience():
    """Zéro an est une mesure ; « non déterminée » est un aveu de lecture."""
    sans_rien = ats.analyser_cv("Aymen Benrbib\naymen@exemple.ma\n")
    assert sans_rien["experienceDeterminee"] is False

    avec_dates = ats.analyser_cv(CV_COMPLET)
    assert avec_dates["experienceDeterminee"] is True


# ----------------------- Preuve par l'expérience -----------------------

def test_une_competence_du_recit_est_etayee():
    """Une compétence décrite dans un poste occupé, et pas seulement listée.

    C'est la distinction sur laquelle repose la pondération par la preuve :
    une rubrique « Compétences » coûte une ligne à écrire, un poste décrit
    engage une période et un employeur.
    """
    profil = ats.analyser_cv(CV_COMPLET)
    assert "python" in profil["skillsEtayees"]


def test_une_competence_seulement_listee_n_est_pas_etayee():
    brut = """Salma Idrissi
salma@mail.ma

EXPÉRIENCE PROFESSIONNELLE

2020 - 2024 : Assistante administrative chez Groupe Amal
  Saisie des dossiers et classement des pièces.

FORMATION

2020 - Master en informatique

COMPÉTENCES

Python, Docker, Kubernetes
"""
    profil = ats.analyser_cv(brut)
    assert "python" in profil["skills"]
    assert "python" not in profil["skillsEtayees"]


def test_l_etayage_ne_retient_pas_une_langue():
    """Les langues sont écartées des compétences techniques, ici aussi."""
    profil = ats.analyser_cv(CV_COMPLET)
    assert all(c not in profil["skillsEtayees"] for c in ("francais", "anglais"))


# ----------------------- Robustesse -----------------------

def test_un_cv_sans_en_tete_reste_analysable():
    """Certains CV n'ont aucun titre de section : le repli doit fonctionner."""
    brut = """Karim Ouazzani
karim@mail.ma
2020 - 2024 : Développeur Python chez SoftHouse
Master en informatique, 2020
Python, Django, PostgreSQL
"""
    profil = ats.analyser_cv(brut)
    assert profil["basics"]["email"] == "karim@mail.ma"
    assert "python" in profil["skills"]
    assert profil["highestDegree"] == "Bac+5"
    assert len(profil["work"]) >= 1


def test_un_document_vide_ne_provoque_pas_d_erreur():
    profil = ats.analyser_cv("")
    assert profil["work"] == []
    assert profil["totalExperienceYears"] == 0
    assert profil["highestDegree"] is None


def test_le_recit_d_experience_est_lu_en_entier():
    """Toutes les compétences décrites dans les postes doivent être étayées.

    Le récit était assemblé avec « " ".join(summary) », alors que `summary`
    est une chaîne une fois l'entrée consolidée. Un `join` sur une chaîne
    insère un espace entre chaque caractère — « F l a s k » — et plus aucune
    compétence n'y était reconnaissable. Aucune erreur n'était levée : l'étayage
    tombait simplement à zéro pour tout le monde, ce qui ressemblait à un
    résultat plutôt qu'à une panne, et faussait la mesure qui en dépendait.
    """
    profil = ats.analyser_cv(CV_COMPLET)
    etayees = set(profil["skillsEtayees"])
    # Décrites dans un poste : « API REST avec Flask et PostgreSQL ».
    # Le manque est calculé avant le message : un ensemble litteral place dans
    # une chaine formatee y ouvre une accolade dans une accolade, que Python
    # accepte mais qu'aucun lecteur ne demele du premier coup.
    attendues = {"flask", "postgresql"}
    manquantes = attendues - etayees
    assert not manquantes, f"compétences décrites mais non étayées : {manquantes}"
    # Seulement listée en fin de curriculum : la distinction doit tenir.
    assert "docker" in profil["skills"] and "docker" not in etayees


# ----------------- Expérience adossée aux compétences du poste -----------------

def test_l_experience_pertinente_pondere_chaque_poste():
    """Huit ans passés à autre chose ne valent pas huit ans sur le sujet.

    Le moteur comptait l'ancienneté brute. Un profil du bon domaine mais au
    parcours hors sujet en tirait la totalité des points d'expérience — ce que
    le recruteur, lui, voit immédiatement.
    """
    profil = ats.analyser_cv(CV_COMPLET)
    annees, part = ats.experience_pertinente(profil, ["flask", "postgresql"])
    assert 0 < part <= 1
    assert annees < profil["totalExperienceYears"]


def test_un_parcours_hors_sujet_ne_compte_presque_pas():
    brut = """Mehdi Touzani
m@mail.ma

EXPÉRIENCE PROFESSIONNELLE

Janvier 2016 – Présent
Administrateur systèmes chez Assurances
  Exploitation de serveurs Windows et gestion des sauvegardes.

FORMATION

2015 - Master en réseaux

COMPÉTENCES

Docker, Kubernetes, Linux
"""
    profil = ats.analyser_cv(brut)
    _, part = ats.experience_pertinente(profil, ["docker", "kubernetes"])
    assert part == 0.0


def test_un_profil_junior_entierement_pertinent_garde_sa_part():
    """La mesure est une part, pas une durée : elle ne punit pas la jeunesse."""
    brut = """Salma Idrissi
s@mail.ma

EXPÉRIENCE PROFESSIONNELLE

Janvier 2023 – Décembre 2024
Développeuse chez SoftHouse
  Développement d'API REST avec Flask et PostgreSQL.

FORMATION

2022 - Master en informatique
"""
    profil = ats.analyser_cv(brut)
    _, part = ats.experience_pertinente(profil, ["flask", "postgresql"])
    assert part == 1.0


def test_sans_competence_exigee_la_part_est_entiere():
    """Une offre sans exigence ne doit pas annuler l'expérience du candidat."""
    profil = ats.analyser_cv(CV_COMPLET)
    annees, part = ats.experience_pertinente(profil, [])
    assert part == 1.0
    assert annees == profil["totalExperienceYears"]


def test_l_anciennete_annoncee_sert_de_repli_sans_dates():
    """Un CV sans dates n'est pas un CV sans expérience.

    Rien ne distinguait « ce candidat n'a aucune expérience » de « je n'ai pas
    su lire ses dates ». Comme l'ancienneté insuffisante est un critère
    éliminatoire, un candidat était écarté sur une information que son
    document contenait pourtant en toutes lettres.
    """
    brut = """Karim Ouazzani
Ingénieur logiciel, 6 ans d'expérience
k@mail.ma

EXPÉRIENCE PROFESSIONNELLE

Développeur backend chez SoftHouse
  Conception d'API REST avec Flask et PostgreSQL.

FORMATION
Master en informatique
"""
    profil = ats.analyser_cv(brut)
    assert profil["work"] == [] or all(not w.get("startDate") for w in profil["work"])
    assert profil["totalExperienceYears"] == 6


def test_les_dates_l_emportent_sur_l_anciennete_annoncee():
    """Une durée vérifiable prime sur une phrase, toujours."""
    brut = """Salma Idrissi
Développeuse, 15 ans d'expérience
s@mail.ma

EXPÉRIENCE PROFESSIONNELLE

Janvier 2022 – Décembre 2023
Développeuse chez SoftHouse
  Développement d'API REST.
"""
    profil = ats.analyser_cv(brut)
    assert profil["totalExperienceYears"] == 2


def test_un_nombre_aberrant_n_est_pas_pris_pour_une_anciennete():
    assert ats.annees_annoncees("Formation de 80 ans d'expérience cumulée") == 0
    assert ats.annees_annoncees("aucune mention") == 0


# ------------- Pratiquer une compétence, ou en être l'entourage -------------
#
# Les exemples ci-dessous sont écrits pour ces tests. Ils ne reprennent pas
# les cas du jeu retenu à l'écart : les mesurer ici reviendrait à les
# transformer en jeu d'entraînement, et ils perdraient toute valeur.

def _cv_avec(phrase):
    return f"""Test Personne
t@mail.ma

EXPÉRIENCE PROFESSIONNELLE

Janvier 2019 – Présent
Ingénieur chez Entreprise
  {phrase}

FORMATION

2018 - Master en informatique

COMPÉTENCES

Kubernetes, Docker
"""


def test_une_competence_pratiquee_est_etayee():
    profil = ats.analyser_cv(_cv_avec(
        "Mise en place d'un cluster Kubernetes et automatisation des déploiements."
    ))
    assert "kubernetes" in profil["skillsEtayees"]


def test_une_competence_seulement_encadree_n_est_pas_etayee():
    """Valider des rapports sur un cluster n'est pas exploiter un cluster.

    C'est la limite qu'un jeu de cas écrit par un tiers a révélée : le
    mécanisme voyait le mot, pas ce que la personne en avait fait.
    """
    profil = ats.analyser_cv(_cv_avec(
        "Validation documentaire des rapports de sécurité des clusters Kubernetes."
    ))
    assert "kubernetes" in profil["skills"]
    assert "kubernetes" not in profil["skillsEtayees"]


def test_le_doute_profite_au_candidat():
    """Ni terme de pratique ni terme d'entourage : on ne retire rien.

    Un curriculum sobre ne doit pas être traité comme un curriculum creux.
    """
    profil = ats.analyser_cv(_cv_avec("Kubernetes au quotidien sur le parc interne."))
    assert "kubernetes" in profil["skillsEtayees"]


def test_une_phrase_mixte_reste_creditee():
    """Coordonner *et* faire reste faire."""
    profil = ats.analyser_cv(_cv_avec(
        "Pilotage des comités et mise en place des clusters Kubernetes."
    ))
    assert "kubernetes" in profil["skillsEtayees"]
