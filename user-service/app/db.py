import logging

from pymongo import ASCENDING, AsyncMongoClient
from pymongo.asynchronous.collection import AsyncCollection
from pymongo.errors import PyMongoError

from app.config import settings

logger = logging.getLogger(__name__)

IndexKeys = str | list[tuple[str, int]]


def create_client() -> AsyncMongoClient:
    # tz_aware so datetimes read back as UTC-aware, matching what the services write.
    return AsyncMongoClient(settings.mongodb_uri, tz_aware=True)


def _normalise(keys: IndexKeys) -> list[tuple[str, int]]:
    return [(keys, ASCENDING)] if isinstance(keys, str) else list(keys)


async def ensure_index(collection: AsyncCollection, keys: IndexKeys, name: str, **options) -> None:
    """Create an index unless one with the same key pattern already exists under any name.

    The Spring services may have created it under a different name. A failure (for example existing data
    that violates a unique index) is logged and swallowed so the service still starts.
    """
    wanted = _normalise(keys)
    try:
        existing = await collection.index_information()
        if any(list(info["key"]) == wanted for info in existing.values()):
            return
        await collection.create_index(wanted, name=name, **options)
    except PyMongoError:
        logger.error("Could not ensure index", exc_info=True, extra={"collection": collection.name, "index": name})
