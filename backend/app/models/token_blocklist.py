from datetime import datetime, timezone

from ..extensions import db


class TokenBlocklist(db.Model):
    """Tokens revoques (logout / session compromise)."""

    __tablename__ = "token_blocklist"

    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(36), unique=True, nullable=False, index=True)
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
