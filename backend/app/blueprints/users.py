"""Administration : comptes, validation des recruteurs, rôles et permissions."""
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request

from ..extensions import db
from ..middleware.permissions import require_permission
from ..models.job_offer import JobOffer
from ..models.permission import Permission
from ..models.role import Role
from ..models.user import User
from ..services import notifications as notifs

users_bp = Blueprint("users", __name__)


def _maintenant():
    return datetime.now(timezone.utc)


# ---------------------------- Utilisateurs ----------------------------

@users_bp.get("/users")
@require_permission("manage_users")
def list_users(current_user):
    """Comptes actifs. La corbeille dispose de son propre point d'accès."""
    requete = User.query.filter(User.deleted_at.is_(None))
    statut = request.args.get("status")
    if statut:
        requete = requete.filter_by(status=statut)
    users = requete.order_by(User.id).all()
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

    # Un compte cree par un administrateur est actif d'emblee : la validation
    # ne concerne que les inscriptions spontanees.
    user = User(
        email=email,
        full_name=data["full_name"].strip(),
        role=role,
        status="active",
        company=(data.get("company") or "").strip() or None,
        phone=(data.get("phone") or "").strip() or None,
        approved_at=_maintenant(),
    )
    user.set_password(data["password"])
    db.session.add(user)
    db.session.flush()
    notifs.compte_cree(user, auteur=current_user)
    db.session.commit()
    return jsonify(user=user.to_dict()), 201


@users_bp.patch("/users/<int:user_id>")
@require_permission("manage_users")
def update_user(current_user, user_id):
    user = User.query.get_or_404(user_id)
    data = request.get_json(silent=True) or {}

    if "full_name" in data:
        user.full_name = data["full_name"].strip()
    if "company" in data:
        user.company = (data["company"] or "").strip() or None
    if "phone" in data:
        user.phone = (data["phone"] or "").strip() or None
    if "is_active" in data:
        if user.est_administrateur and not data["is_active"]:
            return jsonify(error="Un compte administrateur ne peut être désactivé."), 400
        nouvel_etat = bool(data["is_active"])
        # L'interesse doit savoir qu'il perd ou retrouve l'acces : sans cela,
        # il decouvrirait le changement au moment d'echouer a se connecter.
        if nouvel_etat != user.is_active:
            if nouvel_etat:
                notifs.compte_reactive(user, auteur=current_user)
            else:
                notifs.compte_desactive(user, auteur=current_user)
        user.is_active = nouvel_etat
    if "role" in data:
        role = Role.query.filter_by(name=data["role"]).first()
        if role is None:
            return jsonify(error=f"Rôle inconnu : {data['role']}"), 400
        if user.id == current_user.id and user.est_administrateur:
            return jsonify(error="Vous ne pouvez pas modifier votre propre rôle."), 400
        user.role = role

    db.session.commit()
    return jsonify(user=user.to_dict())


# ------------------ Validation des comptes recruteurs ------------------

@users_bp.get("/users/pending")
@require_permission("manage_users")
def list_pending(current_user):
    """Demandes de comptes recruteurs en attente de décision."""
    from ..services.qualification_recruteur import qualifier

    demandes = (
        User.query.filter_by(status="pending")
        .filter(User.deleted_at.is_(None))
        .order_by(User.created_at)
        .all()
    )

    # Chaque demande est accompagnee d'un faisceau d'indices : nature de
    # l'adresse, anteriorite du domaine, ressemblance avec un domaine deja
    # valide. Rien n'est bloquant — l'administrateur decide, mais il decide
    # en voyant ce qu'il ne voyait pas.
    connus = User.query.filter(User.deleted_at.is_(None)).all()

    return jsonify(
        users=[
            {**u.to_dict(), "qualification": qualifier(u, connus)} for u in demandes
        ],
        total=len(demandes),
    )


@users_bp.post("/users/<int:user_id>/approve")
@require_permission("manage_users")
def approve_user(current_user, user_id):
    user = User.query.get_or_404(user_id)
    if user.status == "active":
        return jsonify(error="Ce compte est déjà validé."), 400

    user.status = "active"
    user.is_active = True
    user.approved_at = _maintenant()
    user.rejection_reason = None
    notifs.compte_approuve(user, approbateur=current_user)
    db.session.commit()
    return jsonify(user=user.to_dict(), message=f"Compte de {user.full_name} validé.")


