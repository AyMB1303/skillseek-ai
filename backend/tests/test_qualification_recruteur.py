"""Faisceau d'indices sur une demande de compte recruteur.

Ces tests fixent une intention autant qu'un comportement : le module doit
*informer* l'administrateur sans jamais decider a sa place. Un test verifie
donc explicitement qu'une adresse Gmail n'est pas traitee comme une fraude,
car c'est precisement l'erreur que la conception cherche a eviter.
"""
from types import SimpleNamespace

from app.services.qualification_recruteur import (
    domaine_de,
    nom_entreprise_probable,
    qualifier,
)

from .conftest import auth_header


def _compte(email, statut="active", nom="Compte Test", entreprise=None, ident=1):
    """Objet minimal : le module ne lit que ces quatre attributs."""
    return SimpleNamespace(
        id=ident, email=email, status=statut, full_name=nom, company=entreprise
    )


# ------------------------- Fonctions elementaires -------------------------

def test_extraction_du_domaine():
    assert domaine_de("  Contact@BCSkills.MA ") == "bcskills.ma"
    assert domaine_de("adresse-sans-arobase") == ""
    assert domaine_de(None) == ""


def test_deduction_du_nom_d_entreprise():
    assert nom_entreprise_probable("bc-skills.ma") == "Bc Skills"
    assert nom_entreprise_probable("technova.com.br") == "Technova"
    # Une messagerie grand public ne designe aucune entreprise.
    assert nom_entreprise_probable("gmail.com") is None


# ---------------------------- Nature de l'adresse ----------------------------

def test_une_adresse_professionnelle_est_une_simple_information():
    q = qualifier(_compte("s.lamrani@bcskills.ma", statut="pending", ident=10), [])
    assert q["gravite"] == "information"
    assert q["nature"] == "Domaine professionnel"


def test_une_messagerie_grand_public_n_est_pas_une_alerte():
    """Le point central : Gmail signale une TPE, pas un fraudeur.

    Bloquer ces adresses ecarterait des recruteurs legitimes sans gener
    quiconque peut acheter un domaine. La qualification doit rester au
    niveau « vigilance » et le message doit le dire.
    """
    q = qualifier(_compte("patron.menuiserie@gmail.com", statut="pending", ident=11), [])
    assert q["gravite"] == "attention"
    assert q["nature"] == "Messagerie grand public"
    assert any("pas un motif de refus" in i for i in q["indices"])


def test_une_adresse_jetable_declenche_une_alerte():
    q = qualifier(_compte("x@yopmail.com", statut="pending", ident=12), [])
    assert q["gravite"] == "alerte"


# ------------------------ Anteriorite et imitation ------------------------

def test_les_comptes_deja_valides_sur_le_domaine_sont_comptes():
    connus = [
        _compte("s.lamrani@bcskills.ma", nom="Sarah Lamrani", ident=1),
        _compte("autre@bcskills.ma", statut="pending", nom="En Attente", ident=2),
    ]
    demande = _compte("nouveau@bcskills.ma", statut="pending", ident=99)
    q = qualifier(demande, connus)

    assert q["comptes_valides_sur_domaine"] == 1
    assert any("Sarah Lamrani" in i for i in q["indices"])


def test_un_domaine_imitant_un_domaine_valide_est_signale():
    """Typosquattage : un caractere d'ecart suffit a tromper une lecture rapide."""
    connus = [_compte("s.lamrani@bcskills.ma", nom="Sarah Lamrani", ident=1)]
    demande = _compte("contact@bcskils.ma", statut="pending", ident=99)
    q = qualifier(demande, connus)

    assert q["gravite"] == "alerte"
    assert any("ressemble fortement" in i for i in q["indices"])


def test_deux_domaines_distincts_ne_declenchent_aucune_ressemblance():
    connus = [_compte("m.bennani@technova.ma", ident=1)]
    demande = _compte("contact@bcskills.ma", statut="pending", ident=99)
    q = qualifier(demande, connus)

    assert q["gravite"] == "information"
    assert not any("ressemble" in i for i in q["indices"])


# --------------------------- Coherence declaree ---------------------------

def test_une_entreprise_incoherente_avec_le_domaine_est_relevee():
    demande = _compte(
        "contact@technova.ma", statut="pending", entreprise="BC Skills", ident=99
    )
    q = qualifier(demande, [])
    assert q["gravite"] == "attention"
    assert any("ne correspond pas" in i for i in q["indices"])


def test_la_comparaison_entreprise_domaine_reste_indulgente():
    """« BC Skills » et « bcskills.ma » designent la meme organisation."""
    demande = _compte(
        "contact@bcskills.ma", statut="pending", entreprise="BC Skills", ident=99
    )
    q = qualifier(demande, [])
    assert q["gravite"] == "information"


def test_une_entreprise_absente_ne_declenche_rien():
    """L'entreprise etant facultative, son absence ne doit rien peser."""
    demande = _compte("contact@bcskills.ma", statut="pending", ident=99)
    q = qualifier(demande, [])
    assert q["gravite"] == "information"


# ------------------------------- Integration -------------------------------

def test_les_demandes_en_attente_portent_leur_qualification(client, admin_token):
    client.post(
        "/api/auth/register",
        json={
            "full_name": "Nouveau Recruteur",
            "email": "contact@digitalfactory.ma",
            "password": "Passe@1234",
            "role": "recruiter",
        },
    )

    res = client.get("/api/users/pending", headers=auth_header(admin_token))
    assert res.status_code == 200

    demande = res.get_json()["users"][0]
    q = demande["qualification"]
    assert q["domaine"] == "digitalfactory.ma"
    assert q["gravite"] in ("information", "attention", "alerte")
    # La formulation engage la conception : les indices eclairent, ils ne
    # decident pas.
    assert "ne les remplacent" in q["lecture"] or "remplacent pas" in q["lecture"]
