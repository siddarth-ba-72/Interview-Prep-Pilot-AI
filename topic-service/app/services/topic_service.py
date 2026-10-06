import uuid

from pymongo.errors import DuplicateKeyError

from app.errors import duplicate_topic, topic_not_found
from app.models.topic import Topic
from app.repositories.chat_sessions import ChatSessionsRepository
from app.repositories.topics import TopicsRepository
from app.schemas.topics import TopicResponse


class TopicService:
    def __init__(self, topics: TopicsRepository, chat_sessions: ChatSessionsRepository) -> None:
        self.topics = topics
        self.chat_sessions = chat_sessions

    async def create(self, user_id: str, name: str) -> TopicResponse:
        # The name is stored as submitted (no trimming); only the duplicate check ignores case.
        if await self.topics.exists_by_user_and_name_ignore_case(user_id, name):
            raise duplicate_topic(name)
        topic = Topic(public_id=str(uuid.uuid4()), user_id=user_id, name=name, test_count=0)
        try:
            topic = await self.topics.insert(topic)
        except DuplicateKeyError:  # lost a race with a concurrent create
            raise duplicate_topic(name) from None
        return TopicResponse.from_topic(topic)

    async def list(self, user_id: str) -> list[TopicResponse]:
        return [TopicResponse.from_topic(t) for t in await self.topics.find_by_user_newest_first(user_id)]

    async def delete(self, user_id: str, topic_id: str) -> None:
        topic = await self.topics.find_by_public_id_and_user(topic_id, user_id)
        if topic is None:
            raise topic_not_found(topic_id)
        # Only the chat session is removed; tests and interviews are left behind (known issue K2, kept as is).
        await self.chat_sessions.delete_by_user_and_topic(user_id, topic.id)
        await self.topics.delete_by_id_and_user(topic.id, user_id)
