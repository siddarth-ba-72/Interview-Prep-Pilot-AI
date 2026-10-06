import asyncio
import json

import pytest
from pymongo.errors import DuplicateKeyError  # noqa: F401  (documented: the race test uses FakeChats)

from app.clients.ai_client import AiStreamError, AiUnavailableError
from app.errors import ApiError
from app.models.chat_session import ChatSession, Message, Role
from app.models.topic import Topic
from app.services.chat_service import (
    MODE_CLARIFY,
    MODE_FOLLOW_UP,
    MODE_GENERATE_CONTENT,
    STREAM_FAILED_MESSAGE,
    ChatService,
    determine_mode,
    sse_frame,
)
from app.timeutil import utc_now
from tests.unit.fakes import FakeAi, FakeChats, FakeTopics


@pytest.fixture
def topics():
    return FakeTopics()


@pytest.fixture
def chats():
    return FakeChats()


async def setup(topics, chats, ai, existing: int | None = None):
    """A topic 'pub-1' for u1; optionally a session already holding `existing` messages."""
    topic = await topics.insert(Topic(public_id="pub-1", user_id="u1", name="Kafka"))
    service = ChatService(topics, chats, ai)
    if existing is not None:
        roles = [Role.AI, Role.USER]
        msgs = [Message(role=roles[i % 2], content=f"old{i}", timestamp=utc_now()) for i in range(existing)]
        await chats.insert(ChatSession(user_id="u1", topic_id=topic.id, messages=msgs))
    return service, topic


async def collect(frames) -> list[str]:
    return [frame async for frame in frames]


def stored(chats) -> list[Message]:
    return next(iter(chats.items.values())).messages


# ---------- mode selection ----------

@pytest.mark.parametrize(
    "count, mode", [(0, "GENERATE_CONTENT"), (1, "GENERATE_CONTENT"), (2, "FOLLOW_UP"), (9, "FOLLOW_UP")]
)
def test_mode_is_chosen_from_the_count_before_the_new_message(count, mode):
    assert determine_mode(count) == mode


async def test_first_reply_after_clarification_generates_content(topics, chats):
    ai = FakeAi(chats)
    service, _ = await setup(topics, chats, ai, existing=1)
    await collect(await service.start_reply("u1", "pub-1", "teach me"))
    assert ai.calls[0]["mode"] == MODE_GENERATE_CONTENT


async def test_later_replies_are_follow_ups(topics, chats):
    ai = FakeAi(chats)
    service, _ = await setup(topics, chats, ai, existing=3)
    await collect(await service.start_reply("u1", "pub-1", "and then?"))
    assert ai.calls[0]["mode"] == MODE_FOLLOW_UP


async def test_ai_receives_the_full_history_including_the_new_message(topics, chats):
    ai = FakeAi(chats)
    service, _ = await setup(topics, chats, ai, existing=25)  # more than one visible page
    await collect(await service.start_reply("u1", "pub-1", "newest"))
    sent = ai.calls[0]["messages"]
    assert len(sent) == 26 and sent[-1] == {"role": "USER", "content": "newest"}
    assert sent[0] == {"role": "AI", "content": "old0"}
    assert ai.calls[0]["topic"] == "Kafka"


# ---------- SSE wire format ----------

def test_frame_bytes():
    assert sse_frame({"token": "hi"}) == 'data: {"token": "hi"}\n\n'
    assert sse_frame("[DONE]") == "data: [DONE]\n\n"
    assert sse_frame({"error": "x"}) == 'data: {"error": "x"}\n\n'


def test_newlines_inside_a_token_never_break_framing():
    frame = sse_frame({"token": "line1\nline2\n\nline4"})
    assert frame.count("\n\n") == 1 and frame.endswith("\n\n")
    assert json.loads(frame[len("data: "):]) == {"token": "line1\nline2\n\nline4"}


async def test_stream_is_tokens_then_done(topics, chats):
    service, _ = await setup(topics, chats, FakeAi(chats, tokens=["Hel", "lo\n", "!"]), existing=1)
    frames = await collect(await service.start_reply("u1", "pub-1", "hi"))
    assert frames == ['data: {"token": "Hel"}\n\n', 'data: {"token": "lo\\n"}\n\n', 'data: {"token": "!"}\n\n',
                      "data: [DONE]\n\n"]


