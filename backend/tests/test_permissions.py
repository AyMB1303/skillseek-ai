"""Tests S1-07 / RG-02 : RBAC temps réel, révocation immédiate."""
from app.extensions import db
from app.models.role import Role

from .conftest import auth_header


def test_admin_can_list_users(client, admin_token):
    res = client.get("/api/users", headers=auth_header(admin_token))
    assert res.status_code == 200


def test_candidate_cannot_list_users(client):
    client.post(
        "/api/auth/register",
        json={
            "full_name": "Sara Candidate",
            "email": "sara@test.local",
            "password": "Secret@123",
        },
    )
    login = client.post(
        "/api/auth/login",
        json={"email": "sara@test.local", "password": "Secret@123"},
    )
    token = login.get_json()["access_token"]

    res = client.get("/api/users", headers=auth_header(token))
    assert res.status_code == 403


def test_revocation_is_immediate(app, client, admin_token):
    """RG-02 : retirer une permission agit SANS attendre l'expiration du JWT."""
    # 1. L'admin accede a /api/users avec son token
    assert client.get("/api/users", headers=auth_header(admin_token)).status_code == 200

    # 2. On retire manage_users au role admin (simule l'action d'un super-admin).
    #    Le commit expire le cache de session -> la prochaine lecture vient de la BDD.
    role = Role.query.filter_by(name="admin").first()
    role.permissions = [p for p in role.permissions if p.code != "manage_users"]
    db.session.commit()

    # 3. MEME token, requete suivante -> refusee immediatement
    res = client.get("/api/users", headers=auth_header(admin_token))
    assert res.status_code == 403
    assert "manage_users" in res.get_json()["missing_permissions"]
