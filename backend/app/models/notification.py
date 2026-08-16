from datetime import datetime, timezone

from ..extensions import db

# Types d'evenements notifiables (sert au choix de l'icone cote interface)
TYPES = (
    "candidature_recue",      # -> recruteur proprietaire de l'offre
    "statut_change",          # -> candidat concerne
    "compte_cree",            # -> administrateurs
    "permissions_modifiees",  # -> utilisateurs du role concerne
    "offre_publiee",          # -> administrateurs
    "recruteur_en_attente",   # -> administrateurs
    "compte_approuve",        # -> recruteur valide + administrateurs
    "compte_refuse",          # -> demandeur
    "compte_supprime",        # -> administrateurs
    "bienvenue",              # -> nouvel inscrit
    "score_eleve",            # -> recruteur proprietaire de l'offre
    "compte_desactive",       # -> utilisateur concerne + administrateurs
    "compte_reactive",        # -> utilisateur concerne
    "compte_restaure",        # -> utilisateur concerne + administrateurs
    "connexions_echouees",    # -> titulaire du compte (securite)
    # --- Contrôle des candidatures (S4-06) ---
    "signalement_ouvert",     # -> recruteur proprietaire de l'offre
    "signalement_critique",   # -> administrateurs (alerte de securite)
    "signalement_traite",     # -> administrateurs, apres decision du recruteur
    "identite_a_verifier",    # -> candidat concerne, pour qu'il puisse corriger
)


class Notification(db.Model):
    """Notification destinée à UN utilisateur précis (séparation des rôles)."""

    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    type = db.Column(db.String(40), nullable=False)
    message = db.Column(db.String(400), nullable=False)
    link = db.Column(db.String(200))
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True
    )

    user = db.relationship("User", back_populates="notifications")

    def to_dict(self):
        return {
            "id": self.id,
            "type": self.type,
            "message": self.message,
            "link": self.link,
            "is_read": self.is_read,
            "created_at": self.created_at.isoformat(),
        }