# ---------- persistence ----------

async def test_user_message_is_saved_before_the_ai_is_called(topics, chats):
    ai = FakeAi(chats)
    service, _ = await setup(topics, chats, ai, existing=1)
    await collect(await service.start_reply("u1", "pub-1", "question"))
    assert ai.calls[0]["stored_counts"] == [2]  # the session already held the USER message


async def test_ai_message_is_saved_after_completion(topics, chats):
    service, _ = await setup(topics, chats, FakeAi(chats, tokens=["a", "b", "c"]), existing=1)
    await collect(await service.start_reply("u1", "pub-1", "question"))
    roles = [(m.role, m.content) for m in stored(chats)]
    assert roles[-2:] == [("USER", "question"), ("AI", "abc")]


async def test_message_content_is_stored_verbatim(topics, chats):
    service, _ = await setup(topics, chats, FakeAi(chats), existing=1)
    await collect(await service.start_reply("u1", "pub-1", "  spaced  \n"))
    assert stored(chats)[1].content == "  spaced  \n"


# ---------- failures ----------

@pytest.mark.parametrize("error", [AiStreamError("upstream said no"), AiUnavailableError("down"), RuntimeError("bug")])
async def test_mid_stream_failure_gives_an_error_frame_and_no_ai_message(topics, chats, error):
    ai = FakeAi(chats, tokens=["partial ", "answer"], fail_after=1, error=error)
    service, _ = await setup(topics, chats, ai, existing=1)
    frames = await collect(await service.start_reply("u1", "pub-1", "question"))
    assert frames[0] == 'data: {"token": "partial "}\n\n'
    assert frames[-1] == sse_frame({"error": STREAM_FAILED_MESSAGE})
    assert "data: [DONE]\n\n" not in frames  # the stream closes without [DONE]
    assert [(m.role, m.content) for m in stored(chats)][-1] == ("USER", "question")  # USER kept, no partial AI


async def test_failure_before_the_first_token(topics, chats):
    ai = FakeAi(chats, tokens=[], fail_after=0, error=AiUnavailableError("down"))
    service, _ = await setup(topics, chats, ai, existing=1)
    frames = await collect(await service.start_reply("u1", "pub-1", "q"))
    assert frames == [sse_frame({"error": STREAM_FAILED_MESSAGE})]


async def test_unknown_topic_raises_before_any_frame(topics, chats):
    service, _ = await setup(topics, chats, FakeAi(chats), existing=1)
    with pytest.raises(ApiError) as exc:
        await service.start_reply("u1", "missing", "hi")
    assert (exc.value.status_code, exc.value.code) == (404, "TOPIC_NOT_FOUND")


async def test_other_users_topic_is_not_found(topics, chats):
    service, _ = await setup(topics, chats, FakeAi(chats), existing=1)
    with pytest.raises(ApiError) as exc:
        await service.start_reply("someone-else", "pub-1", "hi")
    assert exc.value.code == "TOPIC_NOT_FOUND"


async def test_reply_without_a_session_raises_and_stores_nothing(topics, chats):
    ai = FakeAi(chats)
    service, _ = await setup(topics, chats, ai)  # no session
    with pytest.raises(ApiError) as exc:
        await service.start_reply("u1", "pub-1", "hi")
    assert exc.value.code == "CHAT_SESSION_NOT_FOUND"
    assert chats.items == {} and ai.calls == []


# ---------- client disconnect ----------

async def test_answer_is_saved_even_if_the_client_disconnects_mid_stream(topics, chats):
    ai = FakeAi(chats, tokens=["Hel", "lo ", "there"], delay=0.01)
    service, _ = await setup(topics, chats, ai, existing=1)
    frames = await service.start_reply("u1", "pub-1", "question")

    iterator = frames.__aiter__()
    assert await iterator.__anext__() == 'data: {"token": "Hel"}\n\n'
    await iterator.aclose()  # what Starlette does to the response generator when the browser goes away

    assert len(service._tasks) == 1  # the producer is still running, and strongly referenced
    await asyncio.wait_for(asyncio.gather(*service._tasks), timeout=5)
    assert service._tasks == set()  # discarded once done
    assert [(m.role, m.content) for m in stored(chats)][-2:] == [("USER", "question"), ("AI", "Hello there")]


