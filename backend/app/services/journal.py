"""Écriture du journal d'audit.

Une seule fonction, appelée depuis les points de décision. Elle n'engage
jamais la transaction : c'est l'appelant qui maîtrise le moment du commit, et
une trace ne doit pas être écrite avant l'action qu'elle décrit.

Le principe qui gouverne ce module : **journaliser ne doit jamais faire
échouer l'action journalisée**. Une trace perdue est regrettable ; un
changement de statut refusé parce que l'audit a trébuché serait absurde.
"""
import logging

from ..extensions import db
from ..models.journal import EntreeJournal

logger = logging.getLogger(__name__)


def tracer(action, auteur=None, objet_type=None, objet_id=None,
           objet_libelle=None, **detail):
    """Consigne une action dans le journal.

    Exemple :
        journal.tracer(
            "candidature_statut", auteur=current_user,
            objet_type="candidature", objet_id=c.id,
            objet_libelle=c.candidate.full_name,
            avant="received", apres="interview",
        )
    """
    try:
        db.session.add(
            EntreeJournal(
                action=action,
                objet_type=objet_type,
                objet_id=objet_id,
                objet_libelle=(objet_libelle or "")[:200] or None,
                detail=detail or None,
                auteur_id=getattr(auteur, "id", None),
                # Le nom est recopie : si le compte disparait, la trace reste
                # lisible. Un audit qui renvoie « utilisateur nº17 » ne sert
                # a personne.
                auteur_nom=getattr(auteur, "full_name", None),
            )
        )
    except Exception as erreur:      # noqa: BLE001
        logger.warning("Écriture du journal impossible : %s", erreur)
