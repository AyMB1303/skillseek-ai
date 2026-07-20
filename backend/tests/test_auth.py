"""Tests S1-06 : inscription, connexion, refresh, logout."""
from .conftest import auth_header


def test_health(client):
    assert client.get("/api/health").status_code == 200


def test_register_creates_candidate(client):
    res = client.post(
        "/api/auth/register",
        json={
            "full_name": "Sara Candidate",
            "email": "sara@test.local",
            "password": "Secret@123",
        },
    )
    assert res.status_code == 201
    assert res.get_json()["user"]["role"] == "candidate"


def test_register_rejects_weak_password(client):
    res = client.post(
        "/api/auth/register",
        json={"full_name": "X Y Z", "email": "x@test.local", "password": "abc"},
    )
    assert res.status_code == 400
    assert "password" in res.get_json()["errors"]


def test_login_wrong_password(client):
    res = client.post(
        "/api/auth/login",
        json={"email": "admin@test.local", "password": "wrong"},
    )
    assert res.status_code == 401


def test_login_and_me(client, admin_token):
    res = client.get("/api/auth/me", headers=auth_header(admin_token))
    assert res.status_code == 200
    assert res.get_json()["user"]["email"] == "admin@test.local"


def test_logout_revokes_token(client, admin_token):
    # Logout -> le token part en blacklist
    res = client.post("/api/auth/logout", headers=auth_header(admin_token))
    assert res.status_code == 200

    # Le meme token est refuse ensuite
    res = client.get("/api/auth/me", headers=auth_header(admin_token))
    assert res.status_code == 401
