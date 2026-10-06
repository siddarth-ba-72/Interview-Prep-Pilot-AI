from fastapi.testclient import TestClient

from app.config import settings
from app.main import app


def test_health_ok_with_valid_secret(monkeypatch):
    monkeypatch.setattr(settings, "jwt_secret", "x" * 32)
    with TestClient(app) as client:
        resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_refuses_to_start_with_short_secret(monkeypatch):
    import pytest

    monkeypatch.setattr(settings, "jwt_secret", "too-short")
    with pytest.raises(RuntimeError, match="at least 32 bytes"):
        with TestClient(app):
            pass


def test_docs_are_disabled(monkeypatch):
    monkeypatch.setattr(settings, "jwt_secret", "x" * 32)
    with TestClient(app) as client:
        assert client.get("/docs").status_code == 404
        assert client.get("/openapi.json").status_code == 404
