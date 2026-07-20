"""Administration : CRUD utilisateurs, rôles et permissions (S1-07 / RG-02)."""
from flask import Blueprint, jsonify, request

from ..extensions import db
from ..middleware.permissions import require_permission
from ..models.permission import Permission
from ..models.role import Role
from ..models.user import User

users_bp = Blueprint("users", __name__)


# ---------------------- Utilisateurs ----------------------

@users_bp.get("/users")
@require_permission("manage_users")
def list_users(current_user):
    users = User.query.order_by(User.id).all()
    return jsonify(users=[u.to_dict() for u in users])


@users_bp.post("/users")
@require_permission("manage_users")
def create_user(current_user):
    data = request.get_json(silent=True) or {}
    required = ("email", "password", "full_name", "role")
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify(error=f"Champs manquants : {', '.join(missing)}"), 400

    email = data["email"].strip().lower()
    if User.query.filter_by(email=email).first():
        return jsonify(error="Email déjà utilisé."), 409

    role = Role.query.filter_by(name=data["role"]).first()
    if role is None:
        return jsonify(error=f"Rôle inconnu : {data['role']}"), 400

    user = User(email=email, full_name=data["full_name"].strip(), role=role)
    user.set_password(data["password"])
    db.session.add(user)
    db.session.commit()
    return jsonify(user=user.to_dict()), 201


@users_bp.patch("/users/<int:user_id>")
@require_permission("manage_users")
def update_user(current_user, user_id):
    user = User.query.get_or_404(user_id)
    data = request.get_json(silent=True) or {}

    if "full_name" in data:
        user.full_name = data["full_name"].strip()
    if "is_active" in data:
        user.is_active = bool(data["is_active"])
    if "role" in data:
        role = Role.query.filter_by(name=data["role"]).first()
        if role is None:
            return jsonify(error=f"Rôle inconnu : {data['role']}"), 400
        user.role = role

    db.session.commit()
    return jsonify(user=user.to_dict())


@users_bp.delete("/users/<int:user_id>")
@require_permission("manage_users")
def delete_user(current_user, user_id):
    if user_id == current_user.id:
        return jsonify(error="Impossible de supprimer son propre compte."), 400
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    return jsonify(message="Utilisateur supprimé.")


# ---------------------- Rôles & permissions ----------------------

@users_bp.get("/roles")
@require_permission("manage_roles")
def list_roles(current_user):
    return jsonify(roles=[r.to_dict() for r in Role.query.order_by(Role.id).all()])


@users_bp.post("/roles")
@require_permission("manage_roles")
def create_role(current_user):
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip().lower()
    if not name:
        return jsonify(error="Nom du rôle requis."), 400
    if Role.query.filter_by(name=name).first():
        return jsonify(error="Ce rôle existe déjà."), 409

    role = Role(name=name, description=data.get("description", ""))
    db.session.add(role)
    db.session.commit()
    return jsonify(role=role.to_dict()), 201


@users_bp.get("/permissions")
@require_permission("manage_roles")
def list_permissions(current_user):
    perms = Permission.query.order_by(Permission.id).all()
    return jsonify(permissions=[p.to_dict() for p in perms])


@users_bp.put("/roles/<int:role_id>/permissions")
@require_permission("manage_roles")
def set_role_permissions(current_user, role_id):
    """Remplace les permissions d'un rôle.

    Effet IMMEDIAT pour tous les utilisateurs du rôle (RG-02) : les
    permissions étant relues en base à chaque requête, aucune attente
    d'expiration de token n'est nécessaire.
    """
    role = Role.query.get_or_404(role_id)
    data = request.get_json(silent=True) or {}
    codes = data.get("permissions")
    if not isinstance(codes, list):
        return jsonify(error="`permissions` doit être une liste de codes."), 400

    perms = Permission.query.filter(Permission.code.in_(codes)).all()
    found = {p.code for p in perms}
    unknown = [c for c in codes if c not in found]
    if unknown:
        return jsonify(error=f"Permissions inconnues : {', '.join(unknown)}"), 400

    role.permissions = perms
    db.session.commit()
    return jsonify(role=role.to_dict())
