import hashlib
from datetime import timedelta

import pytest

from app.errors import ApiError
from app.models.refresh_token import RefreshToken
from app.models.user import AuthProvider, User
from app.repositories.users import _to_doc
from app.schemas.auth import LoginRequest, RegisterRequest
from app.services.auth_service import AuthService, hash_token
from app.services.jwt_service import JwtService
from app.services.passwords import hash_password_sync
from app.timeutil import utc_now
from tests.unit.fakes import FakeRefreshTokens, FakeUsers

SECRET = "unit-test-secret-that-is-long-enough-123"


@pytest.fixture
def users():
    return FakeUsers()


@pytest.fixture
def tokens():
    return FakeRefreshTokens()


@pytest.fixture
def service(users, tokens):
    return AuthService(users, tokens, JwtService(SECRET, 1800), 30)


def reg(email="ann@example.com", password="password1", name="Ann"):
    return RegisterRequest(email=email, password=password, display_name=name)


async def test_register_hashes_password_and_returns_profile(service, users):
    profile = await service.register(reg())
    assert profile.email == "ann@example.com" and profile.display_name == "Ann"
    stored = users.items[profile.id]
    assert stored.auth_provider == AuthProvider.LOCAL
    assert stored.password_hash.startswith("$2b$12$") and "password1" not in stored.password_hash
    assert stored.google_id is None


async def test_register_duplicate_email_conflicts(service):
    await service.register(reg())
    with pytest.raises(ApiError) as exc:
        await service.register(reg())
    assert (exc.value.status_code, exc.value.code) == (409, "EMAIL_ALREADY_REGISTERED")
    assert exc.value.message == "Email already registered"


async def test_email_is_matched_exactly_not_case_folded(service):
    await service.register(reg(email="Ann@Example.com"))
    await service.register(reg(email="ann@example.com"))  # a different record, as in Java


async def test_login_returns_tokens_and_stores_hashed_refresh_token(service, tokens):
    await service.register(reg())
    pair = await service.login(LoginRequest(email="ann@example.com", password="password1"))
    assert pair.auth_response.access_token.count(".") == 2
    assert pair.auth_response.user.email == "ann@example.com"
    (stored,) = tokens.items.values()
    assert stored.token_hash == hashlib.sha256(pair.raw_refresh_token.encode()).hexdigest()
    assert stored.token_hash != pair.raw_refresh_token
    assert timedelta(days=29, hours=23) < stored.expires_at - utc_now() <= timedelta(days=30)


@pytest.mark.parametrize(
    "email, password", [("ann@example.com", "wrong-password"), ("nobody@example.com", "password1")]
)
async def test_login_failures_are_indistinguishable(service, email, password):
    await service.register(reg())
    with pytest.raises(ApiError) as exc:
        await service.login(LoginRequest(email=email, password=password))
    error = exc.value
    assert (error.status_code, error.code, error.message) == (401, "INVALID_CREDENTIALS", "Invalid credentials")


async def test_google_only_user_cannot_log_in_with_a_password(service):
    await service.find_or_create_google_user("g-1", "goog@example.com", "Goog")
    with pytest.raises(ApiError) as exc:
        await service.login(LoginRequest(email="goog@example.com", password="anything1"))
    assert exc.value.status_code == 401


async def test_refresh_rotates_the_token(service, tokens):
    await service.register(reg())
    first = await service.login(LoginRequest(email="ann@example.com", password="password1"))
    second = await service.refresh(first.raw_refresh_token)
    assert second.raw_refresh_token != first.raw_refresh_token
    assert len(tokens.items) == 1  # the old one is gone
    with pytest.raises(ApiError) as exc:
        await service.refresh(first.raw_refresh_token)
    assert exc.value.status_code == 401
    await service.refresh(second.raw_refresh_token)


async def test_unknown_refresh_token_is_401(service):
    with pytest.raises(ApiError) as exc:
        await service.refresh("00000000-0000-0000-0000-000000000000")
    assert exc.value.status_code == 401


async def test_expired_refresh_token_is_deleted_and_401(service, tokens):
    await service.register(reg())
    pair = await service.login(LoginRequest(email="ann@example.com", password="password1"))
    (stored,) = tokens.items.values()
    stored.expires_at = utc_now() - timedelta(seconds=1)
    with pytest.raises(ApiError) as exc:
        await service.refresh(pair.raw_refresh_token)
    assert exc.value.status_code == 401
    assert tokens.items == {}


async def test_refresh_for_a_deleted_user_is_401(service, users):
    profile = await service.register(reg())
    pair = await service.login(LoginRequest(email="ann@example.com", password="password1"))
    del users.items[profile.id]
    with pytest.raises(ApiError) as exc:
        await service.refresh(pair.raw_refresh_token)
    assert exc.value.status_code == 401


async def test_logout_deletes_the_token_and_ignores_unknown_ones(service, tokens):
    await service.register(reg())
    pair = await service.login(LoginRequest(email="ann@example.com", password="password1"))
    await service.logout("not-a-real-token")
    assert len(tokens.items) == 1
    await service.logout(pair.raw_refresh_token)
    assert tokens.items == {}


async def test_google_branch_existing_google_id(service, users):
    existing = await users.insert(
        User(email="g@example.com", auth_provider=AuthProvider.GOOGLE, google_id="g-1", display_name="G")
    )
    found = await service.find_or_create_google_user("g-1", "different@example.com", "Other")
    assert found.id == existing.id
    assert len(users.items) == 1


async def test_google_branch_links_existing_email_account(service, users):
    profile = await service.register(reg(email="ann@example.com"))
    linked = await service.find_or_create_google_user("g-9", "ann@example.com", "Ann G")
    assert linked.id == profile.id
    assert linked.google_id == "g-9"
    assert linked.password_hash is not None  # still able to log in with the password
    assert len(users.items) == 1


async def test_google_branch_creates_a_new_user_without_password(service, users):
    created = await service.find_or_create_google_user("g-2", "new@example.com", "New Person")
    assert created.auth_provider == AuthProvider.GOOGLE
    assert created.google_id == "g-2" and created.password_hash is None
    assert created.display_name == "New Person"
    assert len(users.items) == 1


def test_local_user_document_has_no_google_id_key_at_all():
    doc = _to_doc(User(email="a@example.com", password_hash=hash_password_sync("password1"), display_name="A"))
    assert "googleId" not in doc  # an explicit null would collide on the sparse unique index
    assert doc["authProvider"] == "LOCAL"
    assert "id" not in doc and "_id" not in doc
    assert not any(v is None for v in doc.values())


def test_google_user_document_has_no_password_hash_key():
    doc = _to_doc(User(email="a@example.com", auth_provider=AuthProvider.GOOGLE, google_id="g", display_name="A"))
    assert "passwordHash" not in doc
    assert doc["googleId"] == "g"


def test_hash_token_is_lowercase_hex_sha256():
    assert hash_token("abc") == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"


def test_refresh_token_document_shape():
    token = RefreshToken(user_id="u1", token_hash="h", expires_at=utc_now())
    doc = token.model_dump(by_alias=True, exclude_none=True, exclude={"id"})
    assert set(doc) == {"userId", "tokenHash", "expiresAt"}
