"""Commande `flask demo` : peuple la base d'un jeu de démonstration cohérent.

Objectif : disposer d'une plateforme suffisamment vivante pour que les
tableaux de bord, l'entonnoir et les listes soient représentatifs, sans
avoir à saisir manuellement des dizaines d'enregistrements.

Les candidatures sont réparties sur les deux derniers mois afin que la
courbe d'activité soit lisible, et leurs statuts échelonnés pour que
l'entonnoir présente des taux de conversion réalistes.
"""
import os
import random
from datetime import datetime, timedelta, timezone

import click
from flask import current_app
from flask.cli import with_appcontext

from .demo_data import CANDIDATS, OFFRES, RECRUTEURS, texte_cv
from .demo_profils import (
    OFFRES_SUPPLEMENTAIRES,
    generer_candidats,
    generer_cas_douteux,
)
from .extensions import db
from .models.ai_metric import AiMetric
from .models.application import Application
from .models.job_offer import JobOffer
from .models.notification import Notification
from .models.role import Role
from .models.user import User
from .services import notifications as notifs
from .services.analyse import analyser_candidature
from .services.generateur_pdf import ecrire_cv_pdf

MOT_DE_PASSE = "Demo@1234"

# Repartition des statuts selon la qualite du profil : un bon profil progresse
# davantage dans le processus, ce qui produit un entonnoir credible.
PROGRESSION = {
    "excellent": ["hired", "interview", "interview", "shortlisted"],
    "bon": ["interview", "shortlisted", "shortlisted", "under_review"],
    "moyen": ["under_review", "received", "rejected"],
    "ecarte": ["rejected", "received"],
}


def _horodatage(jours_avant):
    return datetime.now(timezone.utc) - timedelta(days=jours_avant)


def _dernier_identifiant_notification():
    dernier = db.session.query(db.func.max(Notification.id)).scalar()
    return dernier or 0


def _dater_notifications(depuis, quand, lue):
    """Recale les notifications qui viennent d'être produites.

    Les fonctions de notification horodatent au moment de l'appel. Sur un jeu
    de démonstration reconstituant deux mois d'activité, toutes se
    retrouveraient à la même seconde : on les replace donc à la date de
    l'événement qui les a provoquées, et on marque comme lues les plus
    anciennes pour que le compteur de non-lues reste vraisemblable.
    """
    db.session.flush()
    Notification.query.filter(Notification.id > depuis).update(
        {"created_at": quand.replace(tzinfo=None), "is_read": lue},
        synchronize_session=False,
    )


def _obtenir_role(nom):
    role = Role.query.filter_by(name=nom).first()
    if role is None:
        raise click.ClickException(
            f"Rôle « {nom} » introuvable. Lancez d'abord `flask seed`."
        )
    return role


def _creer_utilisateur(donnees, role, statut="active", cree_il_y_a=60):
    existant = User.query.filter_by(email=donnees["email"]).first()
    if existant:
        return existant, False

    utilisateur = User(
        email=donnees["email"],
        full_name=donnees["full_name"],
        role=role,
        status=statut,
        company=donnees.get("company"),
        phone=donnees.get("phone"),
        created_at=_horodatage(cree_il_y_a),
        approved_at=_horodatage(cree_il_y_a) if statut == "active" else None,
    )
    utilisateur.set_password(MOT_DE_PASSE)
    db.session.add(utilisateur)
    return utilisateur, True


