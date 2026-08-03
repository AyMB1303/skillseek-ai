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
    assert ats._identifier_section("EXPÉRIENCE PROFESSIONNELLE") == "experience"


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


def test_les_langues_ne_figurent_pas_parmi_les_competences_techniques():
    profil = ats.analyser_cv(CV_COMPLET)
    assert "francais" not in profil["skills"]
    assert "anglais" not in profil["skills"]


# ----------------------- Adaptation au moteur de score -----------------------

def test_le_profil_est_converti_pour_le_moteur_de_score():
    profil = ats.vers_profil_scoring(ats.analyser_cv(CV_COMPLET))
    assert set(profil) == {"skills", "experience_years", "degree"}
    assert profil["degree"] == "Bac+5"
    assert profil["experience_years"] >= 5
    assert "python" in profil["skills"]


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
