"""Contrôle des candidatures : consultation et traitement des signalements.

Le périmètre suit la même logique que le reste de la plateforme : un recruteur
ne voit que les signalements portant sur ses propres offres, un administrateur
dispose de la vue d'ensemble. Un candidat n'y a jamais accès — il serait
malsain qu'il découvre un soupçon avant que quiconque l'ait vérifié.
"""
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from sqlalchemy.orm import joinedload

from ..extensions import db
from ..middleware.permissions import require_permission
from ..models.application import Application
from ..models.job_offer import JobOffer
from ..models.signalement import (
    SEVERITES,
    STATUTS,
    TYPES_MANUELS,
    Signalement,
)
from ..services import journal, notifications as notifs

signalements_bp = Blueprint("signalements", __name__)


def _requete_pour(utilisateur):
    """Restreint la requête au périmètre de l'utilisateur."""
    requete = (
        Signalement.query
        .options(
            joinedload(Signalement.application).joinedload(Application.candidate),
            joinedload(Signalement.application).joinedload(Application.offer),
        )
        .join(Application, Signalement.application_id == Application.id)
        .join(JobOffer, Application.offer_id == JobOffer.id)
    )
    if not utilisateur.est_administrateur:
        requete = requete.filter(JobOffer.recruiter_id == utilisateur.id)
    return requete


@signalements_bp.get("")
@require_permission("view_signalements")
def lister(current_user):
    """Liste les signalements, filtrable par statut et par gravité."""
    requete = _requete_pour(current_user)

    statut = request.args.get("statut")
    if statut in STATUTS:
        requete = requete.filter(Signalement.statut == statut)

    severite = request.args.get("severite")
    if severite in SEVERITES:
        requete = requete.filter(Signalement.severite == severite)

    trouves = requete.order_by(Signalement.created_at.desc()).limit(200).all()

    # Les compteurs portent sur l'ensemble du perimetre, non sur la page :
    # l'interface doit pouvoir afficher « 3 alertes » meme filtree autrement.
    tous = _requete_pour(current_user).all()
    return jsonify(
        signalements=[s.to_dict(avec_candidature=True) for s in trouves],
        compteurs={
            "total": len(tous),
            "nouveaux": sum(1 for s in tous if s.statut == "nouveau"),
            "alertes": sum(1 for s in tous if s.severite == "alerte"),
            "a_traiter": sum(1 for s in tous if s.statut in ("nouveau", "examine")),
            "par_type": _compter(tous, "type"),
            "par_severite": _compter(tous, "severite"),
        },
    )


def _compter(elements, attribut):
    compteurs = {}
    for element in elements:
        cle = getattr(element, attribut)
        compteurs[cle] = compteurs.get(cle, 0) + 1
    return compteurs


@signalements_bp.get("/candidature/<int:app_id>")
@require_permission("view_signalements")
def par_candidature(current_user, app_id):
    """Signalements portant sur une candidature précise."""
    trouves = (
        _requete_pour(current_user)
        .filter(Signalement.application_id == app_id)
        .order_by(Signalement.created_at.desc())
        .all()
    )
    return jsonify(signalements=[s.to_dict() for s in trouves])


