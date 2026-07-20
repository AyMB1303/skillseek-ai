from datetime import datetime, timezone

from ..extensions import db

# Statuts du workflow de candidature (funnel du cahier des charges)
STATUSES = ("received", "under_review", "shortlisted", "interview", "hired", "rejected")


class Application(db.Model):
    __tablename__ = "applications"
    __table_args__ = (
        db.UniqueConstraint("candidate_id", "offer_id", name="uq_candidate_offer"),
    )

    id = db.Column(db.Integer, primary_key=True)
    cv_path = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(20), default="received", nullable=False)
    # Score IA /100 (Sprint 3) - null tant que non calcule
    score = db.Column(db.Float)
    # Explication du score / motif de rejet par regle (explicabilite)
    score_details = db.Column(db.JSON)
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    candidate_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    candidate = db.relationship("User", back_populates="applications")

    offer_id = db.Column(db.Integer, db.ForeignKey("job_offers.id"), nullable=False)
    offer = db.relationship("JobOffer", back_populates="applications")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "status": self.status,
            "score": self.score,
            "score_details": self.score_details,
            "candidate_id": self.candidate_id,
            "offer_id": self.offer_id,
            "created_at": self.created_at.isoformat(),
        }
