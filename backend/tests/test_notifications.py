"""Tests des notifications : bon destinataire selon l'événement et le rôle."""
from app.extensions import db
from app.models.notification import Notification
from app.models.role import Role
from app.models.user import User

from .conftest import auth_header


def _creer_utilisateur(app, email, nom_role, mot_de_passe="Passe@1234"):
    with app.app_context():
        role = Role.query.filter_by(name=nom_role).first()
        if role is None:
            role = Role(name=nom_role)
            db.session.add(role)
        u = User(email=email, full_name=f"Test {nom_role}", role=role)
        u.set_password(mot_de_passe)
        db.session.add(u)
        db.session.commit()
        return u.id


def test_creation_de_compte_notifie_les_autres_admins(app, client, admin_token):
    """Un second administrateur doit être informé de la création d'un compte."""
    autre_admin_id = _creer_utilisateur(app, "admin2@test.local", "admin")

    res = client.post(
        "/api/users",
        headers=auth_header(admin_token),
        json={
            "email": "nouveau@test.local",
            "password": "Passe@1234",
            "full_name": "Nouveau Compte",
            "role": "candidate",
        },
    )
    assert res.status_code == 201

    with app.app_context():
        notifs = Notification.query.filter_by(user_id=autre_admin_id).all()
        assert len(notifs) == 1
        assert notifs[0].type == "compte_cree"
        assert "Nouveau Compte" in notifs[0].message


def test_auteur_de_la_creation_ne_se_notifie_pas_lui_meme(app, client, admin_token):
    res = client.post(
        "/api/users",
        headers=auth_header(admin_token),
        json={
            "email": "x@test.local",
            "password": "Passe@1234",
            "full_name": "Compte X",
            "role": "candidate",
        },
    )
    assert res.status_code == 201

    with app.app_context():
        moi = User.query.filter_by(email="admin@test.local").first()
        assert Notification.query.filter_by(user_id=moi.id).count() == 0


def test_le_candidat_est_notifie_du_changement_de_statut(app, client, admin_token):
    """Le candidat reçoit une notification lisible, sans mention du score."""
    from app.models.application import Application
    from app.models.job_offer import JobOffer
    from app.models.permission import Permission

    with app.app_context():
        # Recruteur autorise a changer les statuts
        p = Permission.query.filter_by(code="manage_applications").first()
        if p is None:
            p = Permission(code="manage_applications", description="")
            db.session.add(p)
        role_rec = Role.query.filter_by(name="recruiter").first() or Role(name="recruiter")
        role_rec.permissions = [p]
        db.session.add(role_rec)

        role_cand = Role.query.filter_by(name="candidate").first()

        rec = User(email="rec2@test.local", full_name="Rec Deux", role=role_rec)
        rec.set_password("Passe@1234")
        cand = User(email="cand@test.local", full_name="Cand Test", role=role_cand)
        cand.set_password("Passe@1234")
        db.session.add_all([rec, cand])
        db.session.flush()

        offre = JobOffer(title="Poste Test", description="x" * 30, recruiter_id=rec.id)
        db.session.add(offre)
        db.session.flush()

        candidature = Application(cv_path="/tmp/x.pdf", candidate_id=cand.id, offer_id=offre.id)
        db.session.add(candidature)
        db.session.commit()
        cand_id, app_id = cand.id, candidature.id

    login = client.post(
        "/api/auth/login", json={"email": "rec2@test.local", "password": "Passe@1234"}
    )
    token = login.get_json()["access_token"]

    res = client.patch(
        f"/api/applications/{app_id}/status",
        headers=auth_header(token),
        json={"status": "interview"},
    )
    assert res.status_code == 200

    with app.app_context():
        notifs = Notification.query.filter_by(user_id=cand_id).all()
        assert len(notifs) == 1
        assert notifs[0].type == "statut_change"
        assert "entretien" in notifs[0].message.lower()
        assert notifs[0].link == "/mes-candidatures"


def test_chacun_ne_voit_que_ses_propres_notifications(app, client, admin_token):
    """Cloisonnement : l'API ne renvoie jamais les notifications d'autrui."""
    autre_id = _creer_utilisateur(app, "autre@test.local", "candidate")
    with app.app_context():
        db.session.add(
            Notification(user_id=autre_id, type="statut_change", message="Privé", link="/x")
        )
        db.session.commit()

    res = client.get("/api/notifications", headers=auth_header(admin_token))
    assert res.status_code == 200
    messages = [n["message"] for n in res.get_json()["notifications"]]
    assert "Privé" not in messages


def test_marquer_toutes_lues(app, client, admin_token):
    with app.app_context():
        moi = User.query.filter_by(email="admin@test.local").first()
        db.session.add_all(
            [
                Notification(user_id=moi.id, type="compte_cree", message="A"),
                Notification(user_id=moi.id, type="compte_cree", message="B"),
            ]
        )
        db.session.commit()

    avant = client.get("/api/notifications", headers=auth_header(admin_token))
    assert avant.get_json()["non_lues"] == 2

    res = client.post("/api/notifications/read-all", headers=auth_header(admin_token))
    assert res.status_code == 200
    assert res.get_json()["non_lues"] == 0
