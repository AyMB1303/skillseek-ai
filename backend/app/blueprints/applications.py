"""Candidatures : squelette Sprint 1 (upload CV complété au Sprint 2)."""
from flask import Blueprint, jsonify

from ..middleware.permissions import current_user_required, require_permission
from ..models.application import Application

applications_bp = Blueprint("applications", __name__)


@applications_bp.get("")
@require_permission("view_applications")
def list_applications(current_user):
    apps = Application.query.order_by(Application.created_at.desc()).all()
    return jsonify(applications=[a.to_dict() for a in apps])


@applications_bp.get("/mine")
@current_user_required
def my_applications(current_user):
    apps = (
        Application.query.filter_by(candidate_id=current_user.id)
        .order_by(Application.created_at.desc())
        .all()
    )
    return jsonify(applications=[a.to_dict() for a in apps])
