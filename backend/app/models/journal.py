"""Journal d'audit : qui a fait quoi, quand, sur quel objet.

Une plateforme qui écarte des candidats doit pouvoir rendre compte de ses
décisions — celles de la machine comme celles des personnes. Le moteur de
score justifie déjà les siennes ; ce journal fait le pendant pour les actions
humaines : changement de statut, validation d'un compte, modification des
droits, traitement d'un signalement.

Trois choix de conception méritent d'être explicités.

**L'entrée est immuable.** Aucune route ne permet de modifier ni de supprimer
une ligne. Un journal que l'on peut retoucher ne prouve rien.

**L'objet visé est décrit par un couple type/identifiant** plutôt que par une
clé étrangère. Une clé étrangère imposerait la suppression en cascade des
traces lorsque l'objet disparaît — exactement l'inverse de ce qu'on attend
d'un audit : c'est souvent après la suppression qu'on a besoin de savoir qui
l'a ordonnée.

**L'auteur peut être nul.** Certaines actions viennent du système lui-même,
et prétendre le contraire serait faux.
"""
from datetime import datetime, timezone

from ..extensions import db

# Actions tracees. La liste reste volontairement courte : journaliser tout
# revient a ne rien journaliser, le bruit noyant ce qui compte.
ACTIONS = (
    "candidature_statut",       # changement de statut d'une candidature
    "candidature_analysee",     # relance d'analyse
    "signalement_traite",       # decision sur une anomalie
    "signalement_ouvert",       # signalement porte a la main
    "evaluation_entretien",     # compte rendu d'entretien
    "compte_valide",            # validation d'un compte recruteur
    "compte_refuse",
    "compte_desactive",
    "compte_supprime",
    "compte_restaure",
    "permissions_modifiees",
    "offre_publiee",
    "offre_supprimee",
)


class EntreeJournal(db.Model):
    """Trace immuable d'une action significative."""

    __tablename__ = "journal"

    id = db.Column(db.Integer, primary_key=True)

    action = db.Column(db.String(40), nullable=False, index=True)

    # Objet vise, sans cle etrangere : la trace survit a la suppression.
    objet_type = db.Column(db.String(30), index=True)
    objet_id = db.Column(db.Integer, index=True)
    objet_libelle = db.Column(db.String(200))

    # Ce qui a change, sous forme lisible : « reçue -> entretien ».
    detail = db.Column(db.JSON)

    auteur_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    auteur = db.relationship("User", foreign_keys=[auteur_id])
    # Nom recopie : si le compte est supprime, la trace reste lisible.
    auteur_nom = db.Column(db.String(120))

    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc),
        nullable=False, index=True,
    )

    def to_dict(self):
        return {
            "id": self.id,
            "action": self.action,
            "objet_type": self.objet_type,
            "objet_id": self.objet_id,
            "objet_libelle": self.objet_libelle,
            "detail": self.detail or {},
            "auteur": self.auteur_nom or (self.auteur.full_name if self.auteur else None),
            "created_at": self.created_at.isoformat(),
        }
