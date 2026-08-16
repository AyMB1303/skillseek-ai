from datetime import datetime, timezone

from ..extensions import db


class JobOffer(db.Model):
    __tablename__ = "job_offers"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    # Criteres de qualification (convention ATS : obligatoire vs souhaite)
    required_skills = db.Column(db.JSON, default=list)    # indispensables
    preferred_skills = db.Column(db.JSON, default=list)   # appreciees, non bloquantes
    min_experience_years = db.Column(db.Integer, default=0)
    min_degree = db.Column(db.String(100))                # ex: "Bac+3"
    status = db.Column(db.String(20), default="open", nullable=False)  # open/closed

    # Informations attendues sur une annonce (conventions ATS)
    location = db.Column(db.String(120))
    contract_type = db.Column(db.String(40))       # CDI, CDD, Stage, Alternance, Freelance
    remote_policy = db.Column(db.String(30))       # sur site, hybride, teletravail
    salary_min = db.Column(db.Integer)
    salary_max = db.Column(db.Integer)
    salary_currency = db.Column(db.String(10), default="MAD")

    # Suppression logique : l'offre part en corbeille, restaurable
    deleted_at = db.Column(db.DateTime, index=True)

    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    recruiter_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    recruiter = db.relationship("User", back_populates="offers")

    applications = db.relationship("Application", back_populates="offer")

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    @property
    def salaire_affiche(self):
        """Fourchette de rémunération formatée, ou None si non communiquée."""
        if not self.salary_min and not self.salary_max:
            return None
        devise = self.salary_currency or "MAD"
        if self.salary_min and self.salary_max:
            return f"{self.salary_min:,} – {self.salary_max:,} {devise}".replace(",", " ")
        montant = self.salary_min or self.salary_max
        prefixe = "À partir de" if self.salary_min else "Jusqu'à"
        return f"{prefixe} {montant:,} {devise}".replace(",", " ")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "required_skills": self.required_skills or [],
            "preferred_skills": self.preferred_skills or [],
            "min_experience_years": self.min_experience_years,
            "min_degree": self.min_degree,
            "status": self.status,
            "location": self.location,
            "contract_type": self.contract_type,
            "remote_policy": self.remote_policy,
            "salary_min": self.salary_min,
            "salary_max": self.salary_max,
            "salary_display": self.salaire_affiche,
            "recruiter_id": self.recruiter_id,
            "recruiter_name": self.recruiter.full_name if self.recruiter else None,
            "company": self.recruiter.company if self.recruiter else None,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
            "created_at": self.created_at.isoformat(),
        }
