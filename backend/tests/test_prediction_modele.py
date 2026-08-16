"""Tests du modèle appris tel qu'il est utilisé en production.

L'exigence essentielle n'est pas la qualité des prédictions — elle est mesurée
par les protocoles d'évaluation — mais la **robustesse** : aucune analyse de
candidature ne doit échouer parce que le modèle est absent, périmé ou
illisible. Ces tests vérifient chaque mode de défaillance.
"""
from pathlib import Path

import pytest

from app.services.ml import prediction


class OffreFictive:
    def __init__(self):
        self.title = "Développeur Python"
        self.required_skills = ["python", "sql"]
        self.preferred_skills = ["docker"]
        self.min_experience_years = 2
        self.min_degree = "Bac+3"


CV = """Amine Tazi
amine.tazi@example.com | 06 12 34 56 78

Expériences professionnelles
2020 - 2024 : Développeur Python chez Atlas Digital
  Conception d'API REST, bases PostgreSQL, déploiement Docker.

Formation
2020 : Master en génie logiciel, université de Rabat

Compétences
Python, SQL, Docker, Git

Langues
Français (C2), Anglais (B2)
"""


@pytest.fixture(autouse=True)
def _memoire_propre():
    """Chaque test repart d'un chargement neuf."""
    prediction.recharger()
    yield
    prediction.recharger()


def test_modele_absent_ne_bloque_pas_l_analyse(monkeypatch):
    monkeypatch.setattr(prediction, "CHEMIN_MODELE", Path("/inexistant/modele.joblib"))

    assert prediction.disponible() is False
    assert prediction.probabilite(CV, "offre python", offre=OffreFictive()) is None


def test_fichier_illisible_est_ignore(monkeypatch, tmp_path):
    corrompu = tmp_path / "correspondance.joblib"
    corrompu.write_bytes(b"ceci n'est pas un modele")
    monkeypatch.setattr(prediction, "CHEMIN_MODELE", corrompu)

    assert prediction.disponible() is False


def test_modele_entraine_sur_d_autres_caracteristiques_est_refuse(monkeypatch, tmp_path):
    """Des colonnes décalées produiraient des prédictions arbitraires."""
    joblib = pytest.importorskip("joblib")

    chemin = tmp_path / "correspondance.joblib"
    joblib.dump(
        {
            "modele": object(),
            "caracteristiques": ["une_seule_caracteristique"],
            "classes": ["Ne convient pas", "Convient"],
            "classe_positive": "Convient",
            "version": "obsolete",
        },
        chemin,
    )
    monkeypatch.setattr(prediction, "CHEMIN_MODELE", chemin)

    assert prediction.disponible() is False


def test_exigences_reprises_de_l_offre_structuree():
    exigences = prediction.exigences_depuis_offre(OffreFictive())

    # Les competences souhaitees comptent aussi : a l'entrainement, les
    # exigences sont extraites du texte de l'annonce sans distinction.
    assert exigences["competences"] == {"python", "sql", "docker"}
    assert exigences["experience"] == 2
    assert exigences["diplome"] == "Bac+3"


def test_probabilite_valide_lorsque_le_modele_est_present():
    if not prediction.disponible():
        pytest.skip("Aucun modèle entraîné : lancer entrainer_modele.py")

    valeur = prediction.probabilite(
        CV, "Développeur Python, 2 ans d'expérience", offre=OffreFictive()
    )

    assert valeur is not None
    assert 0.0 <= valeur <= 1.0
