"""Offres d'emploi : publication, modification, corbeille."""
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request

from ..extensions import db
from ..middleware.permissions import current_user_required, require_permission
from ..models.job_offer import JobOffer
from ..services import acces, notifications as notifs

offers_bp = Blueprint("offers", __name__)

TYPES_CONTRAT = ("CDI", "CDD", "Stage", "Alternance", "Freelance")
MODES_TRAVAIL = ("Sur site", "Hybride", "Télétravail")


def _maintenant():
    return datetime.now(timezone.utc)


@offers_bp.get("/<int:offer_id>/vivier")
@require_permission("view_applications")
def vivier(current_user, offer_id):
    """Candidats déjà connus dont le profil correspond à cette offre.

    Une plateforme de recrutement accumule des profils analysés. Les laisser
    dormir après une candidature revient à jeter l'essentiel de sa valeur :
    quelqu'un qui a postulé au poste de développeur backend il y a deux mois
    est peut-être exactement le profil recherché aujourd'hui, et personne ne
    pensera à aller le chercher.

    Le rapprochement réutilise le moteur de score, sans sa composante
    sémantique : les textes des curriculum vitæ ne sont pas conservés, seuls
    les profils structurés le sont. Le classement obtenu est donc plus
    grossier que celui d'une vraie candidature — il sert à repérer, pas à
    décider.
    """
    from ..models.application import Application
    from ..services.scoring import SEUIL_RETENU, calculer_score

    offre = JobOffer.query.get_or_404(offer_id)
    if not current_user.est_administrateur and offre.recruiter_id != current_user.id:
        return jsonify(error="Cette offre ne vous appartient pas."), 403

    deja_candidats = {
        a.candidate_id for a in Application.query.filter_by(offer_id=offer_id).all()
    }

    # Un profil par candidat : le plus récent, seul à jour.
    profils = {}
    for candidature in (
        Application.query
        .filter(Application.score_details.isnot(None))
        .order_by(Application.created_at.desc())
        .all()
    ):
        if candidature.candidate_id in deja_candidats:
            continue
        if candidature.candidate_id in profils:
            continue
        profil = (candidature.score_details or {}).get("profil_analyse")
        if profil and candidature.candidate:
            profils[candidature.candidate_id] = (candidature, profil)

    resultats = []
    for candidature, profil in profils.values():
        score, details = calculer_score(profil, offre)
        resultats.append({
            "candidat_id": candidature.candidate_id,
            "candidat": candidature.candidate.full_name,
            "email": candidature.candidate.email,
            "score": score,
            "competences_trouvees": details.get("competences_trouvees", []),
            "competences_manquantes": details.get("competences_manquantes", []),
            "eliminatoires": details.get("eliminatoires", []),
            "derniere_candidature": {
                "offre": candidature.offer.title if candidature.offer else None,
                "date": candidature.created_at.isoformat(),
            },
        })

    resultats.sort(key=lambda r: r["score"], reverse=True)
    retenus = [r for r in resultats if r["score"] >= SEUIL_RETENU][:10]

    return jsonify(
        offre={"id": offre.id, "titre": offre.title},
        profils=retenus,
        examines=len(resultats),
        lecture=(
            "Score calculé sans la proximité sémantique : le texte des CV "
            "n'est pas conservé. Il repère des profils, il ne les classe pas."
        ),
    )


@offers_bp.post("/detecter-competences")
@current_user_required
def detecter_competences(current_user):
    """Relève dans la description de l'offre les compétences du référentiel.

    C'est le même code qui lit les curriculum vitæ. L'intérêt n'est pas
    seulement d'épargner de la saisie : les compétences proposées sont, par
    construction, celles que le moteur saura reconnaître dans les CV. Le
    recruteur ne peut donc plus créer une exigence introuvable en écrivant
    « postgres » là où l'analyse attend « postgresql ».
    """
    from ..services.ats import extraire_competences

    texte = (request.get_json(silent=True) or {}).get("description") or ""
    if len(texte.strip()) < 20:
        return jsonify(competences=[])

    return jsonify(competences=extraire_competences(texte))


@offers_bp.get("/referentiel-competences")
@current_user_required
def referentiel_competences(current_user):
    """Compétences reconnues par le moteur d'analyse.

    Cette route existe pour une raison de fond, pas de confort. Le moteur ne
    sait rapprocher un curriculum d'une offre que si la compétence exigée
    appartient à son référentiel : un recruteur qui saisit « postgres » au lieu
    de « postgresql » rend l'exigence introuvable, et **tous** les candidats
    sont alors écartés pour une compétence qu'ils possèdent pourtant. La panne
    est silencieuse — aucune erreur, seulement un classement vide.

    En exposant le référentiel, l'interface peut proposer les formes exactes et
    avertir lorsqu'une saisie n'est pas reconnue.
    """
    from ..services.competences import INDEX_VARIANTES, REFERENTIEL

    return jsonify(
        competences=sorted(REFERENTIEL.keys()),
        # Les variantes permettent a l'interface de corriger d'elle-meme :
        # « JS » saisi devient « javascript ».
        variantes={v: c for v, c in INDEX_VARIANTES.items() if v not in REFERENTIEL},
        total=len(REFERENTIEL),
    )


