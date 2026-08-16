"""Tests de l'assistant : construction de la base, recherche, faits chiffrés."""
from app.extensions import db
from app.models.application import Application
from app.models.job_offer import JobOffer
from app.models.permission import Permission
from app.models.role import Role
from app.models.user import User
from app.services.rag import assistant, connaissance, generation, index

from .conftest import auth_header


def _preparer(app):
    """Crée un recruteur, deux offres et trois candidatures notées."""
    with app.app_context():
        p_chat = Permission.query.filter_by(code="use_chatbot").first() or Permission(
            code="use_chatbot", description=""
        )
        db.session.add(p_chat)
        role_rec = Role.query.filter_by(name="recruiter").first()
        role_rec.permissions = [p_chat]

        rec = User(email="rec@test.local", full_name="Rec Test", role=role_rec)
        rec.set_password("Passe@1234")
        cand_role = Role.query.filter_by(name="candidate").first()
        db.session.add(rec)
        db.session.flush()

        offre = JobOffer(
            title="Développeur Python Senior",
            description="Conception d'API REST et traitements de données.",
            required_skills=["python", "sql"],
            min_experience_years=3,
            recruiter_id=rec.id,
            location="Casablanca",
            contract_type="CDI",
        )
        db.session.add(offre)
        db.session.flush()

        profils = [
            ("Youssef Tazi", 92, "interview"),
            ("Sara Alaoui", 71, "received"),
            ("Omar Fassi", 38, "rejected"),
        ]
        for nom, note, statut in profils:
            candidat = User(
                email=f"{nom.split()[0].lower()}@test.local",
                full_name=nom,
                role=cand_role,
            )
            candidat.set_password("Passe@1234")
            db.session.add(candidat)
            db.session.flush()

            db.session.add(
                Application(
                    cv_path="/tmp/x.pdf",
                    candidate_id=candidat.id,
                    offer_id=offre.id,
                    score=note,
                    status=statut,
                    score_details={
                        "eliminatoires": ["Expérience 1 an(s) < 3 an(s) requis"]
                        if note < 50 else [],
                        "profil_ats": {
                            "totalExperienceYears": 8 if note > 80 else 2,
                            "highestDegree": "Bac+5",
                            "skills": ["python", "sql", "docker"],
                            "work": [{"position": "Développeur", "company": "TechCorp"}],
                            "languages": [{"language": "Français", "fluency": "C2"}],
                        },
                    },
                )
            )
        db.session.commit()
        return rec.id


def _token_recruteur(client):
    res = client.post(
        "/api/auth/login", json={"email": "rec@test.local", "password": "Passe@1234"}
    )
    return res.get_json()["access_token"]


# ------------------------- Base de connaissance -------------------------

def test_la_base_contient_les_fiches_d_aide(app):
    with app.app_context():
        docs = connaissance.documents_aide()
        assert len(docs) >= 6
        assert all(d.type == "aide" and d.texte for d in docs)


def test_chaque_document_est_autonome(app):
    """Un document doit être compréhensible hors de son contexte d'origine."""
    _preparer(app)
    with app.app_context():
        index.invalider()
        docs = connaissance.construire()
        candidatures = [d for d in docs if d.type == "candidature"]
        assert candidatures
        for doc in candidatures:
            # Le nom du candidat et l'intitule du poste doivent y figurer
            assert "Candidature de" in doc.texte
            assert "pour le poste de" in doc.texte


def test_le_motif_d_ecartement_figure_dans_le_document(app):
    _preparer(app)
    with app.app_context():
        index.invalider()
        docs = connaissance.construire()
        textes = " ".join(d.texte for d in docs if d.type == "candidature")
        assert "Critère éliminatoire" in textes


# ----------------------------- Recherche -----------------------------

def test_la_recherche_privilegie_les_documents_pertinents(app):
    _preparer(app)
    with app.app_context():
        index.invalider()
        resultats = index.rechercher("comment le score est-il calculé ?")
        assert resultats
        # La fiche d'aide sur le score doit remonter en tete
        assert resultats[0][0].type == "aide"


