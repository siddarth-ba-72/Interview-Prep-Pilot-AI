import asyncio
import json
import logging
from collections.abc import AsyncIterator
from datetime import datetime

from pymongo.errors import DuplicateKeyError

from app.clients.ai_client import AiClient, AiStreamError, AiUnavailableError
from app.errors import ErrorCode, api_error, chat_session_not_found, topic_not_found
from app.models.chat_session import ChatSession, Message, Role
from app.models.topic import Topic
from app.repositories.chat_sessions import ChatSessionsRepository
from app.repositories.topics import TopicsRepository
from app.schemas.chat import ChatSessionResponse, MessageResponse, PagedMessagesResponse
from app.timeutil import utc_now

logger = logging.getLogger(__name__)

PAGE_SIZE = 20
MODE_CLARIFY = "CLARIFY"
MODE_GENERATE_CONTENT = "GENERATE_CONTENT"
MODE_FOLLOW_UP = "FOLLOW_UP"
STREAM_FAILED_MESSAGE = "The AI response could not be completed. Please try again."


def sse_frame(payload: dict | str) -> str:
    """One SSE frame. json.dumps keeps a newline inside a token from ever breaking the framing."""
    data = payload if isinstance(payload, str) else json.dumps(payload)
    return f"data: {data}\n\n"


def determine_mode(message_count_before_reply: int) -> str:
    return MODE_GENERATE_CONTENT if message_count_before_reply <= 1 else MODE_FOLLOW_UP


def _end_index(messages: list[Message], before: datetime | None) -> int:
    """Exclusive end of the page: just past the last message older than the cursor (or the end when none)."""
    if before is None:
        return len(messages)
    for i in range(len(messages) - 1, -1, -1):
        if messages[i].timestamp < before:
            return i + 1
    return 0


def page(messages: list[Message], before: datetime | None = None) -> tuple[list[Message], bool]:
    end = _end_index(messages, before)
    start = max(0, end - PAGE_SIZE)
    return messages[start:end], start > 0


def _payloads(messages: list[Message]) -> list[dict]:
    return [{"role": str(m.role), "content": m.content} for m in messages]


class ChatService:
    def __init__(self, topics: TopicsRepository, chats: ChatSessionsRepository, ai: AiClient) -> None:
        self.topics = topics
        self.chats = chats
        self.ai = ai
        # Strong references: asyncio only keeps weak ones, so a running task could otherwise be collected.
        self._tasks: set[asyncio.Task] = set()

    async def _topic(self, user_id: str, topic_id: str) -> Topic:
        topic = await self.topics.find_by_public_id_and_user(topic_id, user_id)
        if topic is None:
            raise topic_not_found(topic_id)
        return topic

    async def get_or_create(self, user_id: str, topic_id: str) -> ChatSessionResponse:
        topic = await self._topic(user_id, topic_id)
        session = await self.chats.find_by_user_and_topic(user_id, topic.id)
        if session is None:
            session = await self._create_session(user_id, topic)
        messages, has_more = page(session.messages)
        return ChatSessionResponse(
            topic_id=topic_id, messages=[MessageResponse.from_message(m) for m in messages], has_more=has_more
        )

    async def _create_session(self, user_id: str, topic: Topic) -> ChatSession:
        try:
            parts = [token async for token in self.ai.stream_learn(topic.name, MODE_CLARIFY, [])]
        except AiUnavailableError:
            raise api_error(ErrorCode.AI_SERVICE_UNAVAILABLE) from None
        except AiStreamError:
            raise api_error(ErrorCode.AI_SERVICE_ERROR) from None
        session = ChatSession(
            user_id=user_id,
            topic_id=topic.id,
            messages=[Message(role=Role.AI, content="".join(parts), timestamp=utc_now())],
        )
        try:
            return await self.chats.insert(session)
        except DuplicateKeyError:  # a concurrent request created it first
            existing = await self.chats.find_by_user_and_topic(user_id, topic.id)
            if existing is None:
                raise
            return existing

    async def get_messages(self, user_id: str, topic_id: str, before: datetime | None) -> PagedMessagesResponse:
        topic = await self._topic(user_id, topic_id)
        session = await self.chats.find_by_user_and_topic(user_id, topic.id)
        if session is None:
            raise chat_session_not_found(topic_id)
        messages, has_more = page(session.messages, before)
        return PagedMessagesResponse(messages=[MessageResponse.from_message(m) for m in messages], has_more=has_more)

    async def start_reply(self, user_id: str, topic_id: str, content: str) -> AsyncIterator[str]:
        """Validate, persist the user's message and start the AI stream; return an iterator of SSE frames.

        Topic/session errors are raised here, before any frame exists. Once this returns, the AI call runs in
        a task of its own: a browser that closes the tab mid-answer cancels the response generator but not
        that task, so the finished answer is still saved (as it was in Java, where the Reactor subscription
        outlived the emitter).
        """
        topic = await self._topic(user_id, topic_id)
        session = await self.chats.find_by_user_and_topic(user_id, topic.id)
        if session is None:
            raise chat_session_not_found(topic_id)

        mode = determine_mode(len(session.messages))  # counted before the new message is appended
        user_message = Message(role=Role.USER, content=content, timestamp=utc_now())
        history = _payloads([*session.messages, user_message])  # full history, not just the visible page
        await self.chats.push_message(session.id, user_message)

        queue: asyncio.Queue[str | None] = asyncio.Queue()
        task = asyncio.create_task(self._produce(queue, session.id, topic, mode, history, user_id, topic_id))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return self._drain(queue)

    @staticmethod
    async def _drain(queue: asyncio.Queue[str | None]) -> AsyncIterator[str]:
        while (frame := await queue.get()) is not None:
            yield frame

    async def _produce(
        self,
        queue: asyncio.Queue[str | None],
        session_id: str,
        topic: Topic,
        mode: str,
        history: list[dict],
        user_id: str,
        topic_id: str,
    ) -> None:
        buffer: list[str] = []
        try:
            async for token in self.ai.stream_learn(topic.name, mode, history):
                buffer.append(token)
                queue.put_nowait(sse_frame({"token": token}))
            # Only after the stream completed: a partial answer is never stored.
            await self.chats.push_message(
                session_id, Message(role=Role.AI, content="".join(buffer), timestamp=utc_now())
            )
            queue.put_nowait(sse_frame("[DONE]"))
        except Exception as exc:
            logger.error(
                "Learn Mode stream failed",
                exc_info=not isinstance(exc, AiStreamError | AiUnavailableError),
                extra={"error_code": ErrorCode.AI_SERVICE_ERROR.name, "topic_id": topic_id, "error": str(exc)},
            )
            queue.put_nowait(sse_frame({"error": STREAM_FAILED_MESSAGE}))
        finally:
            queue.put_nowait(None)

    async def shutdown(self, grace_seconds: float = 5.0) -> None:
        """Let in-flight answers finish (so they are saved) before the Mongo client closes."""
        if not self._tasks:
            return
        _, pending = await asyncio.wait(self._tasks, timeout=grace_seconds)
        for task in pending:
            task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)
