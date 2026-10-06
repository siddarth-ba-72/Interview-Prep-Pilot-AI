from fastapi import APIRouter, Depends

from app.deps import current_user_id, get_interview_service
from app.schemas.interviews import (
    AnswerInterviewRequest,
    InterviewAnswerResponse,
    InterviewReportResponse,
    InterviewStartResponse,
    InterviewStateResponse,
    InterviewSummaryResponse,
    StartInterviewRequest,
)
from app.services.mock_interview_service import MockInterviewService

router = APIRouter(prefix="/api/v1/topics/{topic_id}/interviews")


@router.post("", status_code=201, response_model=InterviewStartResponse)
async def start_interview(
    topic_id: str,
    body: StartInterviewRequest | None = None,  # optional: resuming needs no config
    user_id: str = Depends(current_user_id),
    interviews: MockInterviewService = Depends(get_interview_service),
):
    return await interviews.start(user_id, topic_id, body)


@router.get("", response_model=list[InterviewSummaryResponse])
async def list_interviews(
    topic_id: str,
    user_id: str = Depends(current_user_id),
    interviews: MockInterviewService = Depends(get_interview_service),
):
    return await interviews.list(user_id, topic_id)


@router.get("/{session_id}", response_model=InterviewStateResponse)
async def get_interview(
    topic_id: str,
    session_id: str,
    user_id: str = Depends(current_user_id),
    interviews: MockInterviewService = Depends(get_interview_service),
):
    return await interviews.get(user_id, topic_id, session_id)


@router.post("/{session_id}/answer", response_model=InterviewAnswerResponse)
async def answer_interview(
    topic_id: str,
    session_id: str,
    body: AnswerInterviewRequest | None = None,  # a missing body is a blank answer
    user_id: str = Depends(current_user_id),
    interviews: MockInterviewService = Depends(get_interview_service),
):
    return await interviews.answer(user_id, topic_id, session_id, body or AnswerInterviewRequest())


@router.post("/{session_id}/end", response_model=InterviewReportResponse)
async def end_interview(
    topic_id: str,
    session_id: str,
    user_id: str = Depends(current_user_id),
    interviews: MockInterviewService = Depends(get_interview_service),
):
    return await interviews.end(user_id, topic_id, session_id)


@router.get("/{session_id}/report", response_model=InterviewReportResponse)
async def get_interview_report(
    topic_id: str,
    session_id: str,
    user_id: str = Depends(current_user_id),
    interviews: MockInterviewService = Depends(get_interview_service),
):
    return await interviews.report(user_id, topic_id, session_id)
