import pytest

from app.errors import ApiError
from app.schemas.chat import SendMessageRequest
from app.schemas.topics import CreateTopicRequest


def message(request) -> str:
    with pytest.raises(ApiError) as exc:
        request.ensure_valid()
    assert (exc.value.status_code, exc.value.code) == (400, "USER_INVALID_INPUT")
    return exc.value.message


@pytest.mark.parametrize("name", [None, "", "   ", "\t\n"])
def test_blank_topic_name(name):
    assert message(CreateTopicRequest(name=name)) == "Topic name is required"


def test_topic_name_length_limit():
    CreateTopicRequest(name="x" * 100).ensure_valid()
    assert message(CreateTopicRequest(name="x" * 101)) == "Topic name must be at most 100 characters"


def test_topic_name_length_counts_utf16_units_like_java():
    CreateTopicRequest(name="😀" * 50).ensure_valid()  # 100 UTF-16 units
    assert message(CreateTopicRequest(name="😀" * 51)) == "Topic name must be at most 100 characters"
    CreateTopicRequest(name="é" * 100).ensure_valid()  # BMP characters count once


def test_topic_name_is_not_trimmed():
    request = CreateTopicRequest(name="  Kafka  ")
    request.ensure_valid()
    assert request.name == "  Kafka  "


@pytest.mark.parametrize("content", [None, "", "  ", "\n"])
def test_blank_message(content):
    assert message(SendMessageRequest(content=content)) == "Message content is required"


def test_message_content_is_not_trimmed():
    request = SendMessageRequest(content="  hello  ")
    request.ensure_valid()
    assert request.content == "  hello  "
