from tests.integration.conftest import login, new_email, register


def test_me_returns_the_profile(client):
    email, reg = register(client)
    resp = client.get("/api/v1/users/me", headers={"X-User-Id": reg.json()["id"]})
    assert resp.status_code == 200
    assert resp.json() == {"id": reg.json()["id"], "email": email, "displayName": "Integration User"}


def test_me_without_the_header_is_401(client):
    resp = client.get("/api/v1/users/me")
    assert resp.status_code == 401
    assert resp.json() == {"error": {"code": "USER_UNAUTHORIZED", "message": "Missing required header"}}


def test_me_for_unknown_user_is_404(client):
    resp = client.get("/api/v1/users/me", headers={"X-User-Id": "0" * 24})
    assert resp.status_code == 404
    assert resp.json() == {"error": {"code": "USER_NOT_FOUND", "message": "User not found"}}


def test_me_with_a_malformed_id_is_404_not_500(client):
    assert client.get("/api/v1/users/me", headers={"X-User-Id": "not-an-object-id"}).status_code == 404


def test_the_access_token_carries_the_id_the_gateway_will_forward(client):
    import jwt

    from tests.integration.conftest import TEST_SECRET

    email, reg = register(client)
    token = login(client, email).json()["accessToken"]
    claims = jwt.decode(token, TEST_SECRET.encode(), algorithms=["HS256"])
    assert claims["userId"] == reg.json()["id"] and claims["email"] == email
    assert client.get("/api/v1/users/me", headers={"X-User-Id": claims["userId"]}).status_code == 200
    assert new_email() != email