@offers_bp.get("")
@current_user_required
def list_offers(current_user):
    """Les candidats ne voient que les offres ouvertes ;
    les recruteurs et administrateurs voient aussi les offres fermées.
    Les offres en corbeille sont exclues dans tous les cas."""
    requete = JobOffer.query.filter(JobOffer.deleted_at.is_(None))
    role = current_user.role.name if current_user.role else None
    if role not in ("recruiter", "admin"):
        requete = requete.filter_by(status="open")

    offers = requete.order_by(JobOffer.created_at.desc()).all()
    return jsonify(offers=[o.to_dict() for o in offers])


@offers_bp.get("/<int:offer_id>")
@current_user_required
def get_offer(current_user, offer_id):
    offer = JobOffer.query.get_or_404(offer_id)
    if offer.is_deleted:
        return jsonify(error="Cette offre n'est plus disponible."), 404
    return jsonify(offer=offer.to_dict())


def _appliquer_champs(offer, data):
    """Renseigne les champs d'annonce communs à la création et à la mise à jour."""
    if "location" in data:
        offer.location = (data["location"] or "").strip() or None
    if "contract_type" in data:
        valeur = (data["contract_type"] or "").strip()
        offer.contract_type = valeur if valeur in TYPES_CONTRAT else None
    if "remote_policy" in data:
        valeur = (data["remote_policy"] or "").strip()
        offer.remote_policy = valeur if valeur in MODES_TRAVAIL else None
    for champ in ("salary_min", "salary_max"):
        if champ in data:
            valeur = data[champ]
            setattr(offer, champ, int(valeur) if valeur not in (None, "") else None)


@offers_bp.post("")
@require_permission("manage_offers")
def create_offer(current_user):
    data = request.get_json(silent=True) or {}
    if not data.get("title") or not data.get("description"):
        return jsonify(error="Titre et description requis."), 400

    offer = JobOffer(
        title=data["title"].strip(),
        description=data["description"].strip(),
        required_skills=data.get("required_skills", []),
        preferred_skills=data.get("preferred_skills", []),
        min_experience_years=int(data.get("min_experience_years", 0)),
        min_degree=data.get("min_degree"),
        recruiter=current_user,
    )
    _appliquer_champs(offer, data)

    if offer.salary_min and offer.salary_max and offer.salary_min > offer.salary_max:
        return jsonify(error="Le salaire minimum ne peut dépasser le maximum."), 400

    db.session.add(offer)
    db.session.flush()
    notifs.offre_publiee(offer)
    db.session.commit()
    return jsonify(offer=offer.to_dict()), 201


@offers_bp.patch("/<int:offer_id>")
@require_permission("manage_offers")
def update_offer(current_user, offer_id):
    offer, refus = acces.offre(current_user, offer_id)
    if refus:
        return refus
    data = request.get_json(silent=True) or {}

    for field in ("title", "description", "min_degree", "status"):
        if field in data:
            setattr(offer, field, data[field])
    if "required_skills" in data:
        offer.required_skills = data["required_skills"]
    if "preferred_skills" in data:
        offer.preferred_skills = data["preferred_skills"]
    if "min_experience_years" in data:
        offer.min_experience_years = int(data["min_experience_years"])
    _appliquer_champs(offer, data)

    db.session.commit()
    return jsonify(offer=offer.to_dict())


# ---------------------------- Corbeille ----------------------------

@offers_bp.delete("/<int:offer_id>")
@require_permission("manage_offers")
def delete_offer(current_user, offer_id):
    """Suppression logique : l'offre part en corbeille avec ses candidatures."""
    offer, refus = acces.offre(current_user, offer_id)
    if refus:
        return refus
    if offer.is_deleted:
        return jsonify(error="Cette offre est déjà dans la corbeille."), 400

    offer.deleted_at = _maintenant()
    offer.status = "closed"
    db.session.commit()
    return jsonify(message=f"« {offer.title} » placée dans la corbeille.")


@offers_bp.post("/<int:offer_id>/restore")
@require_permission("manage_offers")
def restore_offer(current_user, offer_id):
    offer, refus = acces.offre(current_user, offer_id)
    if refus:
        return refus
    if not offer.is_deleted:
        return jsonify(error="Cette offre n'est pas dans la corbeille."), 400

    offer.deleted_at = None
    db.session.commit()
    return jsonify(offer=offer.to_dict(), message=f"« {offer.title} » restaurée.")


@offers_bp.delete("/<int:offer_id>/purge")
@require_permission("manage_offers")
def purge_offer(current_user, offer_id):
    """Suppression définitive, réservée aux offres déjà en corbeille."""
    offer, refus = acces.offre(current_user, offer_id)
    if refus:
        return refus
    if not offer.is_deleted:
        return jsonify(error="Placez d'abord cette offre dans la corbeille."), 400
    if offer.applications:
        return jsonify(
            error="Cette offre a reçu des candidatures et ne peut être supprimée "
                  "définitivement. Elle reste consultable dans la corbeille."
        ), 400

    db.session.delete(offer)
    db.session.commit()
    return jsonify(message="Offre supprimée définitivement.")
