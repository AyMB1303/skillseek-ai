"""Évaluations d'entretien : saisie du jugement humain et confrontation.

L'intérêt de cette ressource dépasse la simple prise de notes. En consignant
l'appréciation portée après l'entretien à côté de la note calculée avant, la
plateforme se donne le seul moyen honnête de savoir ce que vaut son propre
classement : non pas sur un corpus public et anglophone, mais sur les
candidats réellement reçus.
"""
from flask import Blueprint, jsonify, request

from ..extensions import db
from ..middleware.permissions import require_permission
from ..models.application import Application
from ..models.evaluation import CRITERES, LIBELLES_VERDICT, VERDICTS, Evaluation
from ..models.job_offer import JobOffer
from ..services import journal

evaluations_bp = Blueprint("evaluations", __name__)

CODES_CRITERES = [code for code, _ in CRITERES]


def _candidature_accessible(utilisateur, app_id):
    """Retourne la candidature si elle relève du périmètre de l'utilisateur."""
    candidature = Application.query.get(app_id)
    if candidature is None:
        return None
    if utilisateur.est_administrateur:
        return candidature
    offre = candidature.offer
    return candidature if offre and offre.recruiter_id == utilisateur.id else None


@evaluations_bp.get("/grille")
@require_permission("view_applications")
def grille(current_user):
    """Critères et verdicts proposés, pour que l'interface reste synchronisée."""
    return jsonify(
        criteres=[{"code": c, "libelle": libelle} for c, libelle in CRITERES],
        verdicts=[{"code": v, "libelle": LIBELLES_VERDICT[v]} for v in VERDICTS],
    )


@evaluations_bp.get("/candidature/<int:app_id>")
@require_permission("view_applications")
def obtenir(current_user, app_id):
    candidature = _candidature_accessible(current_user, app_id)
    if candidature is None:
        return jsonify(error="Candidature introuvable."), 404
    evaluation = candidature.evaluation
    return jsonify(evaluation=evaluation.to_dict() if evaluation else None)


@evaluations_bp.put("/candidature/<int:app_id>")
@require_permission("manage_applications")
def enregistrer(current_user, app_id):
    """Crée ou met à jour l'évaluation d'entretien d'une candidature."""
    candidature = _candidature_accessible(current_user, app_id)
    if candidature is None:
        return jsonify(error="Candidature introuvable."), 404

    donnees = request.get_json(silent=True) or {}

    verdict = donnees.get("verdict")
    if verdict not in VERDICTS:
        return jsonify(error=f"Verdict invalide. Attendu : {', '.join(VERDICTS)}."), 400

    notes_recues = donnees.get("notes") or {}
    notes = {}
    for code in CODES_CRITERES:
        valeur = notes_recues.get(code)
        if valeur in (None, ""):
            continue          # critère non renseigné : admis, la grille reste souple
        try:
            note = int(valeur)
        except (TypeError, ValueError):
            return jsonify(error=f"Note invalide pour « {code} »."), 400
        if not 1 <= note <= 5:
            return jsonify(error="Les notes vont de 1 à 5."), 400
        notes[code] = note

    if not notes:
        return jsonify(error="Renseignez au moins un critère."), 400

    evaluation = candidature.evaluation
    if evaluation is None:
        evaluation = Evaluation(application=candidature)
        db.session.add(evaluation)
        # La note du systeme est figee a la premiere saisie : une reanalyse
        # ulterieure ne doit pas reecrire l'histoire de la comparaison.
        evaluation.score_systeme = candidature.score

    evaluation.notes = notes
    evaluation.verdict = verdict
    evaluation.commentaire = (donnees.get("commentaire") or "").strip() or None
    evaluation.evaluateur_id = current_user.id

    journal.tracer(
        "evaluation_entretien", auteur=current_user,
        objet_type="candidature", objet_id=candidature.id,
        objet_libelle=candidature.candidate.full_name if candidature.candidate else None,
        verdict=verdict, note_humaine=evaluation.note_humaine_sur_100,
        score_systeme=evaluation.score_systeme,
    )
    db.session.commit()
    return jsonify(evaluation=evaluation.to_dict())


@evaluations_bp.get("/comparaison")
@require_permission("view_dashboard")
def comparaison(current_user):
    """Confronte la note du système à l'appréciation humaine.

    C'est la mesure qui manque à tout système de présélection : non pas
    « le modèle est-il bon sur un corpus ? », mais « ses notes concordent-elles
    avec ce que les recruteurs constatent en entretien ? ».
    """
    requete = (
        Evaluation.query
        .join(Application, Evaluation.application_id == Application.id)
        .join(JobOffer, Application.offer_id == JobOffer.id)
    )
    if not current_user.est_administrateur:
        requete = requete.filter(JobOffer.recruiter_id == current_user.id)

    evaluations = [e for e in requete.all() if e.ecart is not None]
    if not evaluations:
        return jsonify(
            effectif=0,
            message=(
                "Aucune évaluation d'entretien enregistrée. La comparaison "
                "devient possible dès le premier compte rendu."
            ),
        )

    ecarts = [e.ecart for e in evaluations]
    concordants = [e for e in ecarts if abs(e) <= 15]

    # Retenus par le systeme et confirmes par le recruteur, et l'inverse :
    # les deux erreurs n'ont pas le meme cout.
    retenus_systeme = [e for e in evaluations if (e.score_systeme or 0) >= 50]
    faux_espoirs = [e for e in retenus_systeme if e.verdict == "non_retenu"]
    pepites_manquees = [
        e for e in evaluations
        if (e.score_systeme or 0) < 50 and e.verdict in ("a_recruter", "reserve")
    ]

    return jsonify(
        effectif=len(evaluations),
        ecart_moyen=round(sum(ecarts) / len(ecarts), 1),
        ecart_absolu_moyen=round(sum(abs(e) for e in ecarts) / len(ecarts), 1),
        part_concordante=round(100 * len(concordants) / len(evaluations), 1),
        faux_espoirs=len(faux_espoirs),
        pepites_manquees=len(pepites_manquees),
        lecture=(
            "Un écart positif signifie que le système note plus généreusement "
            "que le recruteur. La concordance compte les écarts inférieurs à "
            "15 points."
        ),
        detail=[
            {
                "candidat": (
                    e.application.candidate.full_name
                    if e.application and e.application.candidate else None
                ),
                "offre": (
                    e.application.offer.title
                    if e.application and e.application.offer else None
                ),
                "score_systeme": e.score_systeme,
                "note_humaine": e.note_humaine_sur_100,
                "ecart": e.ecart,
                "verdict": LIBELLES_VERDICT.get(e.verdict, e.verdict),
            }
            for e in sorted(evaluations, key=lambda x: abs(x.ecart), reverse=True)[:20]
        ],
    )
