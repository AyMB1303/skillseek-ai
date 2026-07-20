from datetime import datetime, timezone

from ..extensions import db


class JobOffer(db.Model):
    __tablename__ = "job_offers"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    # Criteres eliminatoires (systeme expert - Sprint 3)
    required_skills = db.Column(db.JSON, default=list)   # ex: ["python", "sql"]
    min_experience_years = db.Column(db.Integer, default=0)
    min_degree = db.Column(db.String(100))               # ex: "Bac+3"
    status = db.Column(db.String(20), default="open", nullable=False)  # open/closed
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    recruiter_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    recruiter = db.relationship("User", back_populates="offers")

    applications = db.relationship("Application", back_populates="offer")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "required_skills": self.required_skills or [],
            "min_experience_years": self.min_experience_years,
            "min_degree": self.min_degree,
            "status": self.status,
            "recruiter_id": self.recruiter_id,
            "created_at": self.created_at.isoformat(),
        }
