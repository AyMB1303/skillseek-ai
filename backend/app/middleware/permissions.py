"""RBAC temps réel (RG-02 du cahier des charges).

Le JWT ne contient QUE l'identité de l'utilisateur. Les permissions sont
relues en base de données À CHAQUE requête sensible : si l'administrateur
révoque un droit, la requête suivante de l'utilisateur est refusée,
sans attendre l'expiration du token.
"""
from functools import wraps

from flask import jsonify
from flask_jwt_extended import get_jwt_identity, jwt_required, verify_jwt_in_request

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

        # Les codes exigés sont inscrits sur la fonction elle-même. Sans cela
        # ils resteraient enfermés dans la fermeture, invisibles de
        # l'extérieur — et la description de l'API devrait les recopier à la
        # main, avec la dérive que cela suppose. Ici, la documentation lit ce
        # que le contrôle applique : les deux ne peuvent pas diverger.
        wrapper.__permissions_requises__ = tuple(codes)
        wrapper.__authentification_requise__ = True
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

    # Authentification exigée, mais aucune permission particulière.
    wrapper.__permissions_requises__ = ()
    wrapper.__authentification_requise__ = True
    return wrapper


def jeton_requis(**options):
    """Exige un jeton valide, sans recharger l'utilisateur ni vérifier de droit.

    Enveloppe le décorateur de la bibliothèque plutôt que de l'employer
    directement, pour une raison qui n'apparaît qu'ailleurs : le contrat
    d'API est construit en relevant les marques posées ici. Une route
    protégée par le décorateur brut n'en porte aucune, et se retrouverait
    publiée comme ouverte alors qu'elle exige un jeton — une documentation
    fausse dans le sens le plus gênant.

    Réservé aux trois routes du cycle de vie du jeton : rafraîchissement,
    révocation, et lecture de l'identité courante. Partout ailleurs, c'est
    « require_permission » qui s'applique.
    """

    def decorator(fn):
        protegee = jwt_required(**options)(fn)
        protegee.__permissions_requises__ = ()
        protegee.__authentification_requise__ = True
        return protegee

    return decorator
