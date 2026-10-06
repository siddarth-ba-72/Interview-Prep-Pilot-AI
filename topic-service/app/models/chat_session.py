from datetime import datetime
from enum import StrEnum

from pydantic import Field

from app.schemas.base import CamelModel


class Role(StrEnum):
    USER = "USER"
    AI = "AI"


class Message(CamelModel):
    role: Role
    content: str
    timestamp: datetime


class ChatSession(CamelModel):
    """topics_db.chat_sessions. `topic_id` is the topic's _id hex, not its publicId."""

    id: str | None = None
    user_id: str
    topic_id: str
    messages: list[Message] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None
