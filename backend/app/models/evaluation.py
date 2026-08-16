"""Évaluation d'entretien : le jugement humain, à côté de la note calculée.

Ce modèle ferme une boucle restée ouverte jusqu'ici. La plateforme sait noter
un dossier ; elle ne savait pas ce que cette note valait une fois le candidat
rencontré. En consignant l'appréciation du recruteur après l'entretien, deux
choses deviennent possibles :

  * **mesurer** l'écart entre la note du système et le jugement humain, sur
    des cas réels et non sur un corpus public. C'est la seule évaluation qui
    porte véritablement sur l'usage ;

  * **réentraîner** un jour le modèle sur ces décisions. Le corpus
    d'apprentissage actuel vient d'une source extérieure et anglophone ; des
    entretiens réels, dans la langue et le marché de l'entreprise, vaudraient
    infiniment mieux. Encore faut-il les avoir consignés.

L'évaluation ne modifie jamais la note. Les deux appréciations cohabitent, et
c'est leur écart qui renseigne.
"""
from datetime import datetime, timezone

from ..extensions import db

# Criteres d'un entretien de recrutement. Volontairement peu nombreux : une
# grille trop fine n'est jamais remplie, et une grille jamais remplie ne sert
# a rien.
CRITERES = (
    ("competences_techniques", "Compétences techniques"),
    ("experience_pertinente", "Pertinence de l'expérience"),
    ("communication", "Communication"),
    ("motivation", "Motivation et projet"),
    ("adequation_equipe", "Adéquation à l'équipe"),
)

# Verdict de synthese, distinct des notes : un candidat peut etre bon partout
# et ne pas correspondre au poste.
VERDICTS = ("a_recruter", "reserve", "a_revoir", "non_retenu")

LIBELLES_VERDICT = {
    "a_recruter": "À recruter",
    "reserve": "Sous réserve",
    "a_revoir": "À revoir plus tard",
    "non_retenu": "Non retenu",
}


class Evaluation(db.Model):
    """Compte rendu d'entretien pour une candidature."""

    __tablename__ = "evaluations"
    __table_args__ = (
        # Un entretien, une évaluation : la révision se fait par modification.
        db.UniqueConstraint("application_id", name="uq_evaluation_candidature"),
    )

    id = db.Column(db.Integer, primary_key=True)

    application_id = db.Column(
        db.Integer, db.ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    application = db.relationship("Application", back_populates="evaluation")

    # Notes de 1 à 5 par critère, conservées telles quelles pour rester
    # lisibles et modifiables sans migration si la grille évolue.
    notes = db.Column(db.JSON, nullable=False, default=dict)
    verdict = db.Column(db.String(20), nullable=False)
    commentaire = db.Column(db.Text)

    # Note du système au moment de l'entretien. La figer ici permet de
    # comparer plus tard, même si la candidature est réanalysée entre-temps.
    score_systeme = db.Column(db.Float)

    evaluateur_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    evaluateur = db.relationship("User", foreign_keys=[evaluateur_id])

    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    @property
    def moyenne(self):
        """Moyenne des critères renseignés, sur 5."""
        valeurs = [v for v in (self.notes or {}).values() if isinstance(v, (int, float))]
        return round(sum(valeurs) / len(valeurs), 2) if valeurs else None

    @property
    def note_humaine_sur_100(self):
        """Moyenne ramenée sur 100, pour être comparable à la note du système."""
        moyenne = self.moyenne
        return round((moyenne - 1) / 4 * 100) if moyenne is not None else None

    @property
    def ecart(self):
        """Écart entre la note du système et l'appréciation humaine.

        Positif : le système a été plus généreux que le recruteur.
        """
        humaine = self.note_humaine_sur_100
        if humaine is None or self.score_systeme is None:
            return None
        return round(self.score_systeme - humaine)

    def to_dict(self):
        return {
            "id": self.id,
            "application_id": self.application_id,
            "notes": self.notes or {},
            "verdict": self.verdict,
            "verdict_libelle": LIBELLES_VERDICT.get(self.verdict, self.verdict),
            "commentaire": self.commentaire,
            "moyenne": self.moyenne,
            "note_humaine_sur_100": self.note_humaine_sur_100,
            "score_systeme": self.score_systeme,
            "ecart": self.ecart,
            "evaluateur": self.evaluateur.full_name if self.evaluateur else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