@signalements_bp.post("")
@require_permission("manage_signalements")
def ouvrir(current_user):
    """Ouvre un signalement à la main sur une candidature.

    Les contrôles automatiques ne voient que ce que le document contient. Un
    recruteur, lui, peut téléphoner à un ancien employeur, reconnaître un
    diplôme qui n'existe pas, ou constater qu'un candidat en entretien ne
    ressemble pas à son curriculum. Cette voie existe pour cela : elle
    complète les contrôles, elle ne les double pas.
    """
    donnees = request.get_json(silent=True) or {}

    candidature = Application.query.get(donnees.get("application_id") or 0)
    if candidature is None:
        return jsonify(error="Candidature introuvable."), 404

    # Un recruteur ne signale que sur son propre perimetre.
    offre = candidature.offer
    if not current_user.est_administrateur and (
        offre is None or offre.recruiter_id != current_user.id
    ):
        return jsonify(error="Cette candidature ne relève pas de vos offres."), 403

    type_ = donnees.get("type")
    if type_ not in TYPES_MANUELS:
        return jsonify(
            error=f"Motif invalide. Attendu : {', '.join(TYPES_MANUELS)}."
        ), 400

    message = (donnees.get("message") or "").strip()
    # Un signalement sans explication ne vaut rien pour celui qui le relira :
    # la meme exigence s'applique a la machine et a l'humain.
    if len(message) < 10:
        return jsonify(error="Décrivez l'anomalie en quelques mots (10 caractères minimum)."), 400

    severite = donnees.get("severite")
    if severite not in SEVERITES:
        severite = "attention"

    signalement = Signalement(
        application=candidature,
        type=type_,
        severite=severite,
        message=message[:400],
        origine="manuel",
        created_by_id=current_user.id,
        details={
            "auteur": current_user.full_name,
            "lecture": "Observation portée par un recruteur, hors contrôle automatique.",
        },
    )
    db.session.add(signalement)
    db.session.flush()

    notifs.signalement_manuel(signalement, auteur=current_user)
    journal.tracer(
        "signalement_ouvert", auteur=current_user,
        objet_type="signalement", objet_id=signalement.id,
        objet_libelle=type_, candidature=candidature.id, severite=severite,
    )
    db.session.commit()

    return jsonify(signalement=signalement.to_dict(avec_candidature=True)), 201


@signalements_bp.get("/motifs")
@require_permission("view_signalements")
def motifs(current_user):
    """Motifs proposés au recruteur lorsqu'il ouvre un signalement."""
    return jsonify(
        types=list(TYPES_MANUELS),
        severites=list(SEVERITES),
    )


@signalements_bp.patch("/<int:signalement_id>")
@require_permission("manage_signalements")
def traiter(current_user, signalement_id):
    """Enregistre la décision humaine sur un signalement."""
    signalement = _requete_pour(current_user).filter(
        Signalement.id == signalement_id
    ).first()
    if signalement is None:
        return jsonify(error="Signalement introuvable."), 404

    donnees = request.get_json(silent=True) or {}
    statut = donnees.get("statut")
    if statut not in STATUTS:
        return jsonify(error=f"Statut invalide. Attendu : {', '.join(STATUTS)}."), 400

    commentaire = (donnees.get("commentaire") or "").strip()
    # Ecarter un signalement sans dire pourquoi priverait la trace de sa valeur :
    # c'est precisement la decision qu'il faudra pouvoir justifier plus tard.
    if statut == "ecarte" and not commentaire:
        return jsonify(error="Un motif est requis pour écarter un signalement."), 400

    signalement.statut = statut
    signalement.commentaire = commentaire or None
    signalement.reviewed_by_id = current_user.id
    signalement.reviewed_at = datetime.now(timezone.utc)

    if signalement.est_traite:
        notifs.signalement_traite(signalement, auteur=current_user)
    journal.tracer(
        "signalement_traite", auteur=current_user,
        objet_type="signalement", objet_id=signalement.id,
        objet_libelle=signalement.type,
        statut=statut, motif=commentaire or None,
        candidature=signalement.application_id,
    )

    db.session.commit()
    return jsonify(signalement=signalement.to_dict(avec_candidature=True))


@signalements_bp.get("/synthese")
@require_permission("view_signalements")
def synthese(current_user):
    """Indicateurs de contrôle, destinés au tableau de bord."""
    tous = _requete_pour(current_user).all()
    candidatures_signalees = {s.application_id for s in tous}

    return jsonify(
        total=len(tous),
        candidatures_concernees=len(candidatures_signalees),
        a_traiter=sum(1 for s in tous if s.statut in ("nouveau", "examine")),
        confirmes=sum(1 for s in tous if s.statut == "confirme"),
        ecartes=sum(1 for s in tous if s.statut == "ecarte"),
        par_severite=_compter(tous, "severite"),
        par_type=_compter(tous, "type"),
    )
