"""Profil utilisateur : modification, mot de passe, droits RGPD / loi 09-08."""
import re

from flask import Blueprint, jsonify, request

from ..extensions import db
from ..middleware.permissions import current_user_required
from ..models.application import Application

profile_bp = Blueprint("profile", __name__)

PASSWORD_RE = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$")


@profile_bp.patch("")
@current_user_required
def modifier(current_user):
    data = request.get_json(silent=True) or {}
    nom = (data.get("full_name") or "").strip()
    if len(nom) < 3:
        return jsonify(errors={"full_name": "Nom complet requis (3 caractères minimum)."}), 400
    current_user.full_name = nom
    db.session.commit()
    return jsonify(user=current_user.to_dict())


@profile_bp.post("/password")
@current_user_required
def changer_mot_de_passe(current_user):
    data = request.get_json(silent=True) or {}
    actuel = data.get("current_password") or ""
    nouveau = data.get("new_password") or ""

    if not current_user.check_password(actuel):
        return jsonify(errors={"current_password": "Mot de passe actuel incorrect."}), 400
    if not PASSWORD_RE.match(nouveau):
        return jsonify(
            errors={"new_password": "8 caractères minimum, avec majuscule, minuscule et chiffre."}
        ), 400

    current_user.set_password(nouveau)
    db.session.commit()
    return jsonify(message="Mot de passe modifié.")


@profile_bp.get("/data")
@current_user_required
def exporter_donnees(current_user):
    """Droit d'accès : export des données personnelles de l'utilisateur."""
    candidatures = Application.query.filter_by(candidate_id=current_user.id).all()
    return jsonify(
        compte=current_user.to_dict(),
        candidatures=[
            {
                "offre": c.offer.title if c.offer else None,
                "statut": c.status,
                "score": c.score,
                "deposee_le": c.created_at.isoformat(),
            }
            for c in candidatures
        ],
    )


@profile_bp.delete("")
@current_user_required
def supprimer_compte(current_user):
    """Droit à l'effacement : supprime le compte et ses candidatures."""
    if current_user.role and current_user.role.name == "admin":
        return jsonify(error="Un administrateur ne peut pas supprimer son propre compte."), 400

    Application.query.filter_by(candidate_id=current_user.id).delete()
    db.session.delete(current_user)
    db.session.commit()
    return jsonify(message="Compte supprimé.")
