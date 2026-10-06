from pymongo.asynchronous.collection import AsyncCollection

from app.models.test_report import TestReport
from app.timeutil import utc_now


def _from_doc(doc: dict | None) -> TestReport | None:
    if doc is None:
        return None
    data = dict(doc)
    data["id"] = str(data.pop("_id"))
    return TestReport.model_validate(data)


class TestReportsRepository:
    __test__ = False  # not a pytest class

    def __init__(self, collection: AsyncCollection) -> None:
        self.collection = collection

    async def find_by_session_id(self, test_session_id: str) -> TestReport | None:
        return _from_doc(await self.collection.find_one({"testSessionId": test_session_id}))

    async def find_latest_attempt(self, topic_id: str, user_id: str) -> TestReport | None:
        doc = await self.collection.find_one(
            {"topicId": topic_id, "userId": user_id}, sort=[("attemptNumber", -1), ("_id", -1)]
        )
        return _from_doc(doc)

    async def find_by_topic_and_user(self, topic_id: str, user_id: str) -> list[TestReport]:
        cursor = self.collection.find({"topicId": topic_id, "userId": user_id}).sort("_id", 1)
        return [_from_doc(doc) async for doc in cursor]

    async def insert(self, report: TestReport) -> TestReport:
        report.created_at = utc_now()
        doc = report.model_dump(by_alias=True, exclude_none=True, exclude={"id"})
        result = await self.collection.insert_one(doc)
        report.id = str(result.inserted_id)
        return report
