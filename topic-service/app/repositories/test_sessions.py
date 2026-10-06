from datetime import datetime

from bson import ObjectId
from pymongo.asynchronous.collection import AsyncCollection

from app.models.test_session import Answer, Status, TestSession
from app.timeutil import utc_now


def _from_doc(doc: dict | None) -> TestSession | None:
    if doc is None:
        return None
    data = dict(doc)
    data["id"] = str(data.pop("_id"))
    return TestSession.model_validate(data)


class TestSessionsRepository:
    __test__ = False  # not a pytest class

    def __init__(self, collection: AsyncCollection) -> None:
        self.collection = collection

    async def find_by_id(self, session_id: str) -> TestSession | None:
        if not ObjectId.is_valid(session_id):
            return None
        return _from_doc(await self.collection.find_one({"_id": ObjectId(session_id)}))

    async def find_in_progress(self, topic_id: str, user_id: str) -> TestSession | None:
        return _from_doc(
            await self.collection.find_one({"topicId": topic_id, "userId": user_id, "status": Status.IN_PROGRESS.value})
        )

    async def count_by_topic_and_user(self, topic_id: str, user_id: str) -> int:
        return await self.collection.count_documents({"topicId": topic_id, "userId": user_id})

    async def find_by_ids(self, session_ids: list[str]) -> dict[str, TestSession]:
        """One $in query instead of one lookup per report."""
        oids = [ObjectId(i) for i in set(session_ids) if ObjectId.is_valid(i)]
        if not oids:
            return {}
        sessions = [_from_doc(doc) async for doc in self.collection.find({"_id": {"$in": oids}})]
        return {s.id: s for s in sessions}

    async def insert(self, session: TestSession) -> TestSession:
        session.created_at = utc_now()
        doc = session.model_dump(by_alias=True, exclude_none=True, exclude={"id"})
        result = await self.collection.insert_one(doc)
        session.id = str(result.inserted_id)
        return session

    async def complete(self, session_id: str, answers: list[Answer], raw_score: int, completed_at: datetime) -> bool:
        """Mark COMPLETED, but only if it is still IN_PROGRESS. False means another submit won the race."""
        result = await self.collection.update_one(
            {"_id": ObjectId(session_id), "status": Status.IN_PROGRESS.value},
            {
                "$set": {
                    "answers": [a.model_dump(by_alias=True, exclude_none=True) for a in answers],
                    "rawScore": raw_score,
                    "status": Status.COMPLETED.value,
                    "completedAt": completed_at,
                }
            },
        )
        return result.modified_count == 1
