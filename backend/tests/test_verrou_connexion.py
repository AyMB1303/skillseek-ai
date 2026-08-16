"""Verrou temporaire après échecs de connexion répétés.

Le compteur d'échecs existait déjà, mais il n'empêchait rien : il prévenait le
titulaire pendant qu'un essai systématique se poursuivait. Le verrou ferme
cette porte, sans prétendre régler le sujet — il porte sur le compte visé, ce
qui permet en retour de gêner volontairement quelqu'un. D'où une durée courte
et une notification adressée à l'intéressé.
"""
from datetime import datetime, timedelta, timezone

from app.extensions import db
from app.models.role import Role
from app.models.user import User

MOT_DE_PASSE = "Passe@1234"


def _compte(app, email="cible@test.local"):
    with app.app_context():
        role = Role.query.filter_by(name="candidate").first()
        u = User(email=email, full_name="Compte Cible", role=role)
        u.set_password(MOT_DE_PASSE)
        db.session.add(u)
        db.session.commit()
        return u.id


def _tenter(client, email, mot_de_passe):
    return client.post("/api/auth/login", json={"email": email, "password": mot_de_passe})


def test_le_compte_se_verrouille_apres_le_seuil(app, client):
    _compte(app)
    seuil = app.config["SEUIL_VERROU_CONNEXION"]

    for _ in range(seuil):
        assert _tenter(client, "cible@test.local", "faux").status_code == 401

    # Le mot de passe devient sans effet : c'est le point du verrou.
    res = _tenter(client, "cible@test.local", MOT_DE_PASSE)
    assert res.status_code == 429
    assert "retry_after_minutes" in res.get_json()


def test_le_verrou_precede_la_verification_du_mot_de_passe(app, client):
    """Sinon l'essai continuerait à distinguer le bon du mauvais mot de passe."""
    _compte(app)
    for _ in range(app.config["SEUIL_VERROU_CONNEXION"]):
        _tenter(client, "cible@test.local", "faux")

    juste = _tenter(client, "cible@test.local", MOT_DE_PASSE)
    faux = _tenter(client, "cible@test.local", "encore-faux")
    assert juste.status_code == faux.status_code == 429


def test_le_verrou_expire(app, client):
    identifiant = _compte(app)
    for _ in range(app.config["SEUIL_VERROU_CONNEXION"]):
        _tenter(client, "cible@test.local", "faux")

    with app.app_context():
        u = db.session.get(User, identifiant)
        u.locked_until = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.session.commit()

    assert _tenter(client, "cible@test.local", MOT_DE_PASSE).status_code == 200


def test_une_connexion_reussie_efface_la_serie(app, client):
    identifiant = _compte(app)
    _tenter(client, "cible@test.local", "faux")
    assert _tenter(client, "cible@test.local", MOT_DE_PASSE).status_code == 200

    with app.app_context():
        u = db.session.get(User, identifiant)
        assert u.failed_logins == 0
        assert u.locked_until is None


def test_une_adresse_inconnue_ne_revele_rien(app, client):
    """Le message doit rester identique, verrou ou pas."""
    _compte(app)
    inconnu = _tenter(client, "personne@test.local", "faux")
    connu = _tenter(client, "cible@test.local", "faux")
    assert inconnu.status_code == connu.status_code == 401
    assert inconnu.get_json()["error"] == connu.get_json()["error"]
