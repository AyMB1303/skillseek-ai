"""RBAC temps réel (RG-02 du cahier des charges).

Le JWT ne contient QUE l'identité de l'utilisateur. Les permissions sont
relues en base de données À CHAQUE requête sensible : si l'administrateur
révoque un droit, la requête suivante de l'utilisateur est refusée,
sans attendre l'expiration du token.
"""
from functools import wraps

from flask import jsonify
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request

from ..extensions import db
from ..models.user import User


def _load_current_user():
    """Recharge l'utilisateur depuis la BDD (API SQLAlchemy 2.0)."""
    return db.session.get(User, int(get_jwt_identity()))


def require_permission(*codes: str):
    """Protège une route : l'utilisateur doit posséder TOUTES les permissions.

    Usage:
        @users_bp.get("/users")
        @require_permission("manage_users")
        def list_users(current_user): ...

    La fonction décorée reçoit l'utilisateur courant en premier argument.
    """

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            user = _load_current_user()

            if user is None or not user.is_active:
                return jsonify(error="Compte inexistant ou désactivé."), 401

            # Verification EN BASE a chaque appel -> revocation immediate
            missing = [c for c in codes if not user.has_permission(c)]
            if missing:
                return (
                    jsonify(
                        error="Permission refusée.",
                        missing_permissions=missing,
                    ),
                    403,
                )

            return fn(user, *args, **kwargs)

        return wrapper

    return decorator


def current_user_required(fn):
    """Route accessible à tout utilisateur connecté et actif (sans permission)."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        user = _load_current_user()
        if user is None or not user.is_active:
            return jsonify(error="Compte inexistant ou désactivé."), 401
        return fn(user, *args, **kwargs)

    return wrapper
