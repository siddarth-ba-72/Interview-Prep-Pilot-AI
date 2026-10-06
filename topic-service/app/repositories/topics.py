import re

from bson import ObjectId
from pymongo import ReturnDocument
from pymongo.asynchronous.collection import AsyncCollection

from app.models.topic import Topic
from app.timeutil import utc_now


def _from_doc(doc: dict | None) -> Topic | None:
    if doc is None:
        return None
    data = dict(doc)
    data["id"] = str(data.pop("_id"))
    return Topic.model_validate(data)  # Spring's `_class` field is ignored


def _to_doc(topic: Topic) -> dict:
    return topic.model_dump(by_alias=True, exclude_none=True, exclude={"id"})


class TopicsRepository:
    def __init__(self, collection: AsyncCollection) -> None:
        self.collection = collection

    async def find_by_user_newest_first(self, user_id: str) -> list[Topic]:
        cursor = self.collection.find({"userId": user_id}).sort([("createdAt", -1), ("_id", -1)])
        return [_from_doc(doc) async for doc in cursor]

    async def find_by_public_id_and_user(self, public_id: str, user_id: str) -> Topic | None:
        return _from_doc(await self.collection.find_one({"publicId": public_id, "userId": user_id}))

    async def find_by_id_and_user(self, topic_id: str, user_id: str) -> Topic | None:
        if not ObjectId.is_valid(topic_id):
            return None
        return _from_doc(await self.collection.find_one({"_id": ObjectId(topic_id), "userId": user_id}))

    async def exists_by_user_and_name_ignore_case(self, user_id: str, name: str) -> bool:
        query = {"userId": user_id, "name": {"$regex": f"^{re.escape(name)}$", "$options": "i"}}
        return await self.collection.find_one(query, projection={"_id": 1}) is not None

    async def insert(self, topic: Topic) -> Topic:
        topic.created_at = utc_now()
        result = await self.collection.insert_one(_to_doc(topic))
        topic.id = str(result.inserted_id)
        return topic

    async def delete_by_id_and_user(self, topic_id: str, user_id: str) -> None:
        if ObjectId.is_valid(topic_id):
            await self.collection.delete_one({"_id": ObjectId(topic_id), "userId": user_id})

    async def record_test_score(self, topic_id: str, raw_score: int) -> Topic | None:
        """Bump testCount and fold the score into the running average in one atomic update (deviation D5).

        Java read the topic, changed it in memory and saved it back, so two concurrent submits could lose one.
        The score is a float literal so avgScore is always stored as a BSON double.
        """
        score = float(raw_score)
        pipeline = [
            {"$set": {"testCount": {"$add": [{"$ifNull": ["$testCount", 0]}, 1]}}},
            {
                "$set": {
                    "avgScore": {
                        "$cond": [
                            {"$eq": [{"$ifNull": ["$avgScore", None]}, None]},
                            score,
                            {
                                "$divide": [
                                    {"$add": [{"$multiply": ["$avgScore", {"$subtract": ["$testCount", 1]}]}, score]},
                                    "$testCount",
                                ]
                            },
                        ]
                    }
                }
            },
        ]
        doc = await self.collection.find_one_and_update(
            {"_id": ObjectId(topic_id)}, pipeline, return_document=ReturnDocument.AFTER
        )
        return _from_doc(doc)
