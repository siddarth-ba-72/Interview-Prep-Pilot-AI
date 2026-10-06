from datetime import datetime
from enum import StrEnum

from app.schemas.base import CamelModel


class AuthProvider(StrEnum):
    LOCAL = "LOCAL"
    GOOGLE = "GOOGLE"


class User(CamelModel):
    """users_db.users. `id` is the ObjectId hex; repositories convert at the boundary."""

    id: str | None = None
    email: str
    password_hash: str | None = None
    auth_provider: AuthProvider = AuthProvider.LOCAL
    google_id: str | None = None
    display_name: str
    created_at: datetime | None = None
    updated_at: datetime | None = None
