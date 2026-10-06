from bson import ObjectId
from pymongo.asynchronous.collection import AsyncCollection

from app.models.refresh_token import RefreshToken
from app.timeutil import utc_now


def _from_doc(doc: dict | None) -> RefreshToken | None:
    if doc is None:
        return None
    data = dict(doc)
    data["id"] = str(data.pop("_id"))
    return RefreshToken.model_validate(data)


class RefreshTokensRepository:
    def __init__(self, collection: AsyncCollection) -> None:
        self.collection = collection

    async def find_by_hash(self, token_hash: str) -> RefreshToken | None:
        return _from_doc(await self.collection.find_one({"tokenHash": token_hash}))

    async def insert(self, token: RefreshToken) -> RefreshToken:
        token.created_at = utc_now()
        doc = token.model_dump(by_alias=True, exclude_none=True, exclude={"id"})
        result = await self.collection.insert_one(doc)
        token.id = str(result.inserted_id)
        return token

    async def delete(self, token: RefreshToken) -> None:
        await self.collection.delete_one({"_id": ObjectId(token.id)})
