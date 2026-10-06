from app.errors import ApiError
from app.models.topic import Topic
from app.schemas.base import CamelModel
from app.timeutil import UtcDateTime

MAX_NAME_LENGTH = 100


class CreateTopicRequest(CamelModel):
    name: str | None = None

    def ensure_valid(self) -> None:
        if self.name is None or self.name.strip() == "":
            raise ApiError(400, "USER_INVALID_INPUT", "Topic name is required")
        # Java's @Size counts UTF-16 code units, so an emoji counts twice.
        if len(self.name.encode("utf-16-le")) // 2 > MAX_NAME_LENGTH:
            raise ApiError(400, "USER_INVALID_INPUT", "Topic name must be at most 100 characters")


class TopicResponse(CamelModel):
    id: str  # the topic's publicId, never the Mongo _id
    name: str
    created_at: UtcDateTime | None = None
    test_count: int | None = None
    avg_score: float | None = None

    @classmethod
    def from_topic(cls, topic: Topic) -> "TopicResponse":
        return cls(
            id=topic.public_id,
            name=topic.name,
            created_at=topic.created_at,
            test_count=topic.test_count,
            avg_score=topic.avg_score,
        )
