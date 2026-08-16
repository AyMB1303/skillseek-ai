"""Tableau de bord : KPI et entonnoir calculés depuis la base (S2)."""
from datetime import datetime, timedelta, timezone

from flask import Blueprint, jsonify, request
from sqlalchemy import func

from ..extensions import db
from ..middleware.permissions import require_permission
from ..models.application import Application
from ..models.job_offer import JobOffer
from ..models.role import Role
from ..models.user import User
from ..services import acces
from ..services.scoring import SEUIL_RETENU

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.get("/stats")
@require_permission("view_dashboard")
def stats(current_user):
    """Indicateurs de l'entonnoir sur une période glissante.

    Toutes les valeurs sont calculées : aucune donnée figée.

    Les agrégats suivent le périmètre du recruteur. Un entonnoir global ne
    livre aucun nom, mais il renseigne sur l'activité d'un confrère — volumes
    reçus, taux de conversion — ce qui n'a pas à sortir de son espace.
    """
    jours = request.args.get("days", default=30, type=int)
    depuis = datetime.now(timezone.utc) - timedelta(days=jours)
    precedent = depuis - timedelta(days=jours)

    perimetre = lambda r: acces.restreindre_candidatures(r, current_user)  # noqa: E731
    base = perimetre(Application.query).filter(Application.created_at >= depuis)

    def compter(requete):
        return requete.count()

    recues = compter(base)
    preselectionnees = compter(base.filter(Application.score >= SEUIL_RETENU))
    entretiens = compter(base.filter(Application.status == "interview"))
    recrutes = compter(base.filter(Application.status == "hired"))

    # Periode precedente : sert au calcul des variations affichees sur les cartes
    prec = perimetre(Application.query).filter(
        Application.created_at >= precedent, Application.created_at < depuis
    )
    recues_prec = prec.count()

    def variation(actuel, avant):
        if not avant:
            return None
        return round((actuel - avant) / avant * 100)

    # Serie journaliere pour la courbe
    serie = (
        acces.restreindre_candidatures(
            db.session.query(
                func.date(Application.created_at).label("jour"),
                func.count(Application.id),
            ),
            current_user,
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
        offres_ouvertes=acces.restreindre_offres(
            JobOffer.query.filter(
                JobOffer.status == "open", JobOffer.deleted_at.is_(None)
            ),
            current_user,
        ).count(),
    )


@dashboard_bp.get("/admin")
@require_permission("manage_users")
def stats_admin(current_user):
    """Vue d'ensemble de la plateforme, destinée à l'administrateur."""
    actifs = User.query.filter(User.deleted_at.is_(None))

    par_role = {}
    for role in Role.query.all():
        par_role[role.name] = actifs.filter(User.role_id == role.id).count()

    en_corbeille = (
        User.query.filter(User.deleted_at.isnot(None)).count()
        + JobOffer.query.filter(JobOffer.deleted_at.isnot(None)).count()
    )

    recents = (
        User.query.filter(User.deleted_at.is_(None))
        .order_by(User.created_at.desc())
        .limit(5)
        .all()
    )

    return jsonify(
        comptes={
            "total": actifs.count(),
            "par_role": par_role,
            "en_attente": actifs.filter(User.status == "pending").count(),
            "desactives": actifs.filter(User.is_active.is_(False)).count(),
        },
        offres={
            "total": JobOffer.query.filter(JobOffer.deleted_at.is_(None)).count(),
            "ouvertes": JobOffer.query.filter(
                JobOffer.status == "open", JobOffer.deleted_at.is_(None)
            ).count(),
        },
        candidatures={"total": Application.query.count()},
        corbeille={"total": en_corbeille},
        derniers_comptes=[u.to_dict() for u in recents],
    )