@users_bp.post("/users/<int:user_id>/reject")
@require_permission("manage_users")
def reject_user(current_user, user_id):
    user = User.query.get_or_404(user_id)
    motif = (request.get_json(silent=True) or {}).get("reason", "").strip()

    user.status = "rejected"
    user.is_active = False
    user.rejection_reason = motif or None
    notifs.compte_refuse(user, motif)
    db.session.commit()
    return jsonify(user=user.to_dict(), message="Demande refusée.")


# ------------------------ Corbeille ------------------------

@users_bp.delete("/users/<int:user_id>")
@require_permission("manage_users")
def delete_user(current_user, user_id):
    """Suppression logique : le compte part en corbeille, restaurable."""
    if user_id == current_user.id:
        return jsonify(error="Impossible de supprimer son propre compte."), 400

    user = User.query.get_or_404(user_id)
    if user.est_administrateur:
        return jsonify(error="Un compte administrateur ne peut être supprimé."), 400
    if user.is_deleted:
        return jsonify(error="Ce compte est déjà dans la corbeille."), 400

    user.deleted_at = _maintenant()
    user.is_active = False
    notifs.compte_supprime(user, auteur=current_user)
    db.session.commit()
    return jsonify(message=f"{user.full_name} placé dans la corbeille.")


@users_bp.get("/trash")
@require_permission("manage_users")
def list_trash(current_user):
    """Contenu de la corbeille : comptes et offres supprimés."""
    comptes = (
        User.query.filter(User.deleted_at.isnot(None))
        .order_by(User.deleted_at.desc())
        .all()
    )
    offres = (
        JobOffer.query.filter(JobOffer.deleted_at.isnot(None))
        .order_by(JobOffer.deleted_at.desc())
        .all()
    )
    return jsonify(
        users=[u.to_dict() for u in comptes],
        offers=[o.to_dict() for o in offres],
        total=len(comptes) + len(offres),
    )


@users_bp.post("/users/<int:user_id>/restore")
@require_permission("manage_users")
def restore_user(current_user, user_id):
    user = User.query.get_or_404(user_id)
    if not user.is_deleted:
        return jsonify(error="Ce compte n'est pas dans la corbeille."), 400

    user.deleted_at = None
    user.is_active = True
    notifs.compte_restaure(user, auteur=current_user)
    db.session.commit()
    return jsonify(user=user.to_dict(), message=f"{user.full_name} restauré.")


@users_bp.delete("/users/<int:user_id>/purge")
@require_permission("manage_users")
def purge_user(current_user, user_id):
    """Suppression définitive, réservée aux éléments déjà en corbeille."""
    user = User.query.get_or_404(user_id)
    if not user.is_deleted:
        return jsonify(error="Placez d'abord ce compte dans la corbeille."), 400
    if user.est_administrateur:
        return jsonify(error="Un compte administrateur ne peut être supprimé."), 400

    db.session.delete(user)
    db.session.commit()
    return jsonify(message="Compte supprimé définitivement.")


# ---------------------- Rôles et permissions ----------------------

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

    # Le role administrateur conserve toujours la main sur les comptes et
    # les droits : sans cette garde, la plateforme pourrait devenir
    # definitivement ingerable.
    if role.name == "admin":
        for indispensable in ("manage_users", "manage_roles"):
            if indispensable not in codes:
                return jsonify(
                    error="Le rôle administrateur doit conserver la gestion "
                          "des comptes et des permissions."
                ), 400

    perms = Permission.query.filter(Permission.code.in_(codes)).all()
    found = {p.code for p in perms}
    unknown = [c for c in codes if c not in found]
    if unknown:
        return jsonify(error=f"Permissions inconnues : {', '.join(unknown)}"), 400

    role.permissions = perms
    notifs.permissions_modifiees(role, auteur=current_user)
    db.session.commit()
    return jsonify(role=role.to_dict())
