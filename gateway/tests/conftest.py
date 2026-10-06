import time

import jwt
import pytest
import respx
from fastapi.testclient import TestClient

from app.config import settings
from app.main import create_app

SECRET = "gateway-test-secret-" + "0123456789abcdef" * 5  # 100 bytes: long enough for HS512 too
ORIGIN = "http://localhost:3000"
USER_URL = "http://user.test"
TOPIC_URL = "http://topic.test"


def make_token(secret: str = SECRET, algorithm: str = "HS256", **overrides) -> str:
    """An access token shaped like the user-service's: userId, email, iat, exp (no sub)."""
    now = int(time.time())
    claims = {"userId": "64f0c0ffee0123456789abcd", "email": "ann@example.com", "iat": now, "exp": now + 1800}
    claims.update(overrides)
    claims = {k: v for k, v in claims.items() if v is not ...}  # `...` removes a claim
    return jwt.encode(claims, secret.encode(), algorithm=algorithm)


def bearer(token: str | None = None) -> dict:
    return {"Authorization": f"Bearer {token or make_token()}"}


@pytest.fixture(autouse=True)
def gateway_settings(monkeypatch):
    monkeypatch.setattr(settings, "jwt_secret", SECRET)
    monkeypatch.setattr(settings, "frontend_origin", ORIGIN)
    monkeypatch.setattr(settings, "user_service_url", USER_URL)
    monkeypatch.setattr(settings, "topic_service_url", TOPIC_URL)


@pytest.fixture
def upstream():
    """respx router that stands in for both upstream services."""
    with respx.mock(assert_all_called=False) as router:
        yield router


@pytest.fixture
def client(upstream):
    with TestClient(create_app(), follow_redirects=False) as test_client:
        yield test_client
