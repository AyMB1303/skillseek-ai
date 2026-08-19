"""Tableau de bord : KPI et entonnoir calculés depuis la base (S2)."""
from datetime import datetime, timedelta, timezone

from flask import Blueprint, jsonify, request
from sqlalchemy import func

from ..extensions import db
from ..middleware.permissions import require_permission
from ..models.application import Application
from ..models.job_offer import JobOffer
from ..models.journal import EntreeJournal
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


@dashboard_bp.get("/analyse")
@require_permission("view_dashboard")
def analyse(current_user):
    """Lecture analytique du portefeuille de candidatures.

    Le tableau de bord répond à « combien ». Celui-ci répond à « pourquoi » :
    comment les notes se distribuent, ce qui écarte le plus souvent, quelles
    compétences manquent au marché local, et combien de temps un dossier
    attend avant d'être tranché.

    Tout est calculé à la lecture, sur le périmètre de l'utilisateur. Aucune
    table d'agrégats n'est tenue à jour : sur ces volumes elle coûterait plus
    en complexité qu'elle ne rapporterait en temps de réponse, et elle
    introduirait le risque classique d'un chiffre affiché qui ne correspond
    plus aux données.
    """
    jours = request.args.get("days", default=90, type=int)
    depuis = datetime.now(timezone.utc) - timedelta(days=jours)

    candidatures = (
        acces.restreindre_candidatures(Application.query, current_user)
        .filter(Application.created_at >= depuis)
        .all()
    )
    notes = [c.score for c in candidatures if c.score is not None]

    # --- Distribution des notes -------------------------------------------
    # Les tranches suivent la lecture métier, pas un découpage régulier : le
    # seuil de 50 sépare deux mondes, et 70 marque le profil très adapté.
    tranches = [
        ("0 – 24", 0, 25), ("25 – 49", 25, 50),
        ("50 – 69", 50, 70), ("70 – 84", 70, 85), ("85 – 100", 85, 101),
    ]
    distribution = [
        {
            "tranche": libelle,
            "effectif": sum(1 for n in notes if bas <= n < haut),
            "retenu": bas >= SEUIL_RETENU,
        }
        for libelle, bas, haut in tranches
    ]

    # --- Ce qui écarte, et ce qui manque ----------------------------------
    motifs, manquantes, reserves = {}, {}, {}
    for c in candidatures:
        details = c.score_details or {}
        for motif in details.get("eliminatoires") or []:
            # Le motif porte des valeurs chiffrées propres au dossier
            # (« 2 ans < 5 ans requis ») : on regroupe sur sa nature.
            cle = motif.split(":")[0].split("(")[0].strip()
            motifs[cle] = motifs.get(cle, 0) + 1
        for competence in details.get("competences_manquantes") or []:
            manquantes[competence] = manquantes.get(competence, 0) + 1
        for reserve in details.get("reserves") or []:
            cle = reserve.split(":")[0].split("(")[0].strip()
            reserves[cle] = reserves.get(cle, 0) + 1

    def palmares(compteur, limite=8):
        return [
            {"libelle": k, "effectif": v}
            for k, v in sorted(compteur.items(), key=lambda x: -x[1])[:limite]
        ]

    # --- Délai avant la première décision ---------------------------------
    #
    # La candidature ne porte pas de date de modification : ce serait un champ
    # de plus à tenir à jour, et il ne dirait rien de *quelle* décision a eu
    # lieu. Le journal d'audit, lui, date chaque changement de statut. On y
    # lit donc le délai entre le dépôt d'un dossier et le premier geste du
    # recruteur — l'indicateur que les équipes RH appellent « time to review ».
    #
    # Médiane et non moyenne : un dossier oublié deux mois tirerait la moyenne
    # à lui seul et donnerait une image fausse du rythme habituel.
    identifiants = [c.id for c in candidatures]
    premiers_gestes = {}
    if identifiants:
        traces = (
            EntreeJournal.query
            .filter(EntreeJournal.action == "candidature_statut")
            .filter(EntreeJournal.objet_type == "candidature")
            .filter(EntreeJournal.objet_id.in_(identifiants))
            .order_by(EntreeJournal.created_at)
            .all()
        )
        for trace in traces:
            premiers_gestes.setdefault(trace.objet_id, trace.created_at)

    delais = sorted(
        max((_naif(quand) - _naif(c.created_at)).days, 0)
        for c in candidatures
        if (quand := premiers_gestes.get(c.id)) is not None
    )
    mediane = delais[len(delais) // 2] if delais else None

    en_attente = [c for c in candidatures if c.status in ("received", "under_review")]
    plus_ancienne = min((c.created_at for c in en_attente), default=None)

    return jsonify(
        periode_jours=jours,
        effectif=len(candidatures),
        analysees=len(notes),
        distribution=distribution,
        note_mediane=sorted(notes)[len(notes) // 2] if notes else None,
        motifs_ecartement=palmares(motifs),
        competences_manquantes=palmares(manquantes),
        reserves=palmares(reserves),
        delai_median_jours=mediane,
        dossiers_traces=len(delais),
        en_attente=len(en_attente),
        attente_la_plus_ancienne_jours=(
            (datetime.now(timezone.utc) - _naif(plus_ancienne)).days
            if plus_ancienne else None
        ),
        lecture=(
            "Les motifs d'écartement sont regroupés par nature ; les valeurs "
            "chiffrées propres à chaque dossier sont retirées du regroupement. "
            "Le délai de première décision est lu dans le journal d'audit."
        ),
    )


def _naif(date):
    """Aligne les fuseaux avant soustraction : PostgreSQL et SQLite diffèrent."""
    return date if date.tzinfo else date.replace(tzinfo=timezone.utc)


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
