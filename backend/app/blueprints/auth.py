"""Authentification : inscription, connexion, refresh, déconnexion (S1-06)."""
import re

from flask import Blueprint, jsonify, request
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_jwt,
    get_jwt_identity,
    jwt_required,
)

from ..extensions import db
from ..models.role import Role
from ..models.token_blocklist import TokenBlocklist
from ..models.user import User

auth_bp = Blueprint("auth", __name__)

EMAIL_RE = re.compile(r"^[\w.+-]+@[\w-]+\.[\w.-]+$")
# Au moins 8 caracteres, une majuscule, une minuscule, un chiffre
PASSWORD_RE = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$")


def _validate_registration(data: dict):
    errors = {}
    if not data.get("full_name") or len(data["full_name"].strip()) < 3:
        errors["full_name"] = "Nom complet requis (3 caractères minimum)."
    if not data.get("email") or not EMAIL_RE.match(data["email"]):
        errors["email"] = "Adresse email invalide."
    if not data.get("password") or not PASSWORD_RE.match(data["password"]):
        errors["password"] = (
            "Mot de passe : 8 caractères min., une majuscule, "
            "une minuscule et un chiffre."
        )
    return errors


@auth_bp.post("/register")
def register():
    """Inscription publique -> toujours role 'candidate' (securite)."""
    data = request.get_json(silent=True) or {}
    errors = _validate_registration(data)
    if errors:
        return jsonify(errors=errors), 400

    email = data["email"].strip().lower()
    if User.query.filter_by(email=email).first():
        return jsonify(error="Un compte existe déjà avec cet email."), 409

    role = Role.query.filter_by(name="candidate").first()
    if role is None:
        return jsonify(error="Rôles non initialisés (lancer `flask seed`)."), 500

    user = User(email=email, full_name=data["full_name"].strip(), role=role)
    user.set_password(data["password"])
    db.session.add(user)
    db.session.commit()

    return jsonify(message="Compte créé.", user=user.to_dict()), 201


@auth_bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    user = User.query.filter_by(email=email).first()
    # Message volontairement identique (email inconnu vs mauvais mot de passe)
    if user is None or not user.check_password(password):
        return jsonify(error="Identifiants invalides."), 401
    if not user.is_active:
        return jsonify(error="Compte désactivé."), 403

    return jsonify(
        access_token=create_access_token(identity=str(user.id)),
        refresh_token=create_refresh_token(identity=str(user.id)),
        user=user.to_dict(),
    )


@auth_bp.post("/refresh")
@jwt_required(refresh=True)
def refresh():
    identity = get_jwt_identity()
    return jsonify(access_token=create_access_token(identity=identity))


@auth_bp.post("/logout")
@jwt_required(verify_type=False)
def logout():
    """Revoque le token presente (access OU refresh) via la blacklist."""
    jti = get_jwt()["jti"]
    db.session.add(TokenBlocklist(jti=jti))
    db.session.commit()
    return jsonify(message="Déconnecté.")


@auth_bp.get("/me")
@jwt_required()
def me():
    user = db.session.get(User, int(get_jwt_identity()))
    if user is None:
        return jsonify(error="Compte introuvable."), 404
    return jsonify(user=user.to_dict())
