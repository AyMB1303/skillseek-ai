"""Assistant conversationnel : interrogation en langage naturel."""
from flask import Blueprint, jsonify, request

from ..middleware.permissions import require_permission
from ..services.rag import assistant as rag

assistant_bp = Blueprint("assistant", __name__)


def _portee(utilisateur):
    """Limite la recherche au périmètre de l'utilisateur.

    Un recruteur n'interroge que ses propres offres et les candidatures
    associées. La portée ne s'applique qu'au domaine du recrutement.
    """
    return None if utilisateur.est_administrateur else utilisateur.id


def _domaine(utilisateur):
    """Choisit la base de connaissance interrogée.

    Un administrateur et un recruteur ne posent pas les mêmes questions, mais
    la raison de fond est ailleurs : le rôle administrateur ne détient pas
    `view_applications`. Lui ouvrir la base du recrutement lui livrerait par
    la conversation le contenu de dossiers que le modèle de droits lui refuse.
    """
    return "administration" if utilisateur.est_administrateur else "recrutement"


@assistant_bp.post("/ask")
@require_permission("use_chatbot")
def poser_question(current_user):
    corps = request.get_json(silent=True) or {}
    question = corps.get("question", "")
    if not question.strip():
        return jsonify(error="La question est vide."), 400
    if len(question) > 500:
        return jsonify(error="Question trop longue (500 caractères maximum)."), 400

    # L'historique est fourni par le client et borne cote serveur : il sert
    # uniquement de contexte conversationnel, jamais de source de donnees.
    historique = corps.get("historique")
    if not isinstance(historique, list):
        historique = []

    return jsonify(
        rag.repondre(
            question, _portee(current_user),
            historique=historique[-8:], domaine=_domaine(current_user),
        )
    )


@assistant_bp.get("/status")
@require_permission("use_chatbot")
def etat(current_user):
    return jsonify(rag.diagnostic(_portee(current_user), _domaine(current_user)))
