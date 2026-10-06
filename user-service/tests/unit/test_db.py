from pymongo.errors import OperationFailure

from app.db import ensure_index


class FakeCollection:
    name = "things"

    def __init__(self, existing=None, fail=False):
        self.existing = existing or {}
        self.fail = fail
        self.created = []

    async def index_information(self):
        return self.existing

    async def create_index(self, keys, name, **options):
        if self.fail:
            raise OperationFailure("duplicate key")
        self.created.append((keys, name, options))


async def test_creates_missing_index_with_options():
    coll = FakeCollection({"_id_": {"key": [("_id", 1)]}})
    await ensure_index(coll, "email", "email", unique=True)
    assert coll.created == [([("email", 1)], "email", {"unique": True})]


async def test_skips_index_that_exists_under_another_name():
    coll = FakeCollection({"_id_": {"key": [("_id", 1)]}, "email_1": {"key": [("email", 1)]}})
    await ensure_index(coll, "email", "email", unique=True)
    assert coll.created == []


async def test_compound_keys_must_match_exactly():
    coll = FakeCollection({"a_1": {"key": [("userId", 1)]}})
    await ensure_index(coll, [("userId", 1), ("name", 1)], "user_name_unique", unique=True)
    assert len(coll.created) == 1


async def test_failure_is_logged_not_raised():
    await ensure_index(FakeCollection(fail=True), "email", "email", unique=True)
