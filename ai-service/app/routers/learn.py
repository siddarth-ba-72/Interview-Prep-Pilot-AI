import json
import logging

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.auth import require_caller_identity
from app.llm import stream_completion
from app.prompts import build_messages
from app.schemas import LearnStreamRequest
from app.scope_validator import validate_topic_scope, validate_user_message_scope

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai/learn", tags=["learn"])


def _sse_event(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


async def _event_stream(request: LearnStreamRequest):
    # Validate topic scope
    is_valid_topic, error_msg = await validate_topic_scope(request.topic_name)
    if not is_valid_topic:
        yield _sse_event({"token": error_msg})
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
                yield _sse_event({"token": msg_error})
                yield "data: [DONE]\n\n"
                return

    messages = build_messages(request.topic_name, request.mode, request.messages)
    try:
        async for token in stream_completion(messages):
            yield _sse_event({"token": token})
    except Exception:
        logger.exception("LLM streaming failed")
        yield _sse_event({"error": "The AI response could not be completed. Please try again."})
        return
    yield "data: [DONE]\n\n"


@router.post("/stream")
async def learn_stream(request: LearnStreamRequest, caller: str = Depends(require_caller_identity)):
    return StreamingResponse(_event_stream(request), media_type="text/event-stream")
