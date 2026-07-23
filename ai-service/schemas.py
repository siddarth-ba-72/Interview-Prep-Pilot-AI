from enum import Enum

from pydantic import BaseModel, Field


class Role(str, Enum):
    USER = "USER"
    AI = "AI"


class ChatMessage(BaseModel):
    role: Role
    content: str


class LearnMode(str, Enum):
    CLARIFY = "CLARIFY"
    GENERATE_CONTENT = "GENERATE_CONTENT"
    FOLLOW_UP = "FOLLOW_UP"


class LearnStreamRequest(BaseModel):
    topic_name: str = Field(alias="topicName")
    mode: LearnMode
    messages: list[ChatMessage] = Field(default_factory=list)

    model_config = {"populate_by_name": True}
