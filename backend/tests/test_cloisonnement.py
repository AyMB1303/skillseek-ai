"""Cloisonnement entre recruteurs : le périmètre, et non le rôle.

Les permissions répondent à « peut-il consulter des candidatures ? ». Elles ne
répondent pas à « celle-ci ? ». Deux recruteurs détiennent exactement les mêmes
droits ; ce qui les sépare est le périmètre de leurs offres.

Chaque test vise une route où cette distinction avait été omise. Ils sont
écrits du point de vue de l'attaquant — le recruteur B demande explicitement
une ressource du recruteur A — parce qu'un test qui se contente de vérifier
que A voit ses propres données passerait tout aussi bien sans le correctif.
"""
from app.extensions import db
from app.models.application import Application
from app.models.job_offer import JobOffer
from app.models.permission import Permission
from app.models.role import Role
from app.models.user import User

from .conftest import auth_header

MOT_DE_PASSE = "Passe@1234"


def _preparer(app):
    """Deux recruteurs, une offre et une candidature chacun."""
    with app.app_context():
        role_rec = Role.query.filter_by(name="recruiter").first()
        role_rec.permissions = [
            Permission.query.filter_by(code=code).first()
            or Permission(code=code, description="")
            for code in ("manage_offers", "view_applications",
                         "manage_applications", "view_dashboard")
        ]
        db.session.add_all(role_rec.permissions)
        role_cand = Role.query.filter_by(name="candidate").first()

        identifiants = {}
        for cle, nom in (("a", "Recruteur A"), ("b", "Recruteur B")):
            rec = User(email=f"{cle}@test.local", full_name=nom, role=role_rec)
            rec.set_password(MOT_DE_PASSE)
            db.session.add(rec)
            db.session.flush()

            offre = JobOffer(
                title=f"Poste {cle.upper()}", description="Description.",
                required_skills=["python"], recruiter_id=rec.id,
            )
            db.session.add(offre)
            db.session.flush()

            candidat = User(
                email=f"cand-{cle}@test.local", full_name=f"Candidat {cle.upper()}",
                role=role_cand,
            )
            candidat.set_password(MOT_DE_PASSE)
            db.session.add(candidat)
            db.session.flush()

            candidature = Application(
                cv_path="/tmp/cv.pdf", candidate_id=candidat.id,
                offer_id=offre.id, score=80, status="received",
            )
            db.session.add(candidature)
            db.session.flush()
            identifiants[cle] = {
                "offre": offre.id, "candidature": candidature.id, "recruteur": rec.id
            }

        db.session.commit()
        return identifiants


def _token(client, cle):
    res = client.post(
        "/api/auth/login",
        json={"email": f"{cle}@test.local", "password": MOT_DE_PASSE},
    )
    return res.get_json()["access_token"]


# --------------------------------- Lecture ---------------------------------

def test_la_liste_des_candidatures_est_limitee_au_perimetre(app, client):
    """Le point aveugle le plus courant : la liste précède la route unitaire."""
    ids = _preparer(app)
    res = client.get("/api/applications", headers=auth_header(_token(client, "a")))
    assert res.status_code == 200

    renvoyees = {c["id"] for c in res.get_json()["applications"]}
    assert renvoyees == {ids["a"]["candidature"]}
    assert ids["b"]["candidature"] not in renvoyees


def test_le_filtre_par_offre_ne_permet_pas_de_franchir_le_perimetre(app, client):
    """Un `offer_id` choisi dans l'URL ne doit pas désigner l'offre d'un autre."""
    ids = _preparer(app)
    res = client.get(
        f"/api/applications?offer_id={ids['b']['offre']}",
        headers=auth_header(_token(client, "a")),
    )
    assert res.status_code == 200
    assert res.get_json()["applications"] == []


def test_le_cv_d_un_autre_recruteur_est_refuse(app, client):
    ids = _preparer(app)
    res = client.get(
        f"/api/applications/{ids['b']['candidature']}/cv",
        headers=auth_header(_token(client, "a")),
    )
    assert res.status_code == 403


