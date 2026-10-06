from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.deps import current_user_id, get_chat_service
from app.errors import ApiError
from app.schemas.chat import ChatSessionResponse, PagedMessagesResponse, SendMessageRequest
from app.services.chat_service import ChatService, sse_frame
from app.timeutil import parse_instant

router = APIRouter(prefix="/api/v1/topics/{topic_id}/chat")

SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}


@router.get("", response_model=ChatSessionResponse)
async def get_or_create_chat(
    topic_id: str, user_id: str = Depends(current_user_id), chat: ChatService = Depends(get_chat_service)
):
    return await chat.get_or_create(user_id, topic_id)


@router.get("/messages", response_model=PagedMessagesResponse)
async def get_messages(
    topic_id: str,
    before: str | None = None,
    user_id: str = Depends(current_user_id),
    chat: ChatService = Depends(get_chat_service),
):
    cursor = None
    if before is not None:
        try:
            cursor = parse_instant(before)
        except ValueError:
            raise ApiError(400, "USER_INVALID_INPUT", "Invalid 'before' timestamp; expected ISO-8601") from None
    return await chat.get_messages(user_id, topic_id, cursor)


@router.post("/messages")
async def send_message(
    topic_id: str,
    body: SendMessageRequest,
    user_id: str = Depends(current_user_id),
    chat: ChatService = Depends(get_chat_service),
):
    body.ensure_valid()  # a blank message is a plain 400
    try:
        frames = await chat.start_reply(user_id, topic_id, body.content)
    except ApiError as error:
        # Preserved from the Java controller: a missing topic or session is still a 200 SSE, carrying one error frame.
        frames = _single_frame(sse_frame({"error": error.message}))
    return StreamingResponse(frames, media_type="text/event-stream", headers=SSE_HEADERS)


async def _single_frame(frame: str):
    yield frame
