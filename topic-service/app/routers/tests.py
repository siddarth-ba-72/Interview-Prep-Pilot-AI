from fastapi import APIRouter, Depends

from app.deps import current_user_id, get_test_service
from app.schemas.tests import SubmitTestRequest, TestListItemResponse, TestReportResponse, TestStartResponse
from app.services.test_service import TestService

router = APIRouter(prefix="/api/v1/topics/{topic_id}/tests")


@router.post("", status_code=201, response_model=TestStartResponse)
async def start_test(
    topic_id: str, user_id: str = Depends(current_user_id), tests: TestService = Depends(get_test_service)
):
    return await tests.start(user_id, topic_id)


@router.get("", response_model=list[TestListItemResponse])
async def list_tests(
    topic_id: str, user_id: str = Depends(current_user_id), tests: TestService = Depends(get_test_service)
):
    return await tests.list(user_id, topic_id)


@router.get("/{test_id}", response_model=TestStartResponse)
async def get_test(
    topic_id: str, test_id: str, user_id: str = Depends(current_user_id), tests: TestService = Depends(get_test_service)
):
    return await tests.get(user_id, topic_id, test_id)


@router.post("/{test_id}/submit", response_model=TestReportResponse)
async def submit_test(
    topic_id: str,
    test_id: str,
    body: SubmitTestRequest,
    user_id: str = Depends(current_user_id),
    tests: TestService = Depends(get_test_service),
):
    body.ensure_valid()
    return await tests.submit(user_id, topic_id, test_id, body)


@router.get("/{test_id}/report", response_model=TestReportResponse)
async def get_report(
    topic_id: str, test_id: str, user_id: str = Depends(current_user_id), tests: TestService = Depends(get_test_service)
):
    return await tests.report(user_id, topic_id, test_id)
