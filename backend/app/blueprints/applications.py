"""Candidatures : dépôt du CV, consultation classée, changement de statut."""
import os
import uuid

from flask import Blueprint, current_app, jsonify, request, send_file

from ..extensions import db
from ..middleware.permissions import current_user_required, require_permission
from ..models.ai_metric import AiMetric
from ..models.application import STATUSES, Application
from ..models.job_offer import JobOffer
from ..services import notifications as notifs
from ..services.analyse import analyser_candidature
from ..services.scoring import calculer_score

applications_bp = Blueprint("applications", __name__)

# Formats acceptes par les systemes de suivi des candidatures
EXTENSIONS_AUTORISEES = {".pdf", ".docx"}
TAILLE_MAX = 5 * 1024 * 1024  # 5 Mo


@applications_bp.get("")
@require_permission("view_applications")
def list_applications(current_user):
    """Liste des candidatures, filtrable par offre et par statut."""
    requete = Application.query
    offre_id = request.args.get("offer_id", type=int)
    statut = request.args.get("status")
    if offre_id:
        requete = requete.filter_by(offer_id=offre_id)
    if statut:
        requete = requete.filter_by(status=statut)

    candidatures = requete.order_by(Application.score.desc().nullslast()).all()
    return jsonify(
        applications=[_serialiser(c) for c in candidatures],
        total=len(candidatures),
    )


@applications_bp.get("/mine")
@current_user_required
def my_applications(current_user):
    candidatures = (
        Application.query.filter_by(candidate_id=current_user.id)
        .order_by(Application.created_at.desc())
        .all()
    )
    # Le candidat ne voit pas son score (choix produit du cahier des charges).
    return jsonify(
        applications=[
            {
                "id": c.id,
                "status": c.status,
                "offer": {"id": c.offer.id, "title": c.offer.title} if c.offer else None,
                "created_at": c.created_at.isoformat(),
            }
            for c in candidatures
        ]
    )


@applications_bp.post("")
@current_user_required
def postuler(current_user):
    """Dépôt d'un CV : validation stricte du fichier puis scoring immédiat."""
    fichier = request.files.get("cv")
    offre_id = request.form.get("offer_id", type=int)

    if not fichier or not fichier.filename:
        return jsonify(error="Aucun fichier reçu."), 400
    extension = os.path.splitext(fichier.filename)[1].lower()
    if extension not in EXTENSIONS_AUTORISEES:
        return jsonify(
            error="Format non accepté : déposez votre CV au format PDF ou DOCX."
        ), 400

    fichier.seek(0, os.SEEK_END)
    taille = fichier.tell()
    fichier.seek(0)
    if taille > TAILLE_MAX:
        return jsonify(error="Fichier trop volumineux (5 Mo maximum)."), 400

    offre = JobOffer.query.get_or_404(offre_id)
    if Application.query.filter_by(candidate_id=current_user.id, offer_id=offre.id).first():
        return jsonify(error="Vous avez déjà postulé à cette offre."), 409

    dossier = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(dossier, exist_ok=True)
    nom = f"{uuid.uuid4().hex}{extension}"
    chemin = os.path.join(dossier, nom)
    fichier.save(chemin)

    candidature = Application(cv_path=chemin, candidate=current_user, offer=offre)

    # Analyse automatique immediate : extraction, profil, similarite, score.
    # Un echec de lecture n'empeche jamais l'enregistrement de la candidature ;
    # elle est alors signalee comme non analysable et reste traitable a la main.
    try:
        details = analyser_candidature(candidature, chemin_cv=chemin)
    except Exception as exc:  # noqa: BLE001 - on ne perd jamais une candidature
        current_app.logger.exception("Analyse du CV impossible : %s", exc)
        candidature.score = None
        candidature.score_details = {
            "statut": "analyse_indisponible",
            "message": "Le service d'analyse est momentanément indisponible.",
        }
        details = candidature.score_details

    db.session.add(candidature)
    db.session.flush()
    db.session.add(
        AiMetric(
            application_id=candidature.id,
            payload={
                "evenement": "depot_et_analyse",
                "fichier": os.path.basename(chemin),
                "resultat": details,
            },
        )
    )
    # Le recruteur proprietaire de l'offre est informe immediatement.
    notifs.candidature_recue(candidature)
    db.session.commit()

    return jsonify(application=_serialiser(candidature)), 201


@applications_bp.post("/<int:app_id>/analyze")
@require_permission("view_applications")
def analyser(current_user, app_id):
    """Calcule le score d'une candidature.

    Deux modes :
      * automatique (par défaut) : le CV est relu, le profil extrait et la
        proximité sémantique recalculée ;
      * manuel : le recruteur fournit lui-même le profil, ce qui reste
        nécessaire lorsqu'un document est illisible (scan de mauvaise qualité).
    """
    candidature = Application.query.get_or_404(app_id)
    data = request.get_json(silent=True) or {}
    profil_fourni = any(k in data for k in ("skills", "experience_years", "degree"))

    if profil_fourni:
        profil = {
            "skills": [s.strip().lower() for s in data.get("skills", []) if s.strip()],
            "experience_years": int(data.get("experience_years") or 0),
            "degree": data.get("degree") or None,
        }
        score, details = calculer_score(profil, candidature.offer)
        details["statut"] = "analysee"
        details["profil_analyse"] = profil
        details["saisie_manuelle"] = True
        candidature.score = score
        candidature.score_details = details
    else:
        details = analyser_candidature(candidature)

    db.session.add(
        AiMetric(
            application_id=candidature.id,
            payload={
                "evenement": "analyse_manuelle" if profil_fourni else "analyse_automatique",
                "resultat": details,
            },
        )
    )
    db.session.commit()
    return jsonify(application=_serialiser(candidature))


@applications_bp.patch("/<int:app_id>/status")
@require_permission("manage_applications")
def changer_statut(current_user, app_id):
    candidature = Application.query.get_or_404(app_id)
    statut = (request.get_json(silent=True) or {}).get("status")
    if statut not in STATUSES:
        return jsonify(error=f"Statut invalide. Valeurs possibles : {', '.join(STATUSES)}"), 400

    ancien = candidature.status
    candidature.status = statut
    # Le candidat est informe de l'evolution de SA candidature.
    notifs.statut_change(candidature, ancien)
    db.session.commit()
    return jsonify(application=_serialiser(candidature))


@applications_bp.get("/<int:app_id>/cv")
@require_permission("view_applications")
def telecharger_cv(current_user, app_id):
    candidature = Application.query.get_or_404(app_id)

    # Les CV deposes avant la correction du chemin peuvent etre en relatif :
    # on resout dans les deux cas pour rester compatible.
    chemin = candidature.cv_path
    if not os.path.isabs(chemin):
        chemin = os.path.join(current_app.config["UPLOAD_FOLDER"], os.path.basename(chemin))

    if not os.path.exists(chemin):
        return jsonify(error="Le fichier du CV est introuvable sur le serveur."), 404

    return send_file(
        chemin,
        mimetype="application/pdf",
        download_name=f"CV-{candidature.candidate.full_name}.pdf",
    )


def _serialiser(c):
    return {
        "id": c.id,
        "status": c.status,
        "score": c.score,
        "score_details": c.score_details,
        "created_at": c.created_at.isoformat(),
        "candidate": {
            "id": c.candidate.id,
            "full_name": c.candidate.full_name,
            "email": c.candidate.email,
        }
        if c.candidate
        else None,
        "offer": {"id": c.offer.id, "title": c.offer.title} if c.offer else None,
    }
