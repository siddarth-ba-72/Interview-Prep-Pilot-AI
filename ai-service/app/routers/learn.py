import json
import logging

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.auth import require_caller_identity
from app.exceptions import InvalidTopicError, ErrorCode
from app.llm import stream_completion
from app.prompts import build_messages
from app.schemas import LearnStreamRequest
from app.scope_validator import validate_topic_scope, validate_user_message_scope
from app.logging_config import user_id_context

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai/learn", tags=["learn"])


def _sse_event(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


async def _event_stream(request: LearnStreamRequest):
    # Validate topic scope
    is_valid_topic, error_msg = await validate_topic_scope(request.topic_name)
    if not is_valid_topic:
        user_id = user_id_context.get()
        log_record = logging.LogRecord(
            name=logger.name,
            level=logging.WARNING,
            pathname="",
            lineno=0,
            msg="Invalid topic",
            args=(),
            exc_info=None,
        )
        log_record.context_data = {
            "error_code": ErrorCode.USER_INVALID_TOPIC,
            "topic": request.topic_name,
        }
        logger.handle(log_record)
        yield _sse_event({"error": error_msg})
        yield "data: [DONE]\n\n"
        return

    # Validate user's latest message if in conversation mode
    if request.messages:
        latest_user_msg = next(
            (msg.content for msg in reversed(request.messages) if msg.role.value == "USER"),
            None
        )
        if latest_user_msg:
            is_valid_msg, msg_error = await validate_user_message_scope(
                request.topic_name, latest_user_msg
            )
            if not is_valid_msg:
                user_id = user_id_context.get()
                log_record = logging.LogRecord(
                    name=logger.name,
                    level=logging.WARNING,
                    pathname="",
                    lineno=0,
                    msg="User message out of scope",
                    args=(),
                    exc_info=None,
                )
                log_record.context_data = {
                    "error_code": ErrorCode.USER_INVALID_INPUT,
                    "topic": request.topic_name,
                }
                logger.handle(log_record)
                yield _sse_event({"error": msg_error})
                yield "data: [DONE]\n\n"
                return

    messages = build_messages(request.topic_name, request.mode, request.messages)
    try:
        async for token in stream_completion(messages):
            yield _sse_event({"token": token})
    except Exception as e:
        log_record = logging.LogRecord(
            name=logger.name,
            level=logging.ERROR,
            pathname="",
            lineno=0,
            msg="LLM streaming failed",
            args=(),
            exc_info=(type(e), e, e.__traceback__),
        )
        log_record.context_data = {
            "error_code": ErrorCode.SYSTEM_INTERNAL_ERROR,
            "topic": request.topic_name,
        }
        logger.handle(log_record)
        yield _sse_event({"error": "The AI response could not be completed. Please try again."})
        return
    yield "data: [DONE]\n\n"


@router.post("/stream")
async def learn_stream(request: LearnStreamRequest, caller: str = Depends(require_caller_identity)):
    return StreamingResponse(_event_stream(request), media_type="text/event-stream")
