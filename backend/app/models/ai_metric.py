from datetime import datetime, timezone

from ..extensions import db


class AiMetric(db.Model):
    """Journal des traitements IA (stockage flexible JSON/JSONB)."""

    __tablename__ = "ai_metrics"

    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(
        db.Integer, db.ForeignKey("applications.id"), nullable=False
    )
    # Payload libre : durees, entites extraites, version du modele, etc.
    payload = db.Column(db.JSON, nullable=False)
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "application_id": self.application_id,
            "payload": self.payload,
            "created_at": self.created_at.isoformat(),
        }
