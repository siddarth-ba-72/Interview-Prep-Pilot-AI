from datetime import datetime

from app.schemas.base import CamelModel


class RefreshToken(CamelModel):
    """users_db.refresh_tokens. Only the SHA-256 of the token is stored."""

    id: str | None = None
    user_id: str
    token_hash: str
    expires_at: datetime
    created_at: datetime | None = None
