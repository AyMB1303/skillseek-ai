"""Recommandation d'offres à un candidat.

Le moteur de score répond depuis le début à une seule question : « ce candidat
convient-il à cette offre ? ». Il répond aussi bien à la question inverse — les
deux termes de la comparaison ne changent pas, seul change ce qu'on fait
varier. C'est tout l'objet de ce module, et sa principale vertu : il ne
réimplémente rien.

**Ce qui est montré au candidat, et ce qui ne l'est pas.**

La note n'est jamais communiquée. Elle sert à ordonner, elle ne s'affiche pas.
Un chiffre sans son barème invite au malentendu — quelqu'un qui aurait lu
« 87 % » avant d'être écarté aurait un grief légitime — et il n'apprend rien
d'utilisable. Ce sont les faits qui sont restitués : les compétences reconnues,
et surtout **celles qui manquent**, la seule chose qu'un candidat puisse
corriger.

**Le profil observé l'emporte sur le profil déclaré.** Tant que le candidat n'a
pas postulé, on travaille sur ce qu'il a saisi lui-même. Dès qu'un CV a été
analysé, c'est le profil extrait qui sert : personne ne vérifie une déclaration,
alors qu'un document, lui, a été lu.
"""
from ..models.application import Application
from ..models.job_offer import JobOffer
from .scoring import calculer_score

# Nombre d'offres proposées. Assez pour offrir un choix, assez peu pour que la
# liste se lise d'un coup d'œil : au-delà, la recommandation redevient un
# catalogue et perd son intérêt.
PLAFOND = 6


def profil_du_candidat(utilisateur):
    """Retourne (profil, origine) — le meilleur profil connu de la personne.

    `origine` vaut « cv » lorsqu'il provient d'une candidature analysée, et
    « declare » lorsqu'il vient du formulaire. La distinction est remontée
    jusqu'à l'interface : le candidat doit savoir sur quoi la plateforme
    s'appuie pour lui parler.
    """
    derniere = (
        Application.query
        .filter_by(candidate_id=utilisateur.id)
        .filter(Application.score_details.isnot(None))
        .order_by(Application.created_at.desc())
        .first()
    )
    if derniere:
        details = derniere.score_details or {}
        profil = details.get("profil_analyse")
        if profil and profil.get("skills"):
            return profil, "cv"

    declare = utilisateur.profil_declare or {}
    if declare.get("skills"):
        return declare, "declare"

    return None, None


def _correspondance(trouvees, requises):
    """Qualifie l'adéquation en termes de faits, non de note.

    Trois niveaux seulement, et calculés sur les compétences obligatoires
    plutôt que sur le score. La raison est la même que pour l'absence de
    chiffre : « il vous manque une compétence sur cinq » se vérifie et
    s'actionne, « 72 sur 100 » ne se vérifie pas.
    """
    if not requises:
        return "ouverte"
    part = len(trouvees) / len(requises)
    if part >= 0.99:
        return "forte"
    return "partielle" if part >= 0.5 else "eloignee"


def recommander(utilisateur, ville=None, contrat=None, limite=PLAFOND):
    """Classe les offres ouvertes selon le profil connu du candidat.

    `ville` et `contrat` restreignent le terrain avant le classement : ce sont
    des contraintes que la personne pose elle-même, et aucun rapprochement de
    compétences ne les compense. Le moteur ordonne ensuite ce qui reste.
    """
    profil, origine = profil_du_candidat(utilisateur)
    if profil is None:
        return {"profil_connu": False, "origine": None, "offres": []}

    deja_postulees = {
        a.offer_id for a in Application.query.filter_by(candidate_id=utilisateur.id).all()
    }

    requete = JobOffer.query.filter(
        JobOffer.status == "open", JobOffer.deleted_at.is_(None)
    )
    if ville:
        requete = requete.filter(JobOffer.location.ilike(f"%{ville}%"))
    if contrat:
        requete = requete.filter(JobOffer.contract_type == contrat)

    classees = []
    for offre in requete.all():
        if offre.id in deja_postulees:
            continue

        # Sans composante sémantique : le texte du CV n'est pas conservé, et
        # une déclaration n'en produit pas. Le rapprochement porte donc sur les
        # compétences, l'expérience et le diplôme — plus grossier qu'une vraie
        # analyse, ce qui suffit pour orienter.
        score, details = calculer_score(profil, offre)

        trouvees = details.get("competences_trouvees") or []
        manquantes = details.get("competences_manquantes") or []
        classees.append({
            "offre": {
                "id": offre.id,
                "titre": offre.title,
                "entreprise": offre.recruiter.company if offre.recruiter else None,
                "lieu": offre.location,
                "contrat": offre.contract_type,
                "mode_travail": offre.remote_policy,
            },
            "correspondance": _correspondance(trouvees, offre.required_skills or []),
            "competences_reconnues": trouvees,
            "competences_manquantes": manquantes,
            "experience_requise": offre.min_experience_years,
            "diplome_requis": offre.min_degree,
            # Le rang de classement est conservé pour l'ordre ; la note, non.
            "_ordre": score,
        })

    classees.sort(key=lambda o: o["_ordre"], reverse=True)
    for offre in classees:
        offre.pop("_ordre")

    return {
        "profil_connu": True,
        "origine": origine,
        "competences_du_profil": profil.get("skills", []),
        "offres": classees[:limite],
        "total_examinees": len(classees),
        "lecture": (
            "Les offres sont classées selon la proximité entre votre profil et "
            "leurs exigences. Aucune note ne vous est attribuée : ce classement "
            "vous oriente, il ne présume d'aucune décision de recruteur."
        ),
    }
