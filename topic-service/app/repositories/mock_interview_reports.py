from pymongo.asynchronous.collection import AsyncCollection

from app.models.mock_interview_report import MockInterviewReport
from app.timeutil import utc_now


def _from_doc(doc: dict | None) -> MockInterviewReport | None:
    if doc is None:
        return None
    data = dict(doc)
    data["id"] = str(data.pop("_id"))
    return MockInterviewReport.model_validate(data)


class MockInterviewReportsRepository:
    def __init__(self, collection: AsyncCollection) -> None:
        self.collection = collection

    async def find_by_session_id(self, session_id: str) -> MockInterviewReport | None:
        return _from_doc(await self.collection.find_one({"mockInterviewSessionId": session_id}, sort=[("_id", 1)]))

    async def find_by_session_ids(self, session_ids: list[str]) -> dict[str, MockInterviewReport]:
        """Batch lookup for the history list: one query however many interviews there are."""
        if not session_ids:
            return {}
        cursor = self.collection.find({"mockInterviewSessionId": {"$in": session_ids}}).sort("_id", 1)
        reports: dict[str, MockInterviewReport] = {}
        async for doc in cursor:
            report = _from_doc(doc)
            reports.setdefault(report.mock_interview_session_id, report)  # first wins, as Java's merge did
        return reports

    async def insert(self, report: MockInterviewReport) -> MockInterviewReport:
        report.created_at = utc_now()
        doc = report.model_dump(by_alias=True, exclude_none=True, exclude={"id"})
        result = await self.collection.insert_one(doc)
        report.id = str(result.inserted_id)
        return report
