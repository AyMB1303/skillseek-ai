"""Offres d'emploi : CRUD de base (complété au Sprint 2)."""
from flask import Blueprint, jsonify, request

from ..extensions import db
from ..middleware.permissions import current_user_required, require_permission
from ..models.job_offer import JobOffer

offers_bp = Blueprint("offers", __name__)


@offers_bp.get("")
@current_user_required
def list_offers(current_user):
    offers = JobOffer.query.filter_by(status="open").order_by(
        JobOffer.created_at.desc()
    ).all()
    return jsonify(offers=[o.to_dict() for o in offers])


@offers_bp.get("/<int:offer_id>")
@current_user_required
def get_offer(current_user, offer_id):
    offer = JobOffer.query.get_or_404(offer_id)
    return jsonify(offer=offer.to_dict())


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
        min_experience_years=int(data.get("min_experience_years", 0)),
        min_degree=data.get("min_degree"),
        recruiter=current_user,
    )
    db.session.add(offer)
    db.session.commit()
    return jsonify(offer=offer.to_dict()), 201


@offers_bp.patch("/<int:offer_id>")
@require_permission("manage_offers")
def update_offer(current_user, offer_id):
    offer = JobOffer.query.get_or_404(offer_id)
    data = request.get_json(silent=True) or {}

    for field in ("title", "description", "min_degree", "status"):
        if field in data:
            setattr(offer, field, data[field])
    if "required_skills" in data:
        offer.required_skills = data["required_skills"]
    if "min_experience_years" in data:
        offer.min_experience_years = int(data["min_experience_years"])

    db.session.commit()
    return jsonify(offer=offer.to_dict())
