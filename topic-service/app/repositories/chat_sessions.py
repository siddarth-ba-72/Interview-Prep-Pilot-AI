from bson import ObjectId
from pymongo.asynchronous.collection import AsyncCollection

from app.models.chat_session import ChatSession, Message
from app.timeutil import utc_now


def _from_doc(doc: dict | None) -> ChatSession | None:
    if doc is None:
        return None
    data = dict(doc)
    data["id"] = str(data.pop("_id"))
    return ChatSession.model_validate(data)


class ChatSessionsRepository:
    def __init__(self, collection: AsyncCollection) -> None:
        self.collection = collection

    async def find_by_user_and_topic(self, user_id: str, topic_id: str) -> ChatSession | None:
        return _from_doc(await self.collection.find_one({"userId": user_id, "topicId": topic_id}))

    async def insert(self, session: ChatSession) -> ChatSession:
        now = utc_now()
        session.created_at = now
        session.updated_at = now
        doc = session.model_dump(by_alias=True, exclude_none=True, exclude={"id"})
        result = await self.collection.insert_one(doc)
        session.id = str(result.inserted_id)
        return session

    async def push_message(self, session_id: str, message: Message) -> None:
        """Atomic append (deviation D5): concurrent writers can no longer overwrite each other's messages."""
        await self.collection.update_one(
            {"_id": ObjectId(session_id)},
            {"$push": {"messages": message.model_dump(by_alias=True)}, "$set": {"updatedAt": utc_now()}},
        )

    async def delete_by_user_and_topic(self, user_id: str, topic_id: str) -> None:
        await self.collection.delete_one({"userId": user_id, "topicId": topic_id})
