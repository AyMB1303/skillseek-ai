"""Commande `flask seed` : rôles, permissions et compte admin initial."""
import click
from flask.cli import with_appcontext

from .extensions import db
from .models.permission import Permission
from .models.role import Role
from .models.user import User

PERMISSIONS = {
    "manage_users": "Créer, modifier, supprimer les utilisateurs",
    "manage_roles": "Gérer les rôles et leurs permissions",
    "manage_offers": "Créer et modifier les offres d'emploi",
    "view_applications": "Consulter toutes les candidatures",
    "manage_applications": "Changer le statut des candidatures",
    "view_dashboard": "Accéder au tableau de bord décisionnel",
    "use_chatbot": "Utiliser l'assistant RH",
}

ROLES = {
    "admin": ["manage_users", "manage_roles"],
    "recruiter": [
        "manage_offers",
        "view_applications",
        "manage_applications",
        "view_dashboard",
        "use_chatbot",
    ],
    "candidate": [],
}

ADMIN_EMAIL = "admin@skillseek.local"
ADMIN_PASSWORD = "Admin@1234"  # a changer immediatement en production


@click.command("seed")
@with_appcontext
def seed_command():
    """Initialise permissions, rôles et compte administrateur."""
    # Permissions
    perms = {}
    for code, description in PERMISSIONS.items():
        perm = Permission.query.filter_by(code=code).first()
        if perm is None:
            perm = Permission(code=code, description=description)
            db.session.add(perm)
        perms[code] = perm

    # Roles
    roles = {}
    for name, codes in ROLES.items():
        role = Role.query.filter_by(name=name).first()
        if role is None:
            role = Role(name=name, description=f"Rôle {name}")
            db.session.add(role)
        role.permissions = [perms[c] for c in codes]
        roles[name] = role

    # Admin
    if User.query.filter_by(email=ADMIN_EMAIL).first() is None:
        admin = User(
            email=ADMIN_EMAIL, full_name="Administrateur", role=roles["admin"]
        )
        admin.set_password(ADMIN_PASSWORD)
        db.session.add(admin)
        click.echo(f"Admin créé : {ADMIN_EMAIL} / {ADMIN_PASSWORD}")

    db.session.commit()
    click.echo("Seed terminé : permissions, rôles et admin en place.")
