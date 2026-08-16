import pytest

from app import create_app
from app.extensions import db as _db
from app.models.permission import Permission
from app.models.role import Role
from app.models.user import User


@pytest.fixture()
def app():
    app = create_app("testing")
    with app.app_context():
        _db.create_all()

        # Donnees minimales, calquees sur une base initialisee par `flask seed` :
        # les trois roles doivent exister pour que l'inscription fonctionne.
        p_users = Permission(code="manage_users", description="")
        p_roles = Permission(code="manage_roles", description="")
        admin_role = Role(name="admin", permissions=[p_users, p_roles])
        recruiter_role = Role(name="recruiter", permissions=[])
        candidate_role = Role(name="candidate", permissions=[])
        _db.session.add_all(
            [p_users, p_roles, admin_role, recruiter_role, candidate_role]
        )

        admin = User(email="admin@test.local", full_name="Admin Test", role=admin_role)
        admin.set_password("Admin@1234")
        _db.session.add(admin)
        _db.session.commit()

        yield app

        _db.session.remove()
        _db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def admin_token(client):
    res = client.post(
        "/api/auth/login",
        json={"email": "admin@test.local", "password": "Admin@1234"},
    )
    return res.get_json()["access_token"]


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}
