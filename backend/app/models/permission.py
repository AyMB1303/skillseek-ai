from ..extensions import db
from .role import role_permissions


class Permission(db.Model):
    __tablename__ = "permissions"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(64), unique=True, nullable=False, index=True)
    description = db.Column(db.String(255))

    roles = db.relationship(
        "Role", secondary=role_permissions, back_populates="permissions"
    )

    def to_dict(self) -> dict:
        return {"id": self.id, "code": self.code, "description": self.description}
