from datetime import datetime, timezone

from ..extensions import db, bcrypt

# Cycle de validation d'un compte.
# Un candidat est actif immediatement ; un recruteur doit etre approuve par un
# administrateur, car publier des offres au nom de l'entreprise engage celle-ci.
STATUTS_COMPTE = ("active", "pending", "rejected")


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # Validation des comptes recruteurs.
    # `server_default` est indispensable : sans lui, PostgreSQL refuse d'ajouter
    # cette colonne NOT NULL a une table contenant deja des enregistrements.
    status = db.Column(
        db.String(20), default="active", server_default="active", nullable=False, index=True
    )
    company = db.Column(db.String(150))
    phone = db.Column(db.String(40))
    approved_at = db.Column(db.DateTime)
    rejection_reason = db.Column(db.String(255))
    # Echecs de connexion consecutifs : remis a zero des qu'une tentative
    # aboutit. Sert a prevenir le titulaire d'un compte pris pour cible.
    failed_logins = db.Column(
        db.Integer, nullable=False, default=0, server_default="0"
    )
    # Instant jusqu'auquel les tentatives sont refusees. Le verrou porte sur le
    # compte vise et non sur l'adresse reseau : un essai systematique change
    # d'adresse sans difficulte, alors que le compte cible, lui, ne change pas.
    # La contrepartie est connue — on peut verrouiller le compte d'autrui — et
    # c'est pourquoi le verrou est court et le titulaire prevenu.
    locked_until = db.Column(db.DateTime)

    # Profil declare par le candidat : competences, annees d'experience,
    # niveau de diplome.
    #
    # Il sert a lui recommander des offres AVANT toute candidature — sans quoi
    # la plateforme ne peut rien lui dire tant qu'il n'a pas postule au hasard.
    # Declare et non extrait : personne ne le verifie, et c'est acceptable
    # parce qu'il ne sert qu'a l'orienter, jamais a decider de son sort. Des
    # qu'une candidature est analysee, le profil tire de son CV prend le
    # relais : l'observe l'emporte toujours sur le declare.
    profil_declare = db.Column(db.JSON)

    # Suppression logique : le compte disparait des listes mais reste
    # restaurable, et les donnees liees (candidatures) ne sont pas perdues.
    deleted_at = db.Column(db.DateTime, index=True)

    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False)
    role = db.relationship("Role", back_populates="users")

    offers = db.relationship("JobOffer", back_populates="recruiter")
    applications = db.relationship("Application", back_populates="candidate")
    notifications = db.relationship(
        "Notification", back_populates="user", cascade="all, delete-orphan"
    )

    # --- Mot de passe (bcrypt, jamais en clair) ---
    def set_password(self, password: str) -> None:
        self.password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

    def check_password(self, password: str) -> bool:
        return bcrypt.check_password_hash(self.password_hash, password)

    # --- RBAC : permissions relues en base à chaque appel (RG-02) ---
    def has_permission(self, code: str) -> bool:
        if not self.role:
            return False
        return any(p.code == code for p in self.role.permissions)

    # --- Etat du compte ---
    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    # Aucune propriete « peut_se_connecter » n'est exposee ici, et c'est
    # deliberé. La route de connexion distingue quatre refus — compte
    # supprime, en attente, refuse, desactive — puis le verrou temporaire,
    # chacun avec son propre message. Un booleen unique les confondrait, et
    # une propriete oubliee lors de l'ajout du verrou aurait repondu « oui »
    # pour un compte verrouille.

    @property
    def est_administrateur(self) -> bool:
        return bool(self.role and self.role.name == "admin")

    @property
    def est_verrouille(self) -> bool:
        """Vrai tant que le verrou consécutif aux échecs n'a pas expiré."""
        if self.locked_until is None:
            return False
        limite = self.locked_until
        # Les dates lues depuis SQLite reviennent sans fuseau ; on compare
        # dans le meme referentiel plutot que de risquer une exception.
        maintenant = datetime.now(timezone.utc)
        if limite.tzinfo is None:
            maintenant = maintenant.replace(tzinfo=None)
        return limite > maintenant

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "email": self.email,
            "full_name": self.full_name,
            "role": self.role.name if self.role else None,
            "is_active": self.is_active,
            "status": self.status,
            "company": self.company,
            "phone": self.phone,
            "created_at": self.created_at.isoformat(),
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "rejection_reason": self.rejection_reason,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
        }
