"""Tests de la validation des recruteurs et de la suppression logique."""
from app.extensions import db
from app.models.job_offer import JobOffer
from app.models.notification import Notification
from app.models.role import Role
from app.models.user import User

from .conftest import auth_header


def _inscrire_recruteur(client, email="rec@test.local"):
    return client.post(
        "/api/auth/register",
        json={
            "full_name": "Rec Candidat",
            "email": email,
            "password": "Passe@1234",
            "role": "recruiter",
            "company": "TechCorp",
            "phone": "+212612345678",
        },
    )


# ------------------- Inscription et validation -------------------

def test_un_candidat_est_actif_immediatement(client):
    res = client.post(
        "/api/auth/register",
        json={"full_name": "Sara Alaoui", "email": "sara@test.local", "password": "Passe@1234"},
    )
    assert res.status_code == 201
    assert res.get_json()["user"]["status"] == "active"
    assert res.get_json()["pending"] is False


def test_un_recruteur_est_place_en_attente(app, client):
    res = _inscrire_recruteur(client)
    assert res.status_code == 201

    corps = res.get_json()
    assert corps["user"]["status"] == "pending"
    assert corps["user"]["company"] == "TechCorp"
    assert corps["pending"] is True


def test_l_entreprise_reste_facultative_pour_un_recruteur(client):
    """Exiger l'entreprise ajoutait une friction sans rien garantir.

    La declaration n'etait pas verifiable, et la reclamer ecartait surtout
    les tres petites structures. Le compte reste soumis a validation : c'est
    la, et non a l'inscription, que la verification a lieu.
    """
    res = client.post(
        "/api/auth/register",
        json={
            "full_name": "Sans Entreprise",
            "email": "x@test.local",
            "password": "Passe@1234",
            "role": "recruiter",
        },
    )
    assert res.status_code == 201
    corps = res.get_json()
    assert corps["user"]["status"] == "pending"
    assert corps["user"]["company"] is None


def test_impossible_de_s_inscrire_comme_administrateur(client):
    """Élévation de privilèges : le rôle admin n'est pas accessible publiquement."""
    res = client.post(
        "/api/auth/register",
        json={
            "full_name": "Faux Admin",
            "email": "faux@test.local",
            "password": "Passe@1234",
            "role": "admin",
        },
    )
    assert res.status_code == 400
    assert "role" in res.get_json()["errors"]


def test_un_recruteur_en_attente_ne_peut_pas_se_connecter(client):
    _inscrire_recruteur(client)
    res = client.post(
        "/api/auth/login", json={"email": "rec@test.local", "password": "Passe@1234"}
    )
    assert res.status_code == 403
    assert res.get_json()["status"] == "pending"


def test_les_administrateurs_sont_notifies_de_la_demande(app, client):
    _inscrire_recruteur(client)
    with app.app_context():
        notifs = Notification.query.filter_by(type="recruteur_en_attente").all()
        assert len(notifs) == 1
        assert "TechCorp" in notifs[0].message


def test_apres_validation_le_recruteur_peut_se_connecter(app, client, admin_token):
    _inscrire_recruteur(client)

    attente = client.get("/api/users/pending", headers=auth_header(admin_token))
    assert attente.get_json()["total"] == 1
    identifiant = attente.get_json()["users"][0]["id"]

    res = client.post(f"/api/users/{identifiant}/approve", headers=auth_header(admin_token))
    assert res.status_code == 200
    assert res.get_json()["user"]["status"] == "active"

    connexion = client.post(
        "/api/auth/login", json={"email": "rec@test.local", "password": "Passe@1234"}
    )
    assert connexion.status_code == 200

    with app.app_context():
        notif = Notification.query.filter_by(type="compte_approuve").first()
        assert notif is not None


def test_le_refus_transmet_le_motif_au_demandeur(app, client, admin_token):
    _inscrire_recruteur(client)
    identifiant = client.get(
        "/api/users/pending", headers=auth_header(admin_token)
    ).get_json()["users"][0]["id"]

    res = client.post(
        f"/api/users/{identifiant}/reject",
        headers=auth_header(admin_token),
        json={"reason": "Entreprise non vérifiable"},
    )
    assert res.status_code == 200

    connexion = client.post(
        "/api/auth/login", json={"email": "rec@test.local", "password": "Passe@1234"}
    )
    assert connexion.status_code == 403
    assert "Entreprise non vérifiable" in connexion.get_json()["error"]


# ------------------- Corbeille -------------------

