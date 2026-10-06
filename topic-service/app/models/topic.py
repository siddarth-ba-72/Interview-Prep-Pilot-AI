from datetime import datetime

from app.schemas.base import CamelModel


class Topic(CamelModel):
    """topics_db.topics. `id` is the ObjectId hex; `public_id` (a UUID) is what the API exposes."""

    id: str | None = None
    public_id: str
    user_id: str
    name: str
    test_count: int = 0
    avg_score: float | None = None
    created_at: datetime | None = None
