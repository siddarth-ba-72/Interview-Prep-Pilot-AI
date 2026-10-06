"""In-memory stand-ins for the repositories and the AI client."""
import asyncio
import re
from collections.abc import AsyncIterator

from pymongo.errors import DuplicateKeyError

from app.clients.ai_client import AiStreamError
from app.models.chat_session import ChatSession, Message
from app.models.topic import Topic
from app.timeutil import utc_now


def oid(n: int) -> str:
    return f"{n:024x}"


class FakeTopics:
    def __init__(self) -> None:
        self.items: dict[str, Topic] = {}

    async def find_by_user_newest_first(self, user_id: str) -> list[Topic]:
        mine = [t for t in self.items.values() if t.user_id == user_id]
        return sorted(mine, key=lambda t: (t.created_at, t.id), reverse=True)

    async def find_by_public_id_and_user(self, public_id: str, user_id: str) -> Topic | None:
        return next((t for t in self.items.values() if t.public_id == public_id and t.user_id == user_id), None)

    async def find_by_id_and_user(self, topic_id: str, user_id: str) -> Topic | None:
        topic = self.items.get(topic_id)
        return topic if topic and topic.user_id == user_id else None

    async def exists_by_user_and_name_ignore_case(self, user_id: str, name: str) -> bool:
        pattern = re.compile(f"^{re.escape(name)}$", re.IGNORECASE)
        return any(t.user_id == user_id and pattern.match(t.name) for t in self.items.values())

    async def insert(self, topic: Topic) -> Topic:
        if any(t.user_id == topic.user_id and t.name == topic.name for t in self.items.values()):
            raise DuplicateKeyError("user_name_unique")
        topic.id = oid(len(self.items) + 1)
        topic.created_at = utc_now()
        self.items[topic.id] = topic
        return topic

    async def delete_by_id_and_user(self, topic_id: str, user_id: str) -> None:
        if await self.find_by_id_and_user(topic_id, user_id):
            del self.items[topic_id]


class FakeChats:
    def __init__(self) -> None:
        self.items: dict[str, ChatSession] = {}
        self.raise_duplicate_once = False

    async def find_by_user_and_topic(self, user_id: str, topic_id: str) -> ChatSession | None:
        return next((s for s in self.items.values() if s.user_id == user_id and s.topic_id == topic_id), None)

    async def insert(self, session: ChatSession) -> ChatSession:
        if self.raise_duplicate_once:  # simulate a concurrent request winning the race
            self.raise_duplicate_once = False
            winner = ChatSession(user_id=session.user_id, topic_id=session.topic_id, messages=[
                Message(role="AI", content="winner", timestamp=utc_now())])
            winner.id = oid(99)
            self.items[winner.id] = winner
            raise DuplicateKeyError("user_topic_unique")
        session.id = oid(len(self.items) + 1)
        self.items[session.id] = session
        return session

    async def push_message(self, session_id: str, message: Message) -> None:
        self.items[session_id].messages.append(message)

    async def delete_by_user_and_topic(self, user_id: str, topic_id: str) -> None:
        for key, session in list(self.items.items()):
            if session.user_id == user_id and session.topic_id == topic_id:
                del self.items[key]


class FakeAi:
    """Scripted stream_learn. Records every call, and what the chat held at the moment of the call."""

    def __init__(self, chats: FakeChats | None = None, tokens=("Hello", " world"), fail_after: int | None = None,
                 error: Exception | None = None, delay: float = 0.0) -> None:
        self.chats = chats
        self.tokens = list(tokens)
        self.fail_after = fail_after
        self.error = error or AiStreamError("boom")
        self.delay = delay
        self.calls: list[dict] = []

    async def stream_learn(self, topic_name: str, mode: str, messages: list[dict]) -> AsyncIterator[str]:
        stored = [len(s.messages) for s in self.chats.items.values()] if self.chats else []
        self.calls.append({"topic": topic_name, "mode": mode, "messages": messages, "stored_counts": stored})
        for i, token in enumerate(self.tokens):
            if self.fail_after is not None and i == self.fail_after:
                raise self.error
            if self.delay:
                await asyncio.sleep(self.delay)
            yield token
        if self.fail_after is not None and self.fail_after >= len(self.tokens):
            raise self.error
