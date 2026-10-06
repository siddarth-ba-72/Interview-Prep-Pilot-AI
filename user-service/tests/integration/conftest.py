import os
import uuid

import pymongo
import pytest
from fastapi.testclient import TestClient
from pymongo.errors import PyMongoError

from app.config import settings
from app.main import app

TEST_MONGODB_URI = os.environ.get("TEST_MONGODB_URI", "mongodb://root:change_me@localhost:27017/?authSource=admin")
TEST_SECRET = "integration-test-secret-0123456789abcdef"
PASSWORD = "Integration-Pass-1"


@pytest.fixture(scope="session")
def mongo_uri():
    probe = pymongo.MongoClient(TEST_MONGODB_URI, serverSelectionTimeoutMS=2000)
    try:
        probe.admin.command("ping")
    except PyMongoError:
        pytest.skip(
            "MongoDB not reachable. Start one with `docker compose -f docker-compose.python.yml up -d mongodb` "
            "or point TEST_MONGODB_URI at it."
        )
    finally:
        probe.close()
    return TEST_MONGODB_URI


@pytest.fixture(scope="module")
def db_name():
    return f"users_db_test_{uuid.uuid4().hex[:8]}"


@pytest.fixture(scope="module")
def raw_db(mongo_uri, db_name):
    """A plain synchronous handle on the test database, for arranging and inspecting data."""
    client = pymongo.MongoClient(mongo_uri, tz_aware=True)
    yield client[db_name]
    client.drop_database(db_name)
    client.close()


@pytest.fixture(scope="module")
def client(mongo_uri, db_name, raw_db):
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(settings, "mongodb_uri", mongo_uri)
        mp.setattr(settings, "mongodb_db", db_name)
        mp.setattr(settings, "jwt_secret", TEST_SECRET)
        mp.setattr(settings, "cookie_secure", True)
        mp.setattr(settings, "frontend_origin", "http://localhost:3000")
        mp.setattr(settings, "google_client_id", "test-client-id")
        mp.setattr(settings, "google_client_secret", "test-client-secret")
        with TestClient(app) as test_client:
            yield test_client


def new_email() -> str:
    return f"it+{uuid.uuid4().hex[:10]}@example.com"


def register(client, email=None, password=PASSWORD, display_name="Integration User"):
    email = email or new_email()
    response = client.post(
        "/api/v1/auth/register", json={"email": email, "password": password, "displayName": display_name}
    )
    return email, response


def login(client, email, password=PASSWORD):
    return client.post("/api/v1/auth/login", json={"email": email, "password": password})


def refresh_cookie(response):
    """(value, raw Set-Cookie) of refresh_token. httpx won't resend Secure cookies over http, so tests
    read the header and send `Cookie:` by hand."""
    for raw in response.headers.get_list("set-cookie"):
        if raw.startswith("refresh_token="):
            return raw.split(";", 1)[0].split("=", 1)[1], raw
    return None, None
