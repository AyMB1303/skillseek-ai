from datetime import datetime, timezone

from ..extensions import db

# Types d'evenements notifiables (sert au choix de l'icone cote interface)
TYPES = (
    "candidature_recue",      # -> recruteur
    "statut_change",          # -> candidat
    "compte_cree",            # -> administrateurs
    "permissions_modifiees",  # -> utilisateurs du role concerne
    "offre_publiee",          # -> administrateurs
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
