from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.errors import ApiError, register_exception_handlers
from app.logging_config import RequestIdMiddleware


def make_client() -> TestClient:
    app = FastAPI(redirect_slashes=False)
    register_exception_handlers(app)
    app.add_middleware(RequestIdMiddleware)

    @app.get("/boom")
    async def boom():
        raise ApiError(409, "DUPLICATE_THING", "Thing already exists")

    @app.get("/crash")
    async def crash():
        raise RuntimeError("secret detail")

    @app.get("/typed/{n}")
    async def typed(n: int):
        return {"n": n}

    return TestClient(app, raise_server_exceptions=False)


def test_api_error_uses_envelope():
    resp = make_client().get("/boom")
    assert resp.status_code == 409
    assert resp.json() == {"error": {"code": "DUPLICATE_THING", "message": "Thing already exists"}}


def test_unhandled_error_hides_detail():
    resp = make_client().get("/crash")
    assert resp.status_code == 500
    assert resp.json() == {"error": {"code": "SYSTEM_INTERNAL_ERROR", "message": "Internal server error"}}


def test_validation_error_is_400():
    resp = make_client().get("/typed/abc")
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "USER_INVALID_INPUT"


def test_unknown_path_is_404_envelope():
    resp = make_client().get("/nope")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "NOT_FOUND"


def test_request_id_is_generated_and_echoed():
    client = make_client()
    assert len(client.get("/boom").headers["x-request-id"]) == 36
    assert client.get("/boom", headers={"X-Request-Id": "abc-123"}).headers["x-request-id"] == "abc-123"
