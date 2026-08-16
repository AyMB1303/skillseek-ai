"""Domaine « administration » de l'assistant.

Le test le plus important de ce fichier n'est pas fonctionnel mais
architectural : il vérifie que l'assistant d'un administrateur ne restitue pas
le contenu des candidatures. Le rôle administrateur ne détient pas
`view_applications` ; si la conversation contournait cette restriction, le
modèle de droits ne vaudrait plus rien.
"""
from app.extensions import db
from app.models.application import Application
from app.models.job_offer import JobOffer
from app.models.permission import Permission
from app.models.role import Role
from app.models.signalement import Signalement
from app.models.user import User
from app.services.rag import administration, index

from .conftest import auth_header


def _preparer(app):
    """Un recruteur, une offre, une candidature, une demande et un signalement."""
    with app.app_context():
        chat = Permission.query.filter_by(code="use_chatbot").first() or Permission(
            code="use_chatbot", description=""
        )
        db.session.add(chat)

        role_admin = Role.query.filter_by(name="admin").first()
        role_admin.permissions = list(role_admin.permissions) + [chat]
        role_rec = Role.query.filter_by(name="recruiter").first()
        role_cand = Role.query.filter_by(name="candidate").first()

        rec = User(email="rec@test.local", full_name="Rec Test", role=role_rec)
        rec.set_password("Passe@1234")
        # Demande en attente : c'est elle que l'administrateur doit voir.
        attente = User(
            email="contact@digitalfactory.ma", full_name="Ines Cherkaoui",
            role=role_rec, status="pending",
        )
        attente.set_password("Passe@1234")
        candidat = User(
            email="tazi@test.local", full_name="Youssef Tazi", role=role_cand
        )
        candidat.set_password("Passe@1234")
        db.session.add_all([rec, attente, candidat])
        db.session.flush()

        offre = JobOffer(
            title="Développeur Python", description="API REST.",
            required_skills=["python"], recruiter_id=rec.id,
        )
        db.session.add(offre)
        db.session.flush()

        candidature = Application(
            cv_path="/tmp/x.pdf", candidate_id=candidat.id,
            offer_id=offre.id, score=87, status="received",
        )
        db.session.add(candidature)
        db.session.flush()

        db.session.add(Signalement(
            application_id=candidature.id, type="identite_divergente",
            severite="alerte", message="Le nom du document diffère de celui du compte.",
            statut="nouveau", origine="automatique",
        ))
        db.session.commit()
        index.invalider()


def _token_admin(client):
    res = client.post(
        "/api/auth/login",
        json={"email": "admin@test.local", "password": "Admin@1234"},
    )
    return res.get_json()["access_token"]


# ------------------------------ Faits chiffrés ------------------------------

def test_les_faits_couvrent_la_gouvernance(app):
    _preparer(app)
    with app.app_context():
        f = administration.faits()

    assert f["comptes_en_attente"] == 1
    assert f["signalements_a_traiter"] == 1
    assert f["signalements_alertes"] == 1
    assert f["offres_publiees"] == 1
    assert f["par_role"]["recruiter"]["attente"] == 1
    assert f["par_role"]["candidate"]["actifs"] == 1


def test_le_contexte_chiffre_est_lisible(app):
    _preparer(app)
    with app.app_context():
        texte = administration.texte_faits(administration.faits())
    assert "FAITS VÉRIFIÉS" in texte
    assert "en attente de validation" in texte


# --------------------- Étanchéité vis-à-vis des candidatures ---------------------

def test_la_base_administration_ignore_les_candidatures(app):
    """La propriété qui justifie l'existence d'un domaine séparé.

    Un administrateur ne détient pas `view_applications`. Sa base de
    connaissance ne doit donc contenir ni offre ni candidature, et le nom d'un
    candidat ne doit apparaître nulle part hors du signalement qu'il a le droit
    de traiter.
    """
    _preparer(app)
    with app.app_context():
        docs = administration.documents()

    types = {d.type for d in docs}
    assert "candidature" not in types
    assert "offre" not in types
    assert types <= {"aide", "compte", "signalement", "role"}

    # Le score d'une candidature ne doit apparaître dans aucun document.
    assert not any("87" in d.texte for d in docs)


def test_le_signalement_reste_visible_car_le_droit_existe(app):
    """`view_signalements` est détenu : le dossier signalé doit être identifiable."""
    _preparer(app)
    with app.app_context():
        docs = administration.documents()
    signalements = [d for d in docs if d.type == "signalement"]
    assert len(signalements) == 1
    assert "Youssef Tazi" in signalements[0].texte


def test_la_demande_en_attente_porte_ses_indices(app):
    _preparer(app)
    with app.app_context():
        docs = administration.documents()
    comptes = [d for d in docs if d.type == "compte"]
    assert len(comptes) == 1
    assert "Ines Cherkaoui" in comptes[0].texte
    assert "Domaine professionnel" in comptes[0].texte


# ------------------------------- Rédaction -------------------------------

def test_une_salutation_annonce_ce_qui_attend_une_decision(app):
    _preparer(app)
    with app.app_context():
        f = administration.faits()
        texte = administration.composer("bonjour", [], f)
    assert "demande" in texte.lower()
    assert "signalement" in texte.lower()


def test_la_question_sur_les_validations_est_reconnue(app):
    _preparer(app)
    with app.app_context():
        f = administration.faits()
        assert administration.intention(
            "Combien de comptes attendent une validation ?"
        ) == "validation"
        texte = administration.composer(
            "Combien de comptes attendent une validation ?", [], f
        )
    assert "1 demande" in texte
    # La formulation doit rappeler que les indices n'emportent pas la décision.
    assert "motif de refus" in texte


def test_le_tableau_des_demandes_liste_le_domaine(app):
    _preparer(app)
    with app.app_context():
        t = administration.tableau("Quelles demandes attendent une validation ?")
    assert t["colonnes"][0] == "Demandeur"
    assert t["lignes"][0][1] == "contact@digitalfactory.ma"


def test_le_tableau_des_signalements_ordonne_par_gravite(app):
    _preparer(app)
    with app.app_context():
        t = administration.tableau("Quels signalements restent à traiter ?")
    assert t["lignes"][0][0] == "Alerte"


def test_une_question_hors_perimetre_ne_reste_pas_sans_reponse(app):
    _preparer(app)
    with app.app_context():
        f = administration.faits()
        texte = administration.composer("quelle est la couleur du ciel", [], f)
    assert "je n'ai pas su" in texte.lower()


# ------------------------------ Bout en bout ------------------------------

def test_l_administrateur_interroge_le_domaine_administration(app, client):
    _preparer(app)
    token = _token_admin(client)

    res = client.get("/api/assistant/status", headers=auth_header(token))
    assert res.status_code == 200
    assert res.get_json()["domaine"] == "administration"

    res = client.post(
        "/api/assistant/ask",
        headers=auth_header(token),
        json={"question": "Combien de comptes attendent une validation ?"},
    )
    assert res.status_code == 200
    corps = res.get_json()
    assert corps["domaine"] == "administration"
    assert corps["lien"]["href"] == "/admin/recruteurs"
    assert corps["tableau"]["lignes"]
