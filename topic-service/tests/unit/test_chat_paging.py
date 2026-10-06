from datetime import UTC, datetime, timedelta

import pytest

from app.errors import ApiError
from app.models.chat_session import ChatSession, Message, Role
from app.services.chat_service import PAGE_SIZE, ChatService, page
from tests.unit.fakes import FakeAi, FakeChats, FakeTopics

BASE = datetime(2026, 1, 1, tzinfo=UTC)


def make_messages(n: int) -> list[Message]:
    return [
        Message(role=Role.AI if i % 2 == 0 else Role.USER, content=f"m{i}", timestamp=BASE + timedelta(seconds=i))
        for i in range(n)
    ]


def contents(messages) -> list[str]:
    return [m.content for m in messages]


@pytest.mark.parametrize(
    "total, expected_len, has_more, first",
    [(0, 0, False, None), (1, 1, False, "m0"), (20, 20, False, "m0"), (21, 20, True, "m1"), (45, 20, True, "m25")],
)
def test_latest_page(total, expected_len, has_more, first):
    messages, more = page(make_messages(total))
    assert len(messages) == expected_len and more is has_more
    if first:
        assert messages[0].content == first
        assert messages[-1].content == f"m{total - 1}"


def test_page_size_is_twenty():
    assert PAGE_SIZE == 20


def test_cursor_returns_the_twenty_messages_before_it_in_chronological_order():
    msgs = make_messages(45)
    older, more = page(msgs, before=msgs[30].timestamp)  # strictly before m30 -> m0..m29
    assert contents(older) == [f"m{i}" for i in range(10, 30)]
    assert more is True


def test_cursor_walks_back_to_the_start():
    msgs = make_messages(45)
    older, more = page(msgs, before=msgs[10].timestamp)
    assert contents(older) == [f"m{i}" for i in range(10)]
    assert more is False


def test_cursor_older_than_every_message_gives_an_empty_page():
    msgs = make_messages(5)
    assert page(msgs, before=BASE - timedelta(days=1)) == ([], False)


def test_cursor_is_exclusive():
    msgs = make_messages(5)
    older, _ = page(msgs, before=msgs[3].timestamp)
    assert contents(older) == ["m0", "m1", "m2"]


def test_cursor_newer_than_every_message_behaves_like_no_cursor():
    msgs = make_messages(30)
    assert page(msgs, before=BASE + timedelta(days=1)) == page(msgs)


def test_pages_chain_without_overlap_or_gaps():
    msgs = make_messages(45)
    seen, before = [], None
    while True:
        chunk, more = page(msgs, before)
        seen = contents(chunk) + seen
        if not more:
            break
        before = chunk[0].timestamp
    assert seen == [f"m{i}" for i in range(45)]


async def test_get_messages_requires_an_existing_session():
    topics, chats = FakeTopics(), FakeChats()
    service = ChatService(topics, chats, FakeAi())
    from app.models.topic import Topic

    topic = await topics.insert(Topic(public_id="pub-1", user_id="u1", name="Kafka"))
    with pytest.raises(ApiError) as exc:
        await service.get_messages("u1", "pub-1", None)
    assert (exc.value.status_code, exc.value.code) == (404, "CHAT_SESSION_NOT_FOUND")
    assert exc.value.message == "No chat session found for topic: pub-1. Open Learn Mode first."
    await chats.insert(ChatSession(user_id="u1", topic_id=topic.id, messages=make_messages(3)))
    assert len((await service.get_messages("u1", "pub-1", None)).messages) == 3
