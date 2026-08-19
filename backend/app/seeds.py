"""Commande `flask seed` : rôles, permissions et compte admin initial."""
import os

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
    # Controle des candidatures : partage entre recruteurs et administrateurs.
    # Une permission dediee plutot qu'une reutilisation de `view_applications` :
    # un administrateur doit pouvoir traiter une alerte de securite sans se
    # voir ouvrir pour autant l'ensemble des dossiers de candidature.
    "view_signalements": "Consulter les signalements sur les candidatures",
    "manage_signalements": "Traiter et clore les signalements",
}

ROLES = {
    # L'assistant est ouvert a l'administrateur, mais sur un domaine distinct :
    # comptes, droits, signalements, journal. Il ne lui donne pas acces au
    # contenu des candidatures, faute de `view_applications` — la conversation
    # ne doit pas contourner le modele de droits.
    "admin": [
        "manage_users", "manage_roles", "use_chatbot",
        "view_signalements", "manage_signalements",
    ],
    "recruiter": [
        "manage_offers",
        "view_applications",
        "manage_applications",
        "view_dashboard",
        "use_chatbot",
        "view_signalements",
        "manage_signalements",
    ],
    "candidate": [],
}

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@skillseek.local")
# Le mot de passe initial de l'administrateur se surcharge par l'environnement.
# La valeur de repli reste celle documentee pour la demonstration : un
# deploiement reel doit definir ADMIN_PASSWORD, et cette variable est le seul
# endroit ou le changer.
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Admin@1234")


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
            email=ADMIN_EMAIL,
            full_name="Administrateur",
            role=roles["admin"],
            status="active",
        )
        admin.set_password(ADMIN_PASSWORD)
        db.session.add(admin)
        click.echo(f"Admin créé : {ADMIN_EMAIL} / {ADMIN_PASSWORD}")

    db.session.commit()
    click.echo("Seed terminé : permissions, rôles et admin en place.")
