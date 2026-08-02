"""Tests S2 : offres, tableau de bord et profil."""
from .conftest import auth_header


def _token_recruteur(app, client):
    """Crée un recruteur avec les permissions nécessaires et renvoie son token."""
    from app.extensions import db
    from app.models.permission import Permission
    from app.models.role import Role
    from app.models.user import User

    with app.app_context():
        codes = ["manage_offers", "view_applications", "manage_applications", "view_dashboard"]
        perms = []
        for c in codes:
            p = Permission.query.filter_by(code=c).first() or Permission(code=c, description="")
            db.session.add(p)
            perms.append(p)
        role = Role.query.filter_by(name="recruiter").first() or Role(name="recruiter")
        role.permissions = perms
        db.session.add(role)

        u = User(email="rec@test.local", full_name="Rec Test", role=role)
        u.set_password("Recrut@123")
        db.session.add(u)
        db.session.commit()

    res = client.post("/api/auth/login", json={"email": "rec@test.local", "password": "Recrut@123"})
    return res.get_json()["access_token"]


def test_recruteur_cree_une_offre(app, client):
    token = _token_recruteur(app, client)
    res = client.post(
        "/api/offers",
        headers=auth_header(token),
        json={
            "title": "Développeur Python",
            "description": "Poste backend au sein de l'équipe produit.",
            "required_skills": ["python", "sql"],
            "min_experience_years": 3,
            "min_degree": "Bac+3",
        },
    )
    assert res.status_code == 201
    offre = res.get_json()["offer"]
    assert offre["required_skills"] == ["python", "sql"]
    assert offre["min_experience_years"] == 3


def test_candidat_ne_peut_pas_creer_une_offre(app, client):
    client.post(
        "/api/auth/register",
        json={"full_name": "Sara C", "email": "sara@test.local", "password": "Secret@123"},
    )
    login = client.post(
        "/api/auth/login", json={"email": "sara@test.local", "password": "Secret@123"}
    )
    token = login.get_json()["access_token"]

    res = client.post(
        "/api/offers",
        headers=auth_header(token),
        json={"title": "Faux poste", "description": "x" * 30},
    )
    assert res.status_code == 403


def test_dashboard_renvoie_un_entonnoir_complet(app, client):
    token = _token_recruteur(app, client)
    res = client.get("/api/dashboard/stats?days=30", headers=auth_header(token))
    assert res.status_code == 200

    data = res.get_json()
    assert set(data["kpi"]) == {"recues", "preselectionnees", "entretiens", "recrutes"}
    assert len(data["funnel"]) == 4
    assert data["funnel"][0]["etape"] == "Candidatures reçues"


def test_modification_du_profil(client, admin_token):
    res = client.patch(
        "/api/profile", headers=auth_header(admin_token), json={"full_name": "Nouveau Nom"}
    )
    assert res.status_code == 200
    assert res.get_json()["user"]["full_name"] == "Nouveau Nom"


def test_changement_de_mot_de_passe_refuse_si_actuel_faux(client, admin_token):
    res = client.post(
        "/api/profile/password",
        headers=auth_header(admin_token),
        json={"current_password": "mauvais", "new_password": "Nouveau@123"},
    )
    assert res.status_code == 400
    assert "current_password" in res.get_json()["errors"]
