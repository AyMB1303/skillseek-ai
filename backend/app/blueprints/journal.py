"""Consultation du journal d'audit.

Lecture seule, et réservée aux administrateurs. Un journal consultable par
ceux dont il trace les actions perdrait une part de son intérêt ; et aucune
route d'écriture n'existe, l'immuabilité étant ce qui lui donne sa valeur.
"""
from flask import Blueprint, jsonify, request

from ..middleware.permissions import require_permission
from ..models.journal import ACTIONS, EntreeJournal

journal_bp = Blueprint("journal", __name__)

LIBELLES = {
    "candidature_statut": "Changement de statut d'une candidature",
    "candidature_analysee": "Relance d'analyse",
    "signalement_traite": "Décision sur un signalement",
    "signalement_ouvert": "Signalement ouvert",
    "evaluation_entretien": "Compte rendu d'entretien",
    "compte_valide": "Validation d'un compte",
    "compte_refuse": "Refus d'un compte",
    "compte_desactive": "Désactivation d'un compte",
    "compte_supprime": "Suppression d'un compte",
    "compte_restaure": "Restauration d'un compte",
    "permissions_modifiees": "Modification des droits",
    "offre_publiee": "Publication d'une offre",
    "offre_supprimee": "Suppression d'une offre",
}


@journal_bp.get("")
@require_permission("manage_users")
def lister(current_user):
    """Dernières actions consignées, filtrables par nature et par objet."""
    requete = EntreeJournal.query

    action = request.args.get("action")
    if action in ACTIONS:
        requete = requete.filter(EntreeJournal.action == action)

    objet_type = request.args.get("objet_type")
    if objet_type:
        requete = requete.filter(EntreeJournal.objet_type == objet_type)

    limite = min(int(request.args.get("limite", 100)), 500)
    entrees = requete.order_by(EntreeJournal.created_at.desc()).limit(limite).all()

    return jsonify(
        entrees=[
            {**e.to_dict(), "action_libelle": LIBELLES.get(e.action, e.action)}
            for e in entrees
        ],
        actions=[
            {"code": a, "libelle": LIBELLES.get(a, a)} for a in ACTIONS
        ],
        total=EntreeJournal.query.count(),
    )