# --------------------------------- Écriture ---------------------------------

def test_le_statut_d_une_candidature_d_autrui_ne_peut_pas_etre_change(app, client):
    ids = _preparer(app)
    res = client.patch(
        f"/api/applications/{ids['b']['candidature']}/status",
        headers=auth_header(_token(client, "a")),
        json={"status": "rejected"},
    )
    assert res.status_code == 403

    with app.app_context():
        assert Application.query.get(ids["b"]["candidature"]).status == "received"


def test_l_analyse_d_une_candidature_d_autrui_est_refusee(app, client):
    ids = _preparer(app)
    res = client.post(
        f"/api/applications/{ids['b']['candidature']}/analyze",
        headers=auth_header(_token(client, "a")),
        json={"skills": ["python"], "experience_years": 9, "degree": "bac+5"},
    )
    assert res.status_code == 403

    with app.app_context():
        assert Application.query.get(ids["b"]["candidature"]).score == 80


def test_l_offre_d_un_autre_recruteur_ne_peut_pas_etre_modifiee(app, client):
    """Le trou le plus sérieux : `manage_offers` ne disait rien du propriétaire."""
    ids = _preparer(app)
    res = client.patch(
        f"/api/offers/{ids['b']['offre']}",
        headers=auth_header(_token(client, "a")),
        json={"title": "Détourné", "status": "closed"},
    )
    assert res.status_code == 403

    with app.app_context():
        assert JobOffer.query.get(ids["b"]["offre"]).title == "Poste B"


def test_l_offre_d_un_autre_recruteur_ne_peut_pas_etre_supprimee(app, client):
    ids = _preparer(app)
    res = client.delete(
        f"/api/offers/{ids['b']['offre']}",
        headers=auth_header(_token(client, "a")),
    )
    assert res.status_code == 403

    with app.app_context():
        assert JobOffer.query.get(ids["b"]["offre"]).deleted_at is None


def test_le_vivier_d_une_offre_d_autrui_est_refuse(app, client):
    ids = _preparer(app)
    res = client.get(
        f"/api/offers/{ids['b']['offre']}/vivier",
        headers=auth_header(_token(client, "a")),
    )
    assert res.status_code == 403


# ------------------------------- Agrégats -------------------------------

def test_le_tableau_de_bord_ne_revele_pas_l_activite_d_autrui(app, client):
    """Un entonnoir global ne livre aucun nom, mais renseigne sur un confrère."""
    _preparer(app)
    res = client.get("/api/dashboard/stats", headers=auth_header(_token(client, "a")))
    assert res.status_code == 200

    corps = res.get_json()
    assert corps["kpi"]["recues"]["valeur"] == 1
    assert corps["offres_ouvertes"] == 1


# ---------------------------- Le recruteur légitime ----------------------------

def test_le_recruteur_conserve_l_acces_a_ses_propres_dossiers(app, client):
    """La garde ne doit pas se contenter de tout refuser."""
    ids = _preparer(app)
    token = _token(client, "a")

    assert client.patch(
        f"/api/applications/{ids['a']['candidature']}/status",
        headers=auth_header(token), json={"status": "shortlisted"},
    ).status_code == 200

    assert client.patch(
        f"/api/offers/{ids['a']['offre']}",
        headers=auth_header(token), json={"title": "Poste A révisé"},
    ).status_code == 200


def test_l_administrateur_franchit_les_perimetres(app, client, admin_token):
    """Contrepartie assumée : il doit pouvoir intervenir sur tout dossier signalé."""
    _preparer(app)
    with app.app_context():
        role_admin = Role.query.filter_by(name="admin").first()
        vue = Permission.query.filter_by(code="view_applications").first()
        role_admin.permissions = list(role_admin.permissions) + [vue]
        db.session.commit()

    res = client.get("/api/applications", headers=auth_header(admin_token))
    assert res.status_code == 200
    assert len(res.get_json()["applications"]) == 2