@click.command("demo")
@click.option("--reset", is_flag=True, help="Efface le jeu de démonstration existant.")
@with_appcontext
def demo_command(reset):
    """Crée comptes, offres, CV et candidatures de démonstration."""
    aleatoire = random.Random(42)  # reproductible d'une execution a l'autre

    role_recruteur = _obtenir_role("recruiter")
    role_candidat = _obtenir_role("candidate")

    if reset:
        _effacer(role_recruteur, role_candidat)

    # ------------------------------------------------ Recruteurs
    recruteurs = {}
    nouveaux_recruteurs = 0
    for donnees in RECRUTEURS:
        depuis = _dernier_identifiant_notification()
        utilisateur, cree = _creer_utilisateur(
            donnees, role_recruteur, statut=donnees["status"], cree_il_y_a=70
        )
        recruteurs[donnees["company"]] = utilisateur
        nouveaux_recruteurs += cree
        if cree:
            db.session.flush()
            notifs.bienvenue(utilisateur)
            if utilisateur.status == "pending":
                notifs.recruteur_en_attente(utilisateur)
            _dater_notifications(depuis, _horodatage(70), lue=True)
    db.session.flush()

    proprietaires = [u for u in recruteurs.values() if u.status == "active"]

    # ------------------------------------------------ Offres
    catalogue = OFFRES + OFFRES_SUPPLEMENTAIRES
    offres = {}
    nouvelles_offres = 0
    for index, donnees in enumerate(catalogue):
        existante = JobOffer.query.filter_by(title=donnees["title"]).first()
        if existante:
            offres[donnees["title"]] = existante
            continue

        # Les offres sont echelonnees sur trois mois : la courbe d'activite y
        # gagne en relief, et les delais de traitement deviennent parlants.
        offre = JobOffer(
            recruiter=proprietaires[index % len(proprietaires)],
            created_at=_horodatage(88 - index * 6),
            **donnees,
        )
        db.session.add(offre)
        offres[donnees["title"]] = offre
        nouvelles_offres += 1

        depuis = _dernier_identifiant_notification()
        db.session.flush()
        notifs.offre_publiee(offre)
        _dater_notifications(depuis, offre.created_at, lue=True)
    db.session.flush()

    # ------------------------------------------------ Candidats et candidatures
    dossier = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(dossier, exist_ok=True)

    nouveaux_candidats = 0
    nouvelles_candidatures = 0
    echecs = []

    # Les seize candidats redigees a la main couvrent les cas remarquables ;
    # les profils composes donnent a la plateforme le volume qui rend les
    # tableaux de bord et les rapports decisionnels representatifs.
    noms_pris = {c["full_name"] for c in CANDIDATS}
    population = CANDIDATS + generer_candidats(
        catalogue, aleatoire, par_offre=5, noms_utilises=noms_pris
    )
    # Dossiers construits pour declencher les controles d'anomalies : sans eux
    # l'ecran de controle resterait vide et la fonction indemontrable.
    population += generer_cas_douteux(catalogue, aleatoire, noms_utilises=noms_pris)

    for candidat in population:
        depuis_compte = _dernier_identifiant_notification()
        utilisateur, cree = _creer_utilisateur(
            candidat, role_candidat, cree_il_y_a=aleatoire.randint(20, 80)
        )
        nouveaux_candidats += cree
        db.session.flush()
        if cree:
            notifs.bienvenue(utilisateur)
            _dater_notifications(depuis_compte, _horodatage(60), lue=True)

        offre = offres.get(candidat["offre"])
        if offre is None:
            continue
        if Application.query.filter_by(
            candidate_id=utilisateur.id, offer_id=offre.id
        ).first():
            continue

        # CV au format PDF, lu ensuite par la chaine d'analyse standard
        chemin = os.path.join(dossier, f"demo_{utilisateur.id}.pdf")
        ecrire_cv_pdf(chemin, texte_cv(candidat))

        depose_il_y_a = aleatoire.randint(1, 75)
        candidature = Application(
            cv_path=chemin,
            candidate=utilisateur,
            offer=offre,
            created_at=_horodatage(depose_il_y_a),
            status=aleatoire.choice(PROGRESSION[candidat["qualite"]]),
        )

        try:
            analyser_candidature(candidature, chemin_cv=chemin)
        except Exception as exc:  # noqa: BLE001
            echecs.append(f"{candidat['full_name']} : {exc}")

        # analyser_candidature ecrase le statut par defaut : on le retablit
        candidature.status = aleatoire.choice(PROGRESSION[candidat["qualite"]])

        db.session.add(candidature)
        db.session.flush()
        db.session.add(
            AiMetric(
                application_id=candidature.id,
                payload={"evenement": "demo", "qualite_attendue": candidat["qualite"]},
            )
        )

        # Historique de notifications : sans lui, la plateforme paraitrait
        # n'avoir jamais rien signale a personne.
        depuis = _dernier_identifiant_notification()
        notifs.candidature_recue(candidature)
        notifs.score_eleve(candidature)
        if candidature.status != "received":
            notifs.statut_change(candidature, "received")
        # Au-dela d'une semaine, une notification a ete vue : le compteur de
        # non-lues ne doit refleter que l'activite recente.
        _dater_notifications(
            depuis, candidature.created_at, lue=depose_il_y_a > 7
        )

        nouvelles_candidatures += 1

    db.session.commit()

    # ------------------------------------------------ Restitution
    click.echo("")
    click.echo("Jeu de démonstration en place")
    click.echo("-" * 52)
    click.echo(f"  Recruteurs créés     : {nouveaux_recruteurs}")
    click.echo(f"  Candidats créés      : {nouveaux_candidats}")
    click.echo(f"  Offres publiées      : {nouvelles_offres}")
    click.echo(f"  Candidatures déposées: {nouvelles_candidatures}")

    if echecs:
        click.echo("")
        click.echo("  Analyses en échec :")
        for message in echecs:
            click.echo(f"    - {message}")

    _afficher_resume()


