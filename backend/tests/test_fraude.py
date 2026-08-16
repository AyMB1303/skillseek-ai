"""Tests des contrôles d'anomalies sur les candidatures (S4-06).

Deux exigences sont éprouvées ici, et la seconde compte autant que la première :

  * le dispositif **relève** ce qu'il doit relever — nom sans rapport,
    document dupliqué, chronologie impossible, fichier porteur de code ;
  * il **ne relève pas** les variations légitimes. Un nom inversé, une
    particule omise, une initiale à la place du prénom sont le quotidien d'un
    service de recrutement. Un contrôle qui les signalerait noierait les vrais
    cas sous les faux, et le dispositif deviendrait inutilisable.
"""

import pytest

from app.services import fraude


# --------------------------------------------------------------------------
# Rapprochement des noms
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "compte, document",
    [
        ("Youssef Tazi", "YOUSSEF TAZI"),          # casse
        ("Youssef Tazi", "Tazi Youssef"),          # ordre inversé
        ("Yasmine El Amrani", "Yasmine Amrani"),   # particule omise
        ("Salma Idrissi", "Salma Idrissi-Benali"),  # nom composé
        ("Reda Alaoui", "R. Alaoui"),              # prénom abrégé
        ("Fatima Zahra Alaoui", "Fatima Alaoui"),  # prénom composé abrégé
    ],
)
def test_les_variations_legitimes_ne_sont_pas_signalees(compte, document):
    assert fraude.concordance_des_noms(compte, document) >= 0.67


def test_un_nom_sans_rapport_est_detecte():
    assert fraude.concordance_des_noms("Bilal Sbai", "Youssef Tazi") == 0.0


def test_la_comparaison_est_impossible_sans_nom_extrait():
    """Un document illisible ne doit pas produire de soupçon."""
    assert fraude.concordance_des_noms("Bilal Sbai", None) is None


# --------------------------------------------------------------------------
# Empreinte du document
# --------------------------------------------------------------------------

def test_l_empreinte_ignore_la_mise_en_forme():
    """Deux exports du même CV diffèrent par leurs espaces, pas par leur sens."""
    a = fraude.empreinte_texte("Youssef  TAZI\n\nDéveloppeur   backend")
    b = fraude.empreinte_texte("youssef tazi développeur backend")
    assert a == b


def test_l_empreinte_distingue_deux_documents():
    assert fraude.empreinte_texte("Développeur backend") != fraude.empreinte_texte(
        "Développeuse frontend"
    )


# --------------------------------------------------------------------------
# Cohérence du parcours
# --------------------------------------------------------------------------

def test_une_date_future_est_signalee():
    profil = {"work": [{"startDate": "2031-01"}], "education": []}
    trouves = fraude._controler_chronologie(profil)
    assert any("2031" in s["message"] for s in trouves)


def test_une_experience_superieure_a_la_duree_du_parcours_est_signalee():
    profil = {
        "work": [{"startDate": "2022-01"}],
        "education": [],
        "totalExperienceYears": 25,
    }
    trouves = fraude._controler_chronologie(profil)
    assert any(s["type"] == "chronologie_incoherente" for s in trouves)


def test_un_parcours_coherent_ne_produit_aucun_signalement():
    profil = {
        "work": [{"startDate": "2019-09"}],
        "education": [{"endDate": "2019"}],
        "totalExperienceYears": 6,
    }
    assert fraude._controler_chronologie(profil) == []


def test_un_stage_avant_le_diplome_reste_tolere():
    """Alternance et emploi étudiant précèdent normalement le diplôme."""
    profil = {
        "work": [{"startDate": "2019-01"}],
        "education": [{"endDate": "2020"}],
        "totalExperienceYears": 7,
    }
    assert fraude._controler_chronologie(profil) == []


# --------------------------------------------------------------------------
# Nature du fichier
# --------------------------------------------------------------------------

def test_un_pdf_porteur_de_code_declenche_une_alerte(tmp_path):
    piege = tmp_path / "cv.pdf"
    piege.write_bytes(b"%PDF-1.7\n/OpenAction << /S /JavaScript /JS (app.alert) >>\n")

    trouves = fraude._controler_fichier(str(piege))

    assert any(s["type"] == "fichier_suspect" for s in trouves)
    assert any(s["severite"] == "alerte" for s in trouves)


def test_une_extension_mensongere_est_detectee(tmp_path):
    """Un exécutable renommé en .pdf n'a pas la signature d'un PDF."""
    faux = tmp_path / "cv.pdf"
    faux.write_bytes(b"MZ\x90\x00" + b"\x00" * 100)

    trouves = fraude._controler_fichier(str(faux))

    assert any("signature" in s["message"] for s in trouves)


def test_un_pdf_ordinaire_ne_produit_aucun_signalement(tmp_path):
    normal = tmp_path / "cv.pdf"
    normal.write_bytes(b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n")

    assert fraude._controler_fichier(str(normal)) == []


def test_un_fichier_absent_ne_fait_pas_echouer_le_controle():
    assert fraude._controler_fichier("/chemin/qui/n/existe/pas.pdf") == []


# --------------------------------------------------------------------------
# Indices de rédaction assistée
# --------------------------------------------------------------------------

def test_un_document_concret_ne_declenche_pas_l_indice_de_redaction():
    """Des chiffres et des faits suffisent à écarter le soupçon."""
    texte = (
        "Développeur backend. J'ai migré 12 services vers Kubernetes, réduit de "
        "40% le temps de réponse. Encadrement de 3 développeurs. Budget de 250k€ "
        "sur le projet Atlas. Passage de 15 à 60 clients en deux ans."
    )
    assert fraude._controler_redaction(texte, None) == []


def test_l_indice_de_redaction_reste_une_information():
    """Ce contrôle ne doit jamais produire une alerte : il se trompe trop."""
    texte = " ".join(
        [
            "Force de proposition et rigoureux et organise dans mon travail.",
            "Excellente capacite d'analyse et sens du detail reconnu.",
            "Passionne par les technologies et esprit d'equipe developpe.",
            "Solide experience acquise dans un environnement stimulant ici.",
            "Capacite d'adaptation forte et excellent relationnel avec tous.",
            "Je recherche aujourd'hui un environnement stimulant nouveau.",
            "Mon parcours temoigne d'une progression constante et reguliere.",
            "Je saurai apporter une contribution utile a votre organisation.",
        ]
    )
    trouves = fraude._controler_redaction(texte, None)
    assert all(s["severite"] == "information" for s in trouves)


# --------------------------------------------------------------------------
# Gravité d'ensemble
# --------------------------------------------------------------------------

def test_la_severite_maximale_prime():
    signalements = [
        {"severite": "information"},
        {"severite": "alerte"},
        {"severite": "attention"},
    ]
    assert fraude.severite_maximale(signalements) == "alerte"


def test_aucune_severite_sans_signalement():
    assert fraude.severite_maximale([]) is None
