import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import create_app


def test_health_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_health_needs_no_token_and_is_not_proxied(client, upstream):
    route = upstream.route().respond(500)
    assert client.get("/health").status_code == 200
    assert not route.called


def test_refuses_to_start_with_short_secret(monkeypatch):
    monkeypatch.setattr(settings, "jwt_secret", "too-short")
    with pytest.raises(RuntimeError, match="at least 32 bytes"), TestClient(create_app()):
        pass


def test_docs_are_disabled(client):
    assert client.get("/docs").status_code == 404
    assert client.get("/redoc").status_code == 404
    assert client.get("/openapi.json").status_code == 404
