import asyncio
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.clients.ai_client import AiClient
from app.config import settings
from app.db import create_client, ensure_index
from app.errors import register_exception_handlers
from app.logging_config import RequestIdMiddleware, setup_structured_logging
from app.repositories.chat_sessions import ChatSessionsRepository
from app.repositories.mock_interview_reports import MockInterviewReportsRepository
from app.repositories.mock_interview_sessions import MockInterviewSessionsRepository
from app.repositories.test_reports import TestReportsRepository
from app.repositories.test_sessions import TestSessionsRepository
from app.repositories.topics import TopicsRepository
from app.routers import chat, interviews, tests, topics
from app.services.chat_service import ChatService
from app.services.mock_interview_service import MockInterviewService
from app.services.test_service import TestService
from app.services.topic_service import TopicService

setup_structured_logging("topic-service", settings.log_level)


async def ensure_indexes(db) -> None:
    await ensure_index(db.topics, [("userId", 1), ("name", 1)], "user_name_unique", unique=True)
    await ensure_index(db.topics, "publicId", "publicId", unique=True, sparse=True)
    await ensure_index(db.chat_sessions, [("userId", 1), ("topicId", 1)], "user_topic_unique", unique=True)
    for name in ("test_sessions", "test_reports", "mock_interview_sessions", "mock_interview_reports"):
        await ensure_index(db[name], "topicId", "topicId")
        await ensure_index(db[name], "userId", "userId")
    await ensure_index(db.test_reports, "testSessionId", "testSessionId")
    await ensure_index(db.mock_interview_reports, "mockInterviewSessionId", "mockInterviewSessionId")


@asynccontextmanager
async def lifespan(app: FastAPI):
    client = create_client()
    db = client[settings.mongodb_db]
    http = httpx.AsyncClient(timeout=httpx.Timeout(connect=5, read=90, write=30, pool=5))
    await ensure_indexes(db)

    ai = AiClient(http, settings.ai_service_url, settings.internal_api_key)
    topics_repo = TopicsRepository(db.topics)
    chats_repo = ChatSessionsRepository(db.chat_sessions)
    app.state.mongo = client
    app.state.db = db
    app.state.http = http
    app.state.topic_service = TopicService(topics_repo, chats_repo)
    app.state.chat_service = ChatService(topics_repo, chats_repo, ai)
    app.state.test_service = TestService(
        topics_repo, TestSessionsRepository(db.test_sessions), TestReportsRepository(db.test_reports), ai
    )
    app.state.interview_service = MockInterviewService(
        topics_repo,
        MockInterviewSessionsRepository(db.mock_interview_sessions),
        MockInterviewReportsRepository(db.mock_interview_reports),
        ai,
    )
    yield
    await app.state.chat_service.shutdown()  # in-flight answers get saved before Mongo closes
    await http.aclose()
    await client.close()


# redirect_slashes=False: a 307 here would point the browser at the internal host name.
app = FastAPI(title="PrepPilot Topic Service", lifespan=lifespan, redirect_slashes=False)
register_exception_handlers(app)
app.add_middleware(RequestIdMiddleware)
app.include_router(topics.router)
app.include_router(chat.router)
app.include_router(tests.router)
app.include_router(interviews.router)


@app.get("/health")
async def health(request: Request):
    try:
        async with asyncio.timeout(2):
            await request.app.state.mongo.admin.command("ping")
    except Exception:
        return JSONResponse({"status": "down"}, status_code=503)
    return {"status": "ok"}
