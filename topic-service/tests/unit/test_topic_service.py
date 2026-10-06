import uuid

import pytest

from app.errors import ApiError
from app.models.chat_session import ChatSession
from app.services.topic_service import TopicService
from tests.unit.fakes import FakeChats, FakeTopics


@pytest.fixture
def chats():
    return FakeChats()


@pytest.fixture
def topics():
    return FakeTopics()


@pytest.fixture
def service(topics, chats):
    return TopicService(topics, chats)


async def test_create_returns_public_id_and_zero_tests(service, topics):
    created = await service.create("u1", "Kafka")
    uuid.UUID(created.id)
    assert created.name == "Kafka" and created.test_count == 0 and created.avg_score is None
    stored = next(iter(topics.items.values()))
    assert stored.public_id == created.id and stored.id != created.id  # the Mongo _id is never exposed


async def test_name_is_stored_as_submitted(service, topics):
    await service.create("u1", "  Spaced Name  ")
    assert next(iter(topics.items.values())).name == "  Spaced Name  "


async def test_duplicate_detection_ignores_case(service):
    await service.create("u1", "Kafka")
    with pytest.raises(ApiError) as exc:
        await service.create("u1", "KAFKA")
    assert (exc.value.status_code, exc.value.code) == (409, "DUPLICATE_TOPIC")
    assert exc.value.message == "Topic already exists: KAFKA"


@pytest.mark.parametrize("name", ["C++", "a.b*", "(x)", "[y]", "a|b", "^$", "back\\slash", "q?"])
async def test_regex_metacharacters_are_matched_literally(service, name):
    await service.create("u1", name)
    with pytest.raises(ApiError):
        await service.create("u1", name.lower() if name.lower() != name else name)


async def test_regex_characters_do_not_act_as_wildcards(service):
    await service.create("u1", "abc")
    await service.create("u1", "a.c")  # "a.c" must not collide with "abc"
    await service.create("u1", "C++")
    await service.create("u1", "C")  # "C+" patterns must not collide with "C"


async def test_same_name_for_different_users_is_fine(service):
    await service.create("u1", "Kafka")
    await service.create("u2", "Kafka")


async def test_list_is_newest_first_and_scoped_to_the_user(service):
    for name in ("first", "second", "third"):
        await service.create("u1", name)
    await service.create("u2", "someone else's")
    assert [t.name for t in await service.list("u1")] == ["third", "second", "first"]
    assert [t.name for t in await service.list("u2")] == ["someone else's"]


async def test_delete_removes_topic_and_its_chat_session(service, topics, chats):
    created = await service.create("u1", "Kafka")
    topic_oid = next(iter(topics.items))
    await chats.insert(ChatSession(user_id="u1", topic_id=topic_oid))
    await service.delete("u1", created.id)
    assert topics.items == {} and chats.items == {}


async def test_delete_unknown_topic_is_404(service):
    with pytest.raises(ApiError) as exc:
        await service.delete("u1", "nope")
    assert (exc.value.status_code, exc.value.code) == (404, "TOPIC_NOT_FOUND")
    assert exc.value.message == "Topic not found: nope"


async def test_another_users_topic_is_404_and_untouched(service, topics):
    created = await service.create("u1", "Kafka")
    with pytest.raises(ApiError) as exc:
        await service.delete("u2", created.id)
    assert exc.value.status_code == 404
    assert len(topics.items) == 1


async def test_deleting_leaves_other_collections_alone_known_issue_k2(service, topics):
    created = await service.create("u1", "Kafka")
    await service.delete("u1", created.id)  # no tests/interviews repositories are touched
    assert topics.items == {}
