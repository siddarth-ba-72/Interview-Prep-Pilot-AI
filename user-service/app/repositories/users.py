from bson import ObjectId
from pymongo.asynchronous.collection import AsyncCollection

from app.models.user import User
from app.timeutil import utc_now


def _from_doc(doc: dict | None) -> User | None:
    if doc is None:
        return None
    data = dict(doc)
    data["id"] = str(data.pop("_id"))
    return User.model_validate(data)  # Spring's `_class` field is ignored


def _to_doc(user: User) -> dict:
    # exclude_none: never write null fields. users.googleId has a sparse unique index, and a sparse
    # index still indexes an explicit null, so a second local user would collide.
    return user.model_dump(by_alias=True, exclude_none=True, exclude={"id"})


class UsersRepository:
    def __init__(self, collection: AsyncCollection) -> None:
        self.collection = collection

    async def find_by_id(self, user_id: str) -> User | None:
        if not ObjectId.is_valid(user_id):
            return None
        return _from_doc(await self.collection.find_one({"_id": ObjectId(user_id)}))

    async def find_by_email(self, email: str) -> User | None:
        return _from_doc(await self.collection.find_one({"email": email}))

    async def find_by_google_id(self, google_id: str) -> User | None:
        return _from_doc(await self.collection.find_one({"googleId": google_id}))

    async def exists_by_email(self, email: str) -> bool:
        return await self.collection.find_one({"email": email}, projection={"_id": 1}) is not None

    async def insert(self, user: User) -> User:
        now = utc_now()
        user.created_at = now
        user.updated_at = now
        result = await self.collection.insert_one(_to_doc(user))
        user.id = str(result.inserted_id)
        return user

    async def save(self, user: User) -> User:
        if user.id is None:
            return await self.insert(user)
        user.updated_at = utc_now()
        await self.collection.replace_one({"_id": ObjectId(user.id)}, _to_doc(user), upsert=True)
        return user
