"""Signalement d'anomalie sur une candidature (S4-06).

Un signalement n'est **jamais une accusation**. C'est une observation datée,
motivée et vérifiable, portée à la connaissance du recruteur, qui seul décide
de ce qu'il en fait. Cette réserve n'est pas de la prudence rhétorique : les
contrôles produisent inévitablement des faux positifs — un nom d'épouse, une
translittération de l'arabe, un CV rédigé par un cabinet de placement — et
traiter un signalement comme une preuve reviendrait à écarter des candidats
honnêtes sur un indice.

D'où trois principes appliqués dans tout le module :

  * un signalement ne modifie jamais la note ni le statut d'une candidature ;
  * il porte toujours le **motif exact** et les éléments qui l'ont déclenché,
    de sorte que le recruteur puisse vérifier par lui-même ;
  * il possède un cycle de vie propre — examiné, confirmé, écarté — qui trace
    la décision humaine à côté de l'observation automatique.
"""
from datetime import datetime, timezone

from ..extensions import db

# Familles de controles. Le prefixe indique ce qui est verifie.
TYPES = (
    "identite_divergente",      # nom du compte != nom du document
    "email_divergent",          # adresse du document != celle du compte
    "email_tiers",              # adresse du document appartient a un autre compte
    "telephone_partage",        # numero deja rattache a un autre candidat
    "document_duplique",        # document identique depose par un autre candidat
    "document_similaire",       # document tres proche de celui d'un autre candidat
    "chronologie_incoherente",  # dates impossibles ou contradictoires
    "redaction_assistee",       # indices de generation automatique du texte
    "fichier_suspect",          # contenu actif ou format incoherent
    # --- Releve par un humain ---
    "diplome_douteux",          # diplome ou etablissement invraisemblable
    "experience_invraisemblable",  # parcours qui ne tient pas a la lecture
    "references_fausses",       # employeur ou reference introuvable
    "autre",                    # tout ce que les controles n'anticipent pas
)

# Types qu'un recruteur peut ouvrir lui-meme. Les controles automatiques ne
# couvrent que ce qui est verifiable par le document ; un recruteur, lui,
# peut telephoner a un ancien employeur ou reconnaitre un diplome qui
# n'existe pas. Sa saisie complete la machine, elle ne la double pas.
TYPES_MANUELS = (
    "identite_divergente",
    "diplome_douteux",
    "experience_invraisemblable",
    "references_fausses",
    "document_similaire",
    "autre",
)

# Origine de l'observation : la distinction compte pour l'audit, et pour
# mesurer ce que les controles automatiques laissent passer.
ORIGINES = ("automatique", "manuel")

# Gravites, de la simple information a l'alerte appelant une verification.
SEVERITES = ("information", "attention", "alerte")

# Cycle de vie : l'observation automatique, puis la decision humaine.
STATUTS = ("nouveau", "examine", "confirme", "ecarte")

# Statuts marquant une decision prise. Nommes plutot que repetes en litteral :
# la meme paire servait a trois endroits, et rien ne garantissait qu'elle reste
# la meme partout.
STATUTS_TRANCHES = ("confirme", "ecarte")


class Signalement(db.Model):
    """Anomalie relevée automatiquement sur une candidature."""

    __tablename__ = "signalements"

    id = db.Column(db.Integer, primary_key=True)

    application_id = db.Column(
        db.Integer, db.ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    application = db.relationship("Application", back_populates="signalements")

    type = db.Column(db.String(40), nullable=False, index=True)
    severite = db.Column(db.String(20), nullable=False, default="attention")
    message = db.Column(db.String(400), nullable=False)
    # Elements chiffres ayant declenche le controle : ce qui rend l'observation
    # verifiable plutot que peremptoire.
    details = db.Column(db.JSON)

    origine = db.Column(
        db.String(20), nullable=False, default="automatique",
        server_default="automatique",
    )
    # Auteur du signalement lorsqu'il a ete ouvert a la main.
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_by = db.relationship("User", foreign_keys=[created_by_id])

    statut = db.Column(
        db.String(20), nullable=False, default="nouveau",
        server_default="nouveau", index=True,
    )
    commentaire = db.Column(db.String(400))

    reviewed_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    reviewed_by = db.relationship("User", foreign_keys=[reviewed_by_id])
    reviewed_at = db.Column(db.DateTime)

    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc),
        nullable=False, index=True,
    )

    @property
    def est_traite(self):
        """Une décision humaine a été prise, quel qu'en soit le sens."""
        return self.statut in STATUTS_TRANCHES

    def to_dict(self, avec_candidature=False):
        donnees = {
            "id": self.id,
            "application_id": self.application_id,
            "type": self.type,
            "severite": self.severite,
            "message": self.message,
            "details": self.details or {},
            "origine": self.origine,
            "created_by": self.created_by.full_name if self.created_by else None,
            "statut": self.statut,
            "commentaire": self.commentaire,
            "reviewed_by": self.reviewed_by.full_name if self.reviewed_by else None,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "created_at": self.created_at.isoformat(),
        }
        if avec_candidature and self.application:
            candidature = self.application
            donnees["candidature"] = {
                "id": candidature.id,
                "candidat": (
                    candidature.candidate.full_name if candidature.candidate else None
                ),
                "candidat_id": candidature.candidate_id,
                "offre": candidature.offer.title if candidature.offer else None,
                "offre_id": candidature.offer_id,
                "score": candidature.score,
                "statut_candidature": candidature.status,
            }
        return donnees
