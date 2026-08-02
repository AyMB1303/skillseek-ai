"""Tableau de bord : KPI et entonnoir calculés depuis la base (S2)."""
from datetime import datetime, timedelta, timezone

from flask import Blueprint, jsonify, request
from sqlalchemy import func

from ..extensions import db
from ..middleware.permissions import require_permission
from ..models.application import Application
from ..models.job_offer import JobOffer
from ..services.scoring import SEUIL_RETENU

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.get("/stats")
@require_permission("view_dashboard")
def stats(current_user):
    """Indicateurs de l'entonnoir sur une période glissante.

    Toutes les valeurs sont calculées : aucune donnée figée.
    """
    jours = request.args.get("days", default=30, type=int)
    depuis = datetime.now(timezone.utc) - timedelta(days=jours)
    precedent = depuis - timedelta(days=jours)

    base = Application.query.filter(Application.created_at >= depuis)

    def compter(requete):
        return requete.count()

    recues = compter(base)
    preselectionnees = compter(base.filter(Application.score >= SEUIL_RETENU))
    entretiens = compter(base.filter(Application.status == "interview"))
    recrutes = compter(base.filter(Application.status == "hired"))

    # Periode precedente : sert au calcul des variations affichees sur les cartes
    prec = Application.query.filter(
        Application.created_at >= precedent, Application.created_at < depuis
    )
    recues_prec = prec.count()

    def variation(actuel, avant):
        if not avant:
            return None
        return round((actuel - avant) / avant * 100)

    # Serie journaliere pour la courbe
    serie = (
        db.session.query(
            func.date(Application.created_at).label("jour"), func.count(Application.id)
        )
        .filter(Application.created_at >= depuis)
        .group_by("jour")
        .order_by("jour")
        .all()
    )

    def taux(numerateur, denominateur):
        return round(numerateur / denominateur * 100, 1) if denominateur else 0.0

    return jsonify(
        periode_jours=jours,
        kpi={
            "recues": {"valeur": recues, "variation": variation(recues, recues_prec)},
            "preselectionnees": {"valeur": preselectionnees},
            "entretiens": {"valeur": entretiens},
            "recrutes": {"valeur": recrutes},
        },
        funnel=[
            {"etape": "Candidatures reçues", "valeur": recues, "taux": 100.0},
            {
                "etape": "Filtre IA",
                "valeur": preselectionnees,
                "taux": taux(preselectionnees, recues),
            },
            {
                "etape": "Entretiens",
                "valeur": entretiens,
                "taux": taux(entretiens, preselectionnees),
            },
            {"etape": "Recrutements", "valeur": recrutes, "taux": taux(recrutes, entretiens)},
        ],
        serie=[{"jour": str(j), "valeur": v} for j, v in serie],
        offres_ouvertes=JobOffer.query.filter_by(status="open").count(),
    )
