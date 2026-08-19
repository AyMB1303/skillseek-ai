"""Lecture analytique du portefeuille de candidatures.

Le tableau de bord répond à « combien ». Cette route répond à « pourquoi » —
et c'est là que les erreurs de calcul passent inaperçues, faute d'un chiffre
de référence auquel les comparer. D'où ces tests.
"""
from datetime import datetime, timedelta, timezone

from app.extensions import db
from app.models.application import Application
from app.models.job_offer import JobOffer
from app.models.journal import EntreeJournal
from app.models.permission import Permission
from app.models.role import Role
from app.models.user import User

from .conftest import auth_header

MOT_DE_PASSE = "Passe@1234"


def _preparer(app):
    """Un recruteur, une offre, cinq candidatures aux profils contrastés."""
    with app.app_context():
        role_rec = Role.query.filter_by(name="recruiter").first()
        role_rec.permissions = [
            Permission.query.filter_by(code=code).first()
            or Permission(code=code, description="")
            for code in ("view_dashboard", "view_applications")
        ]
        db.session.add_all(role_rec.permissions)
        role_cand = Role.query.filter_by(name="candidate").first()

        rec = User(email="rec@test.local", full_name="Rec Test", role=role_rec)
        rec.set_password(MOT_DE_PASSE)
        db.session.add(rec)
        db.session.flush()

        offre = JobOffer(
            title="Développeur Python", description="API REST.",
            required_skills=["python", "sql"], recruiter_id=rec.id,
        )
        db.session.add(offre)
        db.session.flush()

        # Notes choisies pour tomber dans quatre tranches distinctes.
        profils = [
            (92, "hired", [], []),
            (74, "interview", [], ["Expérience 4 ans < 5 ans requis"]),
            (58, "under_review", [], []),
            (41, "rejected", ["Compétence obligatoire absente : sql"], []),
            (18, "rejected", ["Compétence obligatoire absente : python"], []),
        ]
        depot = datetime.now(timezone.utc) - timedelta(days=20)

        for rang, (note, statut, eliminatoires, reserves) in enumerate(profils):
            candidat = User(
                email=f"c{rang}@test.local", full_name=f"Candidat {rang}",
                role=role_cand,
            )
            candidat.set_password(MOT_DE_PASSE)
            db.session.add(candidat)
            db.session.flush()

            candidature = Application(
                cv_path="/tmp/cv.pdf", candidate_id=candidat.id, offer_id=offre.id,
                score=note, status=statut, created_at=depot,
                score_details={
                    "eliminatoires": eliminatoires,
                    "reserves": reserves,
                    "competences_manquantes": ["sql"] if note < 50 else [],
                },
            )
            db.session.add(candidature)
            db.session.flush()

            # Trace de première décision, quatre jours après le dépôt : c'est
            # elle que la route lit pour calculer le délai.
            if statut != "received":
                db.session.add(EntreeJournal(
                    action="candidature_statut", objet_type="candidature",
                    objet_id=candidature.id, auteur_id=rec.id,
                    created_at=depot + timedelta(days=4),
                ))

        db.session.commit()


def _token(client):
    res = client.post(
        "/api/auth/login",
        json={"email": "rec@test.local", "password": MOT_DE_PASSE},
    )
    return res.get_json()["access_token"]


def test_la_distribution_couvre_toutes_les_tranches(app, client):
    _preparer(app)
    res = client.get("/api/dashboard/analyse", headers=auth_header(_token(client)))
    assert res.status_code == 200

    corps = res.get_json()
    assert corps["effectif"] == 5
    assert corps["analysees"] == 5

    par_tranche = {d["tranche"]: d["effectif"] for d in corps["distribution"]}
    assert par_tranche["85 – 100"] == 1      # 92
    assert par_tranche["70 – 84"] == 1       # 74
    assert par_tranche["50 – 69"] == 1       # 58
    assert par_tranche["25 – 49"] == 1       # 41
    assert par_tranche["0 – 24"] == 1        # 18
    assert sum(par_tranche.values()) == corps["analysees"]


def test_le_seuil_de_preselection_est_marque_sur_les_tranches(app, client):
    """L'interface doit pouvoir colorer sans réimplémenter la règle RG-01."""
    _preparer(app)
    res = client.get("/api/dashboard/analyse", headers=auth_header(_token(client)))
    retenues = {d["tranche"] for d in res.get_json()["distribution"] if d["retenu"]}
    assert retenues == {"50 – 69", "70 – 84", "85 – 100"}


def test_la_note_mediane_est_bien_la_mediane(app, client):
    _preparer(app)
    res = client.get("/api/dashboard/analyse", headers=auth_header(_token(client)))
    # 18, 41, 58, 74, 92 → la valeur centrale est 58.
    assert res.get_json()["note_mediane"] == 58


def test_les_motifs_d_ecartement_sont_regroupes_par_nature(app, client):
    """Sans regroupement, chaque dossier produirait son propre motif unique."""
    _preparer(app)
    res = client.get("/api/dashboard/analyse", headers=auth_header(_token(client)))
    motifs = {m["libelle"]: m["effectif"] for m in res.get_json()["motifs_ecartement"]}
    assert motifs["Compétence obligatoire absente"] == 2


def test_les_reserves_sont_comptees_separement_des_eliminatoires(app, client):
    _preparer(app)
    res = client.get("/api/dashboard/analyse", headers=auth_header(_token(client)))
    corps = res.get_json()
    assert corps["reserves"][0]["libelle"] == "Expérience 4 ans < 5 ans requis"
    assert all(
        "Expérience" not in m["libelle"] for m in corps["motifs_ecartement"]
    )


def test_le_delai_de_decision_vient_du_journal(app, client):
    """La candidature ne porte pas de date de modification : le journal, si."""
    _preparer(app)
    res = client.get("/api/dashboard/analyse", headers=auth_header(_token(client)))
    corps = res.get_json()
    assert corps["delai_median_jours"] == 4
    assert corps["dossiers_traces"] == 5


def test_l_analyse_reste_dans_le_perimetre_du_recruteur(app, client, admin_token):
    """Même garde que partout ailleurs : le périmètre, pas le rôle."""
    _preparer(app)
    res = client.get("/api/dashboard/analyse", headers=auth_header(_token(client)))
    assert res.get_json()["effectif"] == 5

    # L'administrateur du jeu de test ne détient pas `view_dashboard`.
    refus = client.get("/api/dashboard/analyse", headers=auth_header(admin_token))
    assert refus.status_code == 403


def test_une_base_vide_ne_fait_pas_echouer_l_analyse(app, client):
    """Le cas du premier jour : aucune candidature, aucun journal."""
    with app.app_context():
        role_rec = Role.query.filter_by(name="recruiter").first()
        perm = Permission.query.filter_by(code="view_dashboard").first() or Permission(
            code="view_dashboard", description=""
        )
        db.session.add(perm)
        role_rec.permissions = [perm]
        rec = User(email="rec@test.local", full_name="Rec Test", role=role_rec)
        rec.set_password(MOT_DE_PASSE)
        db.session.add(rec)
        db.session.commit()

    res = client.get("/api/dashboard/analyse", headers=auth_header(_token(client)))
    assert res.status_code == 200

    corps = res.get_json()
    assert corps["effectif"] == 0
    assert corps["note_mediane"] is None
    assert corps["delai_median_jours"] is None
    assert corps["motifs_ecartement"] == []
