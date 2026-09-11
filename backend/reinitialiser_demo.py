"""Efface le candidat de démonstration, pour rejouer l'enregistrement vidéo.

Une prise de vue rate rarement du premier coup. Or le scénario n'est pas
rejouable tel quel : le compte existe déjà — et la suppression depuis l'espace
d'administration est une mise à la corbeille, qui conserve la ligne et donc
l'adresse — tandis que la candidature est protégée contre le doublon. La
deuxième prise échouerait donc deux fois, à l'inscription puis au dépôt.

Ce script supprime réellement le compte et ce qui s'y rattache, afin que la
prise suivante reparte d'un état vierge. Il est volontairement étroit : il ne
touche qu'une adresse, refuse d'agir sur autre chose qu'un compte candidat, et
ne connaît rien de la base au-delà de cela.

    docker compose exec backend python reinitialiser_demo.py
    docker compose exec backend python reinitialiser_demo.py autre@exemple.ma
"""
import os
import sys

from app import create_app
from app.extensions import db
from app.models.application import Application
from app.models.user import User

ADRESSE_PAR_DEFAUT = "sahrizaid8@gmail.com"


def reinitialiser(adresse):
    utilisateur = User.query.filter_by(email=adresse.strip().lower()).first()
    if utilisateur is None:
        print(f"Aucun compte pour {adresse} : rien à faire.")
        return 0

    # Garde-fou : ce script sert une démonstration, pas l'administration. Un
    # recruteur ou un administrateur effacé par mégarde emporterait ses offres
    # et son journal avec lui.
    role = getattr(utilisateur.role, "name", None)
    if role != "candidate":
        print(f"Refus : {adresse} porte le rôle « {role} », pas « candidate ».")
        return 1

    candidatures = Application.query.filter_by(candidate_id=utilisateur.id).all()
    for candidature in candidatures:
        # Le CV déposé est un fichier sur le disque : le laisser derrière soi
        # accumulerait des documents orphelins au fil des prises.
        chemin = candidature.cv_path
        if chemin and os.path.isabs(chemin) and os.path.exists(chemin):
            try:
                os.remove(chemin)
            except OSError as erreur:
                print(f"CV non supprimé ({chemin}) : {erreur}")
        db.session.delete(candidature)

    db.session.delete(utilisateur)
    db.session.commit()
    print(
        f"Compte {adresse} supprimé, "
        f"{len(candidatures)} candidature(s) effacée(s). "
        "La prise suivante repart d'une inscription vierge."
    )
    return 0


if __name__ == "__main__":
    adresse = sys.argv[1] if len(sys.argv) > 1 else ADRESSE_PAR_DEFAUT
    app = create_app()
    with app.app_context():
        sys.exit(reinitialiser(adresse))
