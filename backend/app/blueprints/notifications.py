"""Notifications de l'utilisateur connecté (chacun ne voit que les siennes)."""
from flask import Blueprint, jsonify

from ..middleware.permissions import current_user_required
from ..services import notifications as svc

notifications_bp = Blueprint("notifications", __name__)


@notifications_bp.get("")
@current_user_required
def lister(current_user):
    notifs = svc.lister(current_user.id)
    return jsonify(
        notifications=[n.to_dict() for n in notifs],
        non_lues=svc.compter_non_lues(current_user.id),
    )


@notifications_bp.post("/<int:notif_id>/read")
@current_user_required
def marquer_lue(current_user, notif_id):
    if not svc.marquer_lue(current_user.id, notif_id):
        return jsonify(error="Notification introuvable."), 404
    return jsonify(non_lues=svc.compter_non_lues(current_user.id))


@notifications_bp.post("/read-all")
@current_user_required
def marquer_toutes_lues(current_user):
    svc.marquer_toutes_lues(current_user.id)
    return jsonify(non_lues=0)
