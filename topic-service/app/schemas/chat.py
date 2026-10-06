from app.errors import ApiError
from app.models.chat_session import Message
from app.schemas.base import CamelModel
from app.timeutil import UtcDateTime


class MessageResponse(CamelModel):
    role: str
    content: str
    timestamp: UtcDateTime

    @classmethod
    def from_message(cls, message: Message) -> "MessageResponse":
        return cls(role=message.role, content=message.content, timestamp=message.timestamp)


class ChatSessionResponse(CamelModel):
    topic_id: str  # the topic's publicId
    messages: list[MessageResponse]
    has_more: bool


class PagedMessagesResponse(CamelModel):
    messages: list[MessageResponse]
    has_more: bool


class SendMessageRequest(CamelModel):
    content: str | None = None

    def ensure_valid(self) -> None:
        if self.content is None or self.content.strip() == "":
            raise ApiError(400, "USER_INVALID_INPUT", "Message content is required")
