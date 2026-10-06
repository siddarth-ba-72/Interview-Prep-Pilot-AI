from bson import ObjectId
from pymongo.asynchronous.collection import AsyncCollection

from app.models.mock_interview import MockInterviewSession, Status
from app.timeutil import utc_now


def _from_doc(doc: dict | None) -> MockInterviewSession | None:
    if doc is None:
        return None
    data = dict(doc)
    data["id"] = str(data.pop("_id"))
    return MockInterviewSession.model_validate(data)


def _to_doc(session: MockInterviewSession) -> dict:
    # exclude_none: a finished session simply has no currentQuestion field, exactly as Spring stored it.
    return session.model_dump(by_alias=True, exclude_none=True, exclude={"id"})


class MockInterviewSessionsRepository:
    def __init__(self, collection: AsyncCollection) -> None:
        self.collection = collection

    async def find_by_id(self, session_id: str) -> MockInterviewSession | None:
        if not ObjectId.is_valid(session_id):
            return None
        return _from_doc(await self.collection.find_one({"_id": ObjectId(session_id)}))

    async def find_in_progress(self, topic_id: str, user_id: str) -> MockInterviewSession | None:
        query = {"topicId": topic_id, "userId": user_id, "status": Status.IN_PROGRESS.value}
        return _from_doc(await self.collection.find_one(query))

    async def find_by_topic_and_user(self, topic_id: str, user_id: str) -> list[MockInterviewSession]:
        cursor = self.collection.find({"topicId": topic_id, "userId": user_id}).sort("_id", 1)
        return [_from_doc(doc) async for doc in cursor]

    async def insert(self, session: MockInterviewSession) -> MockInterviewSession:
        session.created_at = utc_now()
        result = await self.collection.insert_one(_to_doc(session))
        session.id = str(result.inserted_id)
        return session

    async def save(self, session: MockInterviewSession) -> MockInterviewSession:
        """Whole-document replace, like Spring Data's save()."""
        if session.id is None:
            return await self.insert(session)
        await self.collection.replace_one({"_id": ObjectId(session.id)}, _to_doc(session), upsert=True)
        return session
