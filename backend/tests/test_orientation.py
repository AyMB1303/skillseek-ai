"""Recommandation d'offres au candidat.

Deux propriétés sont testées avec insistance, parce qu'elles portent des
engagements et non seulement du comportement : **aucune note n'est jamais
communiquée au candidat**, et **le profil extrait d'un CV l'emporte toujours
sur le profil déclaré**.
"""
from app.extensions import db
from app.models.application import Application
from app.models.job_offer import JobOffer
from app.models.role import Role
from app.models.user import User

from .conftest import auth_header

MOT_DE_PASSE = "Passe@1234"


def _preparer(app):
    """Un recruteur, trois offres aux exigences distinctes, un candidat."""
    with app.app_context():
        role_rec = Role.query.filter_by(name="recruiter").first()
        role_cand = Role.query.filter_by(name="candidate").first()

        rec = User(email="rec@test.local", full_name="Rec Test",
                   role=role_rec, company="TechCorp")
        rec.set_password(MOT_DE_PASSE)
        db.session.add(rec)
        db.session.flush()

        offres = [
            ("Développeur Python", ["python", "sql"], 2, "Casablanca", "CDI"),
            ("Développeur Java", ["java", "spring"], 3, "Rabat", "CDI"),
            ("Data Analyst", ["python", "sql", "power bi"], 1, "Casablanca", "Stage"),
        ]
        for titre, competences, annees, lieu, contrat in offres:
            db.session.add(JobOffer(
                title=titre, description=f"Poste de {titre}.",
                required_skills=competences, min_experience_years=annees,
                recruiter_id=rec.id, status="open",
                location=lieu, contract_type=contrat,
            ))

        candidat = User(email="cand@test.local", full_name="Candidat Test",
                        role=role_cand)
        candidat.set_password(MOT_DE_PASSE)
        db.session.add(candidat)
        db.session.commit()
        return candidat.id


def _token(client, email="cand@test.local"):
    res = client.post(
        "/api/auth/login", json={"email": email, "password": MOT_DE_PASSE}
    )
    return res.get_json()["access_token"]


def _declarer(client, token, **donnees):
    corps = {"skills": ["python", "sql"], "experience_years": 3, "degree": "bac+5"}
    corps.update(donnees)
    return client.put(
        "/api/profile/competences", headers=auth_header(token), json=corps
    )


# ------------------------------ Profil déclaré ------------------------------

def test_les_competences_declarees_sont_canonisees(app, client):
    """« JS » saisi librement ne trouverait jamais « javascript » dans l'offre."""
    _preparer(app)
    token = _token(client)
    res = _declarer(client, token, skills=["JS", "Postgres", "  python  "])
    assert res.status_code == 200

    competences = res.get_json()["profil"]["skills"]
    assert "javascript" in competences
    assert "postgresql" in competences
    assert "python" in competences


def test_les_doublons_sont_ecartes(app, client):
    _preparer(app)
    res = _declarer(client, _token(client), skills=["Python", "python", "PYTHON"])
    assert res.get_json()["profil"]["skills"] == ["python"]


def test_une_experience_invraisemblable_est_refusee(app, client):
    _preparer(app)
    res = _declarer(client, _token(client), experience_years=140)
    assert res.status_code == 400


# ---------------------------- Recommandations ----------------------------

def test_sans_profil_aucune_recommandation_mais_pas_d_erreur(app, client):
    """Le premier jour d'un compte : il faut le dire, pas échouer."""
    _preparer(app)
    res = client.get("/api/profile/recommandations",
                     headers=auth_header(_token(client)))
    assert res.status_code == 200

    corps = res.get_json()
    assert corps["profil_connu"] is False
    assert corps["offres"] == []


def test_les_offres_sont_classees_par_proximite(app, client):
    _preparer(app)
    token = _token(client)
    _declarer(client, token, skills=["python", "sql"])

    corps = client.get("/api/profile/recommandations",
                       headers=auth_header(token)).get_json()
    assert corps["profil_connu"] is True

    titres = [o["offre"]["titre"] for o in corps["offres"]]
    # Les deux offres Python/SQL passent devant celle en Java, qu'aucune
    # compétence déclarée ne recoupe.
    assert titres.index("Développeur Java") == len(titres) - 1


def test_aucune_note_n_est_communiquee_au_candidat(app, client):
    """L'engagement le plus important de ce module.

    Le classement s'appuie sur le score, mais la réponse ne doit contenir
    aucune valeur numérique d'adéquation — ni au premier niveau, ni cachée
    dans un sous-objet.
    """
    _preparer(app)
    token = _token(client)
    _declarer(client, token)

    corps = client.get("/api/profile/recommandations",
                       headers=auth_header(token)).get_json()

    interdits = {"score", "note", "_ordre", "score_details", "probabilite"}
    for offre in corps["offres"]:
        assert not (interdits & set(offre)), f"Note exposée : {offre}"
        assert not (interdits & set(offre["offre"]))


def test_les_competences_manquantes_sont_restituees(app, client):
    """C'est la seule information que le candidat puisse corriger."""
    _preparer(app)
    token = _token(client)
    _declarer(client, token, skills=["python", "sql"])

    corps = client.get("/api/profile/recommandations",
                       headers=auth_header(token)).get_json()
    analyste = next(
        o for o in corps["offres"] if o["offre"]["titre"] == "Data Analyst"
    )
    assert "power bi" in analyste["competences_manquantes"]
    assert set(analyste["competences_reconnues"]) == {"python", "sql"}
    assert analyste["correspondance"] == "partielle"


def test_une_offre_deja_postulee_n_est_plus_proposee(app, client):
    identifiant = _preparer(app)
    token = _token(client)
    _declarer(client, token)

    with app.app_context():
        offre = JobOffer.query.filter_by(title="Développeur Python").first()
        db.session.add(Application(
            cv_path="/tmp/cv.pdf", candidate_id=identifiant, offer_id=offre.id,
        ))
        db.session.commit()

    corps = client.get("/api/profile/recommandations",
                       headers=auth_header(token)).get_json()
    assert all(
        o["offre"]["titre"] != "Développeur Python" for o in corps["offres"]
    )


def test_le_filtre_de_ville_precede_le_classement(app, client):
    """Une contrainte posée par la personne ne se compense pas par un score."""
    _preparer(app)
    token = _token(client)
    _declarer(client, token)

    corps = client.get("/api/profile/recommandations?ville=Rabat",
                       headers=auth_header(token)).get_json()
    assert [o["offre"]["titre"] for o in corps["offres"]] == ["Développeur Java"]


def test_le_profil_extrait_du_cv_prime_sur_le_declare(app, client):
    """L'observé l'emporte sur le déclaré : personne ne vérifie une saisie."""
    identifiant = _preparer(app)
    token = _token(client)
    _declarer(client, token, skills=["python"])

    with app.app_context():
        offre = JobOffer.query.filter_by(title="Développeur Java").first()
        db.session.add(Application(
            cv_path="/tmp/cv.pdf", candidate_id=identifiant, offer_id=offre.id,
            score=70,
            score_details={
                "profil_analyse": {
                    "skills": ["java", "spring"],
                    "experience_years": 5,
                    "degree": "bac+5",
                }
            },
        ))
        db.session.commit()

    corps = client.get("/api/profile/recommandations",
                       headers=auth_header(token)).get_json()
    assert corps["origine"] == "cv"
    assert set(corps["competences_du_profil"]) == {"java", "spring"}
