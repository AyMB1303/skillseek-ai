"""Authentification : inscription, connexion, refresh, déconnexion (S1-06)."""
import math
import re
from datetime import datetime, timezone

from flask import Blueprint, current_app, jsonify, request
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
from ..services import notifications as notifs

auth_bp = Blueprint("auth", __name__)

EMAIL_RE = re.compile(r"^[\w.+-]+@[\w-]+\.[\w.-]+$")
# Au moins 8 caracteres, une majuscule, une minuscule, un chiffre
PASSWORD_RE = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$")


def _minutes_restantes(echeance):
    """Attente restante, arrondie à la minute supérieure.

    Les dates lues depuis SQLite reviennent sans fuseau ; la comparaison se
    fait dans le référentiel de l'échéance pour éviter une exception là où le
    besoin est simplement d'afficher un délai.
    """
    maintenant = datetime.now(timezone.utc)
    if echeance.tzinfo is None:
        maintenant = maintenant.replace(tzinfo=None)
    return max(1, math.ceil((echeance - maintenant).total_seconds() / 60))


def _validate_registration(data: dict):
    errors = {}
    if not data.get("full_name") or len(data["full_name"].strip()) < 3:
        errors["full_name"] = "Nom complet requis (3 caractères minimum)."
    if not data.get("email") or not EMAIL_RE.match(data["email"]):
        errors["email"] = "Adresse email invalide."
    if not data.get("password") or not PASSWORD_RE.match(data["password"]):
        errors["password"] = (  # nosec B105
            "Mot de passe : 8 caractères min., une majuscule, "
            "une minuscule et un chiffre."
        )
    return errors


@auth_bp.post("/register")
def register():
    """Inscription publique : candidat ou recruteur.

    Un candidat est actif immédiatement. Un recruteur est placé en attente :
    publier des offres au nom d'une entreprise engage celle-ci, un
    administrateur doit donc valider le compte au préalable. Les rôles
    d'administration ne sont jamais accessibles par cette voie.
    """
    data = request.get_json(silent=True) or {}
    errors = _validate_registration(data)

    demande = (data.get("role") or "candidate").strip().lower()
    if demande not in ("candidate", "recruiter"):
        errors["role"] = "Type de compte invalide."
    # L'entreprise n'est plus exigee : le domaine de l'adresse en dit souvent
    # davantage, et l'ecran de validation presente desormais a l'administrateur
    # un faisceau d'indices — nature de l'adresse, comptes deja valides sur le
    # meme domaine, ressemblance avec un domaine connu. Reclamer une
    # declaration invérifiable ajoutait une friction sans rien garantir.

    if errors:
        return jsonify(errors=errors), 400

    email = data["email"].strip().lower()
    if User.query.filter_by(email=email).first():
        return jsonify(error="Un compte existe déjà avec cet email."), 409

    role = Role.query.filter_by(name=demande).first()
    if role is None:
        return jsonify(error="Rôles non initialisés (lancer `flask seed`)."), 500

    user = User(
        email=email,
        full_name=data["full_name"].strip(),
        role=role,
        status="pending" if demande == "recruiter" else "active",
        company=(data.get("company") or "").strip() or None,
        phone=(data.get("phone") or "").strip() or None,
    )
    user.set_password(data["password"])
    db.session.add(user)
    db.session.flush()

    notifs.bienvenue(user)
    if demande == "recruiter":
        notifs.recruteur_en_attente(user)

    db.session.commit()

    message = (
        "Compte créé. Il doit être validé par un administrateur avant "
        "votre première connexion."
        if demande == "recruiter"
        else "Compte créé. Vous pouvez vous connecter."
    )
    return jsonify(message=message, user=user.to_dict(), pending=demande == "recruiter"), 201


@auth_bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    user = User.query.filter_by(email=email).first()

    # Verrou temporaire apres echecs repetes.
    #
    # Il est verifie AVANT le mot de passe : sans cela, un essai systematique
    # continuerait a distinguer un mot de passe juste d'un mot de passe faux
    # pendant toute la duree du verrou, et le verrou ne servirait a rien.
    if user is not None and user.est_verrouille:
        minutes = _minutes_restantes(user.locked_until)
        return jsonify(
            error=f"Trop de tentatives infructueuses. Réessayez dans {minutes} minute(s).",
            retry_after_minutes=minutes,
        ), 429

    # Message volontairement identique (email inconnu vs mauvais mot de passe)
    if user is None or not user.check_password(password):
        if user is not None:
            # Le compteur est porte par le compte vise, et l'alerte lui est
            # adressee : celui qui essaie les mots de passe n'apprend rien.
            user.failed_logins = (user.failed_logins or 0) + 1
            seuil = current_app.config["SEUIL_VERROU_CONNEXION"]
            if user.failed_logins >= seuil:
                user.locked_until = (
                    datetime.now(timezone.utc)
                    + current_app.config["DUREE_VERROU_CONNEXION"]
                )
            notifs.connexions_echouees(user, user.failed_logins)
            db.session.commit()
        return jsonify(error="Identifiants invalides."), 401

    if user.is_deleted:
        return jsonify(error="Ce compte n'existe plus."), 403
    if user.status == "pending":
        return jsonify(
            error="Votre compte recruteur est en attente de validation par un administrateur.",
            status="pending",
        ), 403
    if user.status == "rejected":
        return jsonify(
            error=user.rejection_reason or "Votre demande de compte recruteur a été refusée.",
            status="rejected",
        ), 403
    if not user.is_active:
        return jsonify(error="Compte désactivé. Contactez un administrateur."), 403

    if user.failed_logins or user.locked_until:
        user.failed_logins = 0      # une connexion reussie clot la serie
        user.locked_until = None
        db.session.commit()

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