def _afficher_resume():
    """Contrôle de cohérence : les scores obtenus doivent refléter les profils."""
    candidatures = Application.query.filter(Application.score.isnot(None)).all()
    if not candidatures:
        click.echo("\n  Aucun score calculé.")
        return

    scores = sorted((c.score for c in candidatures), reverse=True)
    retenues = [s for s in scores if s >= 50]

    click.echo("")
    click.echo("Contrôle des scores")
    click.echo("-" * 52)
    click.echo(f"  Candidatures analysées : {len(scores)}")
    click.echo(f"  Score le plus élevé    : {scores[0]}/100")
    click.echo(f"  Score le plus faible   : {scores[-1]}/100")
    click.echo(f"  Au-dessus du seuil (50): {len(retenues)}")
    click.echo("")
    click.echo("Comptes de démonstration (mot de passe : " + MOT_DE_PASSE + ")")
    click.echo("-" * 52)
    for r in RECRUTEURS:
        etat = "en attente de validation" if r["status"] == "pending" else "actif"
        click.echo(f"  {r['email']:38} recruteur, {etat}")
    click.echo(f"  {CANDIDATS[0]['email']:38} candidat")
    click.echo("")


def _effacer(role_recruteur, role_candidat):
    """Supprime les enregistrements de démonstration, sans toucher au reste.

    Le repérage ne peut pas se fonder sur les seules listes écrites à la main :
    la majorité des candidats sont composés à l'exécution, et leurs adresses ne
    figurent nulle part. Tous les comptes en `@example.ma` sont donc visés —
    domaine réservé à la démonstration — ainsi que les recruteurs nommément
    déclarés.

    L'ordre compte : les offres doivent partir avant leurs propriétaires.
    `job_offers.recruiter_id` étant NOT NULL, supprimer un recruteur dont une
    offre subsiste ferait échouer la transaction.
    """
    emails = [d["email"] for d in RECRUTEURS] + [c["email"] for c in CANDIDATS]
    # Le catalogue complet, offres supplementaires comprises : en omettre
    # laisserait des offres sans proprietaire.
    titres = [o["title"] for o in OFFRES + OFFRES_SUPPLEMENTAIRES]

    comptes = (
        User.query.filter(
            db.or_(
                User.email.in_(emails),
                User.email.like("%@example.ma"),
            )
        ).all()
    )
    identifiants = [u.id for u in comptes]

    if identifiants:
        candidatures = Application.query.filter(
            Application.candidate_id.in_(identifiants)
        ).all()
        for candidature in candidatures:
            AiMetric.query.filter_by(application_id=candidature.id).delete()
            if candidature.cv_path and os.path.exists(candidature.cv_path):
                try:
                    os.remove(candidature.cv_path)
                except OSError:
                    pass
            db.session.delete(candidature)
        Notification.query.filter(Notification.user_id.in_(identifiants)).delete(
            synchronize_session=False
        )

    # Offres visees par leur intitule, plus toute offre appartenant a un compte
    # de demonstration : sans ce second critere, une offre creee a la main par
    # un recruteur de demonstration bloquerait la suppression de son auteur.
    offres = JobOffer.query.filter(
        db.or_(
            JobOffer.title.in_(titres),
            JobOffer.recruiter_id.in_(identifiants) if identifiants else False,
        )
    ).all()
    for offre in offres:
        for candidature in list(offre.applications):
            AiMetric.query.filter_by(application_id=candidature.id).delete()
            db.session.delete(candidature)
        db.session.delete(offre)

    # Les offres partent d'abord : `recruiter_id` n'accepte pas la valeur nulle.
    db.session.flush()

    for compte in comptes:
        db.session.delete(compte)

    db.session.commit()
    click.echo("Jeu de démonstration précédent effacé.")
