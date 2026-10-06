from fastapi import APIRouter, Depends, Response

from app.deps import current_user_id, get_topic_service
from app.schemas.topics import CreateTopicRequest, TopicResponse
from app.services.topic_service import TopicService

router = APIRouter(prefix="/api/v1/topics")


@router.post("", status_code=201, response_model=TopicResponse)
async def create_topic(
    body: CreateTopicRequest, user_id: str = Depends(current_user_id), topics: TopicService = Depends(get_topic_service)
):
    body.ensure_valid()
    return await topics.create(user_id, body.name)


@router.get("", response_model=list[TopicResponse])
async def list_topics(user_id: str = Depends(current_user_id), topics: TopicService = Depends(get_topic_service)):
    return await topics.list(user_id)


@router.delete("/{topic_id}", status_code=204)
async def delete_topic(
    topic_id: str, user_id: str = Depends(current_user_id), topics: TopicService = Depends(get_topic_service)
):
    await topics.delete(user_id, topic_id)
    return Response(status_code=204)