def test_la_suppression_place_le_compte_en_corbeille(app, client, admin_token):
    client.post(
        "/api/auth/register",
        json={"full_name": "A Supprimer", "email": "sup@test.local", "password": "Passe@1234"},
    )
    with app.app_context():
        identifiant = User.query.filter_by(email="sup@test.local").first().id

    res = client.delete(f"/api/users/{identifiant}", headers=auth_header(admin_token))
    assert res.status_code == 200

    # Absent de la liste courante, present dans la corbeille
    liste = client.get("/api/users", headers=auth_header(admin_token)).get_json()["users"]
    assert "sup@test.local" not in [u["email"] for u in liste]

    corbeille = client.get("/api/trash", headers=auth_header(admin_token)).get_json()
    assert "sup@test.local" in [u["email"] for u in corbeille["users"]]


def test_un_compte_en_corbeille_ne_peut_plus_se_connecter(app, client, admin_token):
    client.post(
        "/api/auth/register",
        json={"full_name": "A Supprimer", "email": "sup@test.local", "password": "Passe@1234"},
    )
    with app.app_context():
        identifiant = User.query.filter_by(email="sup@test.local").first().id
    client.delete(f"/api/users/{identifiant}", headers=auth_header(admin_token))

    res = client.post(
        "/api/auth/login", json={"email": "sup@test.local", "password": "Passe@1234"}
    )
    assert res.status_code == 403


def test_restauration_depuis_la_corbeille(app, client, admin_token):
    client.post(
        "/api/auth/register",
        json={"full_name": "A Restaurer", "email": "res@test.local", "password": "Passe@1234"},
    )
    with app.app_context():
        identifiant = User.query.filter_by(email="res@test.local").first().id

    client.delete(f"/api/users/{identifiant}", headers=auth_header(admin_token))
    res = client.post(f"/api/users/{identifiant}/restore", headers=auth_header(admin_token))
    assert res.status_code == 200

    connexion = client.post(
        "/api/auth/login", json={"email": "res@test.local", "password": "Passe@1234"}
    )
    assert connexion.status_code == 200


def test_un_compte_administrateur_est_protege(app, client, admin_token):
    """Protection structurelle : la plateforme doit rester administrable."""
    with app.app_context():
        role = Role.query.filter_by(name="admin").first()
        autre = User(email="admin2@test.local", full_name="Admin Deux", role=role)
        autre.set_password("Passe@1234")
        db.session.add(autre)
        db.session.commit()
        identifiant = autre.id

    suppression = client.delete(f"/api/users/{identifiant}", headers=auth_header(admin_token))
    assert suppression.status_code == 400

    desactivation = client.patch(
        f"/api/users/{identifiant}", headers=auth_header(admin_token), json={"is_active": False}
    )
    assert desactivation.status_code == 400


def test_le_role_admin_conserve_ses_permissions_essentielles(app, client, admin_token):
    with app.app_context():
        role_id = Role.query.filter_by(name="admin").first().id

    res = client.put(
        f"/api/roles/{role_id}/permissions",
        headers=auth_header(admin_token),
        json={"permissions": []},
    )
    assert res.status_code == 400
    assert "administrateur" in res.get_json()["error"]


def test_purge_impossible_sur_une_offre_avec_candidatures(app, client, admin_token):
    """La traçabilité des candidatures interdit la suppression définitive."""
    from app.models.application import Application
    from app.models.permission import Permission

    with app.app_context():
        p = Permission.query.filter_by(code="manage_offers").first() or Permission(
            code="manage_offers", description=""
        )
        db.session.add(p)
        role_admin = Role.query.filter_by(name="admin").first()
        role_admin.permissions = list(role_admin.permissions) + [p]

        cand_role = Role.query.filter_by(name="candidate").first()
        cand = User(email="c@test.local", full_name="Cand Test", role=cand_role)
        cand.set_password("Passe@1234")
        db.session.add(cand)
        db.session.flush()

        offre = JobOffer(title="Poste", description="x" * 30, recruiter_id=cand.id)
        db.session.add(offre)
        db.session.flush()
        db.session.add(
            Application(cv_path="/tmp/x.pdf", candidate_id=cand.id, offer_id=offre.id)
        )
        db.session.commit()
        offre_id = offre.id

    client.delete(f"/api/offers/{offre_id}", headers=auth_header(admin_token))
    res = client.delete(f"/api/offers/{offre_id}/purge", headers=auth_header(admin_token))
    assert res.status_code == 400
    assert "candidatures" in res.get_json()["error"]