async def test_a_failed_stream_after_disconnect_still_saves_nothing_partial(topics, chats):
    ai = FakeAi(chats, tokens=["a", "b", "c"], fail_after=2, delay=0.01)
    service, _ = await setup(topics, chats, ai, existing=1)
    frames = await service.start_reply("u1", "pub-1", "question")
    iterator = frames.__aiter__()
    await iterator.__anext__()
    await iterator.aclose()
    await asyncio.wait_for(asyncio.gather(*service._tasks), timeout=5)
    assert stored(chats)[-1].role == "USER"


async def test_shutdown_waits_for_in_flight_answers(topics, chats):
    ai = FakeAi(chats, tokens=["x", "y"], delay=0.02)
    service, _ = await setup(topics, chats, ai, existing=1)
    await service.start_reply("u1", "pub-1", "question")
    await service.shutdown()
    assert stored(chats)[-1].content == "xy"


async def test_shutdown_cancels_tasks_that_outlive_the_grace_period(topics, chats):
    ai = FakeAi(chats, tokens=["x"] * 1000, delay=0.05)
    service, _ = await setup(topics, chats, ai, existing=1)
    await service.start_reply("u1", "pub-1", "question")
    await service.shutdown(grace_seconds=0.05)
    assert service._tasks == set()


# ---------- creating the session (CLARIFY) ----------

async def test_first_open_calls_ai_in_clarify_mode_and_stores_it_as_the_first_ai_message(topics, chats):
    ai = FakeAi(chats, tokens=["What ", "level?"])
    service, topic = await setup(topics, chats, ai)
    response = await service.get_or_create("u1", "pub-1")
    assert ai.calls == [{"topic": "Kafka", "mode": MODE_CLARIFY, "messages": [], "stored_counts": []}]
    assert response.topic_id == "pub-1"  # the publicId, not the _id
    assert [(m.role, m.content) for m in response.messages] == [("AI", "What level?")]
    assert next(iter(chats.items.values())).topic_id == topic.id  # stored against the _id


async def test_second_open_does_not_call_ai_again(topics, chats):
    ai = FakeAi(chats)
    service, _ = await setup(topics, chats, ai)
    await service.get_or_create("u1", "pub-1")
    await service.get_or_create("u1", "pub-1")
    assert len(ai.calls) == 1


@pytest.mark.parametrize(
    "error, status, code, message",
    [
        (AiStreamError("bad"), 502, "AI_SERVICE_ERROR", "AI service error"),
        (AiUnavailableError("down"), 502, "AI_SERVICE_UNAVAILABLE", "AI service temporarily unavailable"),
    ],
)
async def test_ai_failure_while_creating_the_session(topics, chats, error, status, code, message):
    ai = FakeAi(chats, tokens=[], fail_after=0, error=error)
    service, _ = await setup(topics, chats, ai)
    with pytest.raises(ApiError) as exc:
        await service.get_or_create("u1", "pub-1")
    assert (exc.value.status_code, exc.value.code, exc.value.message) == (status, code, message)
    assert chats.items == {}  # nothing half-created


async def test_concurrent_creation_returns_the_winners_session(topics, chats):
    chats.raise_duplicate_once = True
    service, _ = await setup(topics, chats, FakeAi(chats))
    response = await service.get_or_create("u1", "pub-1")
    assert [m.content for m in response.messages] == ["winner"]


async def test_get_or_create_for_unknown_topic(topics, chats):
    service, _ = await setup(topics, chats, FakeAi(chats))
    with pytest.raises(ApiError) as exc:
        await service.get_or_create("u1", "nope")
    assert exc.value.code == "TOPIC_NOT_FOUND"
