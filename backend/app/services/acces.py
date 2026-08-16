"""Appartenance des ressources : qui a le droit d'agir sur quoi.

Les permissions répondent à « cet utilisateur peut-il consulter des
candidatures ? ». Elles ne répondent pas à « **celle-ci** ? ». Deux recruteurs
détiennent exactement les mêmes droits ; ce qui les sépare n'est pas leur rôle
mais le périmètre de leurs offres. Sans ce second contrôle, `manage_offers`
autorisait un recruteur à modifier l'annonce d'un autre — pas parce que la
vérification était mal écrite, mais parce qu'elle n'existait pas.

Le rattachement suit une chaîne unique :

    recruteur → offre → candidature → CV, signalements, évaluations

Une candidature n'a donc pas de propriétaire propre : elle relève de qui a
publié l'offre. Centraliser cette règle ici évite qu'elle soit réécrite — et
oubliée — dans chaque route.

L'administrateur passe outre, mais seulement parce qu'il détient
`manage_users` : c'est la contrepartie assumée d'un rôle qui doit pouvoir
intervenir sur n'importe quel dossier signalé.

Le refus renvoie **403 et non 404**. Le choix se discute : un 404 masquerait
l'existence de la ressource. Il ne masquerait rien ici, les offres étant
publiquement listées et les identifiants séquentiels ; un 403 explicite reste
plus honnête et plus simple à diagnostiquer.
"""
from flask import jsonify

from ..models.application import Application
from ..models.job_offer import JobOffer

MESSAGE_OFFRE = "Cette offre ne relève pas de votre périmètre."
MESSAGE_CANDIDATURE = "Cette candidature ne relève pas de vos offres."


# --------------------------------------------------------------------------
# Prédicats
# --------------------------------------------------------------------------

def possede_offre(utilisateur, offre):
    if utilisateur.est_administrateur:
        return True
    return offre is not None and offre.recruiter_id == utilisateur.id


def possede_candidature(utilisateur, candidature):
    if utilisateur.est_administrateur:
        return True
    if candidature is None:
        return False
    return possede_offre(utilisateur, candidature.offer)


# --------------------------------------------------------------------------
# Récupération contrôlée
#
# Chaque fonction renvoie un couple (ressource, refus). Le refus est une
# réponse Flask prête à être retournée ; ce style évite les exceptions et
# rend la garde visible sur la ligne qui suit l'appel.
# --------------------------------------------------------------------------

def offre(utilisateur, offre_id, inclure_corbeille=True):
    obj = JobOffer.query.get(offre_id)
    if obj is None or (obj.is_deleted and not inclure_corbeille):
        return None, (jsonify(error="Offre introuvable."), 404)
    if not possede_offre(utilisateur, obj):
        return None, (jsonify(error=MESSAGE_OFFRE), 403)
    return obj, None


def candidature(utilisateur, app_id):
    obj = Application.query.get(app_id)
    if obj is None:
        return None, (jsonify(error="Candidature introuvable."), 404)
    if not possede_candidature(utilisateur, obj):
        return None, (jsonify(error=MESSAGE_CANDIDATURE), 403)
    return obj, None


# --------------------------------------------------------------------------
# Restriction des listes
#
# Le point aveugle le plus courant : une route unitaire bien gardée ne sert à
# rien si la liste qui la précède expose déjà tout.
# --------------------------------------------------------------------------

def restreindre_candidatures(requete, utilisateur):
    """Limite une requête de candidatures aux offres de l'utilisateur."""
    if utilisateur.est_administrateur:
        return requete
    return requete.join(JobOffer, Application.offer_id == JobOffer.id).filter(
        JobOffer.recruiter_id == utilisateur.id
    )


def restreindre_offres(requete, utilisateur):
    """Limite une requête d'offres à celles publiées par l'utilisateur."""
    if utilisateur.est_administrateur:
        return requete
    return requete.filter(JobOffer.recruiter_id == utilisateur.id)
