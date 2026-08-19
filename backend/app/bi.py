"""Export des données décisionnelles (S4-03).

    docker compose exec backend flask bi-export

Power BI se connecte normalement à PostgreSQL en direct, ce qui donne des
rapports actualisables d'un clic. Cette commande fournit une **seconde voie**,
utile dans deux situations concrètes :

  * le connecteur PostgreSQL de Power BI exige le pilote Npgsql, dont
    l'installation n'est pas toujours possible sur un poste d'entreprise ;
  * une démonstration ou une soutenance se déroule parfois sans la base en
    fonctionnement, et des fichiers plats suffisent alors.

Les fichiers produits sont l'image exacte des vues décisionnelles : les mêmes
colonnes, les mêmes règles de gestion. Un rapport construit sur les fichiers
peut donc être rebasculé sur la connexion directe sans être refait.
"""
import csv
import os
from pathlib import Path

import click
from flask.cli import with_appcontext
from sqlalchemy import text

from .extensions import db

VUES = [
    ("bi_indicateurs", "indicateurs"),
    ("bi_offres", "offres"),
    ("bi_candidatures", "candidatures"),
    ("bi_entonnoir", "entonnoir"),
    ("bi_activite", "activite"),
    ("bi_competences", "competences"),
]


def _chemin_sql():
    """Localise le fichier des vues, dans le conteneur comme hors de lui.

    Dans le conteneur, `bi/` est monté à la racine de l'application ; en
    exécution locale, il se trouve un niveau au-dessus du dossier `backend`.
    """
    racine = Path(__file__).resolve()
    candidats = [
        parent / "bi" / "vues_decisionnelles.sql"
        for parent in racine.parents[:4]
    ]
    for chemin in candidats:
        if chemin.exists():
            return chemin
    return candidats[1]      # message d'erreur portant le chemin attendu


def _dossier(cible=None):
    chemin = Path(cible or os.getenv("BI_EXPORT_DIR", "/app/exports"))
    chemin.mkdir(parents=True, exist_ok=True)
    return chemin


@click.command("bi-creer-vues")
@with_appcontext
def creer_vues_command():
    """(Re)crée les vues décisionnelles dans la base."""
    chemin = _chemin_sql()
    if not chemin.exists():
        click.echo(f"Fichier introuvable : {chemin}")
        raise SystemExit(1)

    sql = chemin.read_text(encoding="utf-8")
    db.session.execute(text(sql))
    db.session.commit()

    click.echo("Vues décisionnelles créées :")
    for vue, _ in VUES:
        nombre = db.session.execute(text(f"SELECT COUNT(*) FROM {vue}")).scalar()  # nosec B608
        click.echo(f"  {vue:20} {nombre:>6} ligne(s)")


@click.command("bi-export")
@click.option("--vers", default=None, help="Dossier de destination des fichiers.")
@with_appcontext
def export_command(vers):
    """Exporte les vues décisionnelles au format CSV."""
    dossier = _dossier(vers)

    try:
        db.session.execute(text("SELECT 1 FROM bi_indicateurs"))
    except Exception:
        db.session.rollback()
        click.echo("Vues absentes. Lancez d'abord : flask bi-creer-vues")
        raise SystemExit(1)

    click.echo(f"Export vers {dossier}")
    for vue, fichier in VUES:
        resultat = db.session.execute(text(f"SELECT * FROM {vue}"))  # nosec B608
        colonnes = list(resultat.keys())
        lignes = resultat.fetchall()

        chemin = dossier / f"{fichier}.csv"
        # L'encodage UTF-8 avec marque d'ordre est celui qu'Excel et Power BI
        # reconnaissent sans intervention : sans elle, les accents sont
        # illisibles a l'ouverture.
        with chemin.open("w", encoding="utf-8-sig", newline="") as flux:
            redacteur = csv.writer(flux, delimiter=";")
            redacteur.writerow(colonnes)
            redacteur.writerows(lignes)

        click.echo(f"  {fichier + '.csv':22} {len(lignes):>6} ligne(s)")

    click.echo("\nDans Power BI : Obtenir les données -> Texte/CSV -> "
               "séparateur point-virgule.")


def enregistrer(app):
    app.cli.add_command(creer_vues_command)
    app.cli.add_command(export_command)
