"""Commandes d'administration en ligne de commande.

    flask users                       liste les comptes
    flask reset-password <email>      réinitialise un mot de passe
"""
import click
from flask.cli import with_appcontext

from .extensions import db
from .models.user import User

MOT_DE_PASSE_PAR_DEFAUT = "Passe@1234"


@click.command("users")
@with_appcontext
def lister_utilisateurs():
    """Affiche les comptes existants avec leur rôle."""
    comptes = User.query.order_by(User.id).all()
    if not comptes:
        click.echo("Aucun compte. Lancez `flask seed`.")
        return

    click.echo(f"\n{'ID':<4} {'EMAIL':<34} {'RÔLE':<12} {'NOM':<24} ACTIF")
    click.echo("-" * 88)
    for u in comptes:
        role = u.role.name if u.role else "—"
        click.echo(
            f"{u.id:<4} {u.email:<34} {role:<12} {u.full_name:<24} "
            f"{'oui' if u.is_active else 'non'}"
        )
    click.echo(
        "\nMot de passe oublié : flask reset-password <email>\n"
    )


@click.command("reset-password")
@click.argument("email")
@click.option("--password", default=MOT_DE_PASSE_PAR_DEFAUT, help="Nouveau mot de passe.")
@with_appcontext
def reinitialiser_mot_de_passe(email, password):
    """Réinitialise le mot de passe d'un compte."""
    utilisateur = User.query.filter_by(email=email.strip().lower()).first()
    if utilisateur is None:
        click.echo(f"Aucun compte avec l'adresse {email}.")
        click.echo("Utilisez `flask users` pour voir la liste.")
        return

    utilisateur.set_password(password)
    utilisateur.is_active = True
    db.session.commit()
    click.echo(f"Mot de passe réinitialisé : {utilisateur.email} / {password}")
