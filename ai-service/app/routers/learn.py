import json
import logging

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.auth import require_caller_identity
from app.llm import stream_completion
from app.prompts import build_messages
from app.schemas import LearnStreamRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai/learn", tags=["learn"])


def _sse_event(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


async def _event_stream(request: LearnStreamRequest):
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