def test_la_recherche_renvoie_toujours_un_resultat(app):
    """Même hors sujet, l'assistant propose des sources plutôt qu'un vide."""
    _preparer(app)
    with app.app_context():
        index.invalider()
        assert index.rechercher("quelle est la météo demain ?")


def test_l_index_est_reconstruit_apres_modification(app):
    """Une nouvelle candidature doit apparaître sans redémarrage du service."""
    _preparer(app)
    with app.app_context():
        index.invalider()
        avant = len(index.obtenir()[0])

        # Nouveau candidat : la contrainte d'unicite interdit deux
        # candidatures d'une meme personne sur une meme offre.
        nouveau = User(
            email="nouveau@test.local",
            full_name="Nouveau Candidat",
            role=Role.query.filter_by(name="candidate").first(),
        )
        nouveau.set_password("Passe@1234")
        db.session.add(nouveau)
        db.session.flush()

        db.session.add(
            Application(
                cv_path="/tmp/y.pdf",
                candidate_id=nouveau.id,
                offer_id=JobOffer.query.first().id,
                score=60,
            )
        )
        db.session.commit()

        assert len(index.obtenir()[0]) > avant


# ------------------------- Faits chiffrés -------------------------

def test_les_grandeurs_sont_calculees_et_non_estimees(app):
    _preparer(app)
    with app.app_context():
        f = assistant.faits()
        assert f["candidatures_total"] == 3
        assert f["au_dessus_du_seuil"] == 2      # 92 et 71
        assert f["entretiens"] == 1
        assert f["note_maximale"] == 92
        assert f["note_minimale"] == 38


def test_le_tableau_des_meilleurs_profils_respecte_le_seuil(app):
    _preparer(app)
    with app.app_context():
        tableau = assistant._tableau_associe("quels sont les meilleurs profils ?", None)
        assert tableau is not None
        assert len(tableau["lignes"]) == 2       # le profil a 38 est exclu
        assert "92/100" in tableau["lignes"][0]


def test_le_tableau_de_l_entonnoir_est_coherent(app):
    _preparer(app)
    with app.app_context():
        tableau = assistant._tableau_associe("montre-moi l'entonnoir", None)
        assert tableau["lignes"][0][1] == 3      # candidatures recues
        assert tableau["lignes"][1][1] == 2      # au-dessus du seuil


# ------------------------- Génération -------------------------

def test_un_fournisseur_est_toujours_disponible():
    """Le mode par gabarits garantit une réponse en toute circonstance."""
    assert generation.fournisseur_actif() in ("ollama", "api", "gabarits")


def test_la_reponse_cite_ses_sources(app):
    _preparer(app)
    with app.app_context():
        index.invalider()
        reponse = assistant.repondre("quels sont les meilleurs profils ?")
        assert reponse["texte"]
        assert reponse["sources"]
        assert all("titre" in s and "pertinence" in s for s in reponse["sources"])


def test_une_question_vide_est_refusee(app):
    with app.app_context():
        assert "question" in assistant.repondre("").get("texte", "").lower()


# ------------------------- Point d'accès -------------------------

def test_l_assistant_repond_via_l_api(app, client):
    _preparer(app)
    token = _token_recruteur(client)

    res = client.post(
        "/api/assistant/ask",
        headers=auth_header(token),
        json={"question": "Combien de candidatures attendent une décision ?"},
    )
    assert res.status_code == 200
    corps = res.get_json()
    assert corps["texte"]
    assert "fournisseur" in corps


def test_l_acces_est_refuse_sans_la_permission(app, client, admin_token):
    """L'administrateur du jeu de test ne dispose pas de `use_chatbot`."""
    _preparer(app)
    res = client.post(
        "/api/assistant/ask",
        headers=auth_header(admin_token),
        json={"question": "test"},
    )
    assert res.status_code == 403


def test_une_question_trop_longue_est_refusee(app, client):
    _preparer(app)
    token = _token_recruteur(client)
    res = client.post(
        "/api/assistant/ask",
        headers=auth_header(token),
        json={"question": "a" * 501},
    )
    assert res.status_code == 400
