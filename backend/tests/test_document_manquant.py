"""Candidature dont le document a disparu du disque.

C'est l'incident le plus déroutant que la plateforme puisse produire : la base
affirme qu'un CV existe, l'interface échoue à l'ouvrir, l'analyse rend une note
vide, et rien ne dit pourquoi. Le recruteur relance alors indéfiniment la même
opération.

Deux exigences en découlent, et ce sont elles qui sont vérifiées ici. Un
document absent doit produire un **refus explicite et distinct** d'une
extraction infructueuse — les deux n'appellent pas le même recours. Et la
remise à plat du jeu de démonstration doit **rétablir les fichiers** plutôt que
se contenter de les inventorier.
"""
import os

from app.extensions import db
from app.models.application import Application
from app.models.job_offer import JobOffer
from app.models.permission import Permission
from app.models.role import Role
from app.models.user import User
from app.services.generateur_pdf import ecrire_cv_pdf

from .conftest import auth_header

MOT_DE_PASSE = "Passe@1234"


def _preparer(app, chemin_cv):
    """Un recruteur, son offre, une candidature pointant sur `chemin_cv`."""
    with app.app_context():
        role_rec = Role.query.filter_by(name="recruiter").first()
        role_rec.permissions = [
            Permission.query.filter_by(code=code).first()
            or Permission(code=code, description="")
            for code in ("view_applications", "manage_applications")
        ]
        db.session.add_all(role_rec.permissions)

        rec = User(email="rec@test.local", full_name="Rec Test", role=role_rec)
        rec.set_password(MOT_DE_PASSE)
        db.session.add(rec)
        db.session.flush()

        offre = JobOffer(
            title="Développeur Python", description="Poste back-end.",
            required_skills=["python"], recruiter_id=rec.id, status="open",
        )
        db.session.add(offre)

        candidat = User(email="cand@test.local", full_name="Candidat Test",
                        role=Role.query.filter_by(name="candidate").first())
        candidat.set_password(MOT_DE_PASSE)
        db.session.add(candidat)
        db.session.flush()

        candidature = Application(
            cv_path=chemin_cv, candidate_id=candidat.id, offer_id=offre.id,
        )
        db.session.add(candidature)
        db.session.commit()
        return candidature.id


def _token(client, email="rec@test.local"):
    res = client.post(
        "/api/auth/login", json={"email": email, "password": MOT_DE_PASSE}
    )
    return res.get_json()["access_token"]


def test_relancer_l_analyse_sur_un_document_absent_est_refuse(app, client):
    """Un refus nommé, pas une note vide.

    Renvoyer 200 avec un score nul confond « je n'ai pas su lire » et « il n'y
    a rien à lire ». Le premier autorise la saisie manuelle du profil, le
    second appelle un nouveau dépôt : la réponse doit trancher.
    """
    identifiant = _preparer(app, "/tmp/cv-qui-n-existe-pas.pdf")
    res = client.post(
        f"/api/applications/{identifiant}/analyze",
        headers=auth_header(_token(client)),
    )
    assert res.status_code == 409
    assert "introuvable" in res.get_json()["error"]


def test_la_saisie_manuelle_reste_possible_sans_document(app, client):
    """Le recours doit rester ouvert : c'est ce qui rend le refus acceptable."""
    identifiant = _preparer(app, "/tmp/cv-qui-n-existe-pas.pdf")
    res = client.post(
        f"/api/applications/{identifiant}/analyze",
        headers=auth_header(_token(client)),
        json={"skills": ["python"], "experience_years": 3, "degree": "bac+5"},
    )
    assert res.status_code == 200
    assert res.get_json()["application"]["score"] is not None


def test_un_document_present_est_analyse_normalement(app, client, tmp_path):
    """Contrôle négatif : le garde-fou ne doit rien bloquer d'autre."""
    chemin = str(tmp_path / "cv.pdf")
    ecrire_cv_pdf(chemin, "COMPETENCES\npython\nsql\n\nEXPERIENCE\n3 ans")
    identifiant = _preparer(app, chemin)

    res = client.post(
        f"/api/applications/{identifiant}/analyze",
        headers=auth_header(_token(client)),
    )
    assert res.status_code == 200


def test_le_generateur_produit_un_fichier_lisible(tmp_path):
    """Le semis dépend entièrement de cette écriture ; elle mérite un filet."""
    chemin = str(tmp_path / "cv.pdf")
    ecrire_cv_pdf(chemin, "COMPETENCES\npython\n" + "ligne\n" * 200)

    assert os.path.exists(chemin)
    with open(chemin, "rb") as fichier:
        contenu = fichier.read()
    assert contenu.startswith(b"%PDF-")
    assert contenu.rstrip().endswith(b"%%EOF")
