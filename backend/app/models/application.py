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

    # Empreinte du texte du CV : sert a reperer un meme document depose sous
    # deux identites. Comparer des empreintes est immediat, la ou comparer les
    # textes deux a deux couterait un temps quadratique.
    cv_empreinte = db.Column(db.String(64), index=True)

    signalements = db.relationship(
        "Signalement", back_populates="application",
        cascade="all, delete-orphan", passive_deletes=True,
    )

    # Compte rendu d'entretien : au plus un par candidature.
    evaluation = db.relationship(
        "Evaluation", back_populates="application", uselist=False,
        cascade="all, delete-orphan", passive_deletes=True,
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "status": self.status,
            "score": self.score,
            "score_details": self.score_details,
            "candidate_id": self.candidate_id,
            "offer_id": self.offer_id,
            "created_at": self.created_at.isoformat(),
            "signalements": [s.to_dict() for s in self.signalements],
        }
