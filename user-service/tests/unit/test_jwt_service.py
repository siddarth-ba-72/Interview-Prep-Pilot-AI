import jwt
import pytest

from app.services.jwt_service import JwtService

SECRET = "unit-test-secret-that-is-long-enough-123"


def test_claims_are_exactly_the_java_ones():
    token = JwtService(SECRET, 1800).generate_access_token("64f0c0ffee0123456789abcd", "a@b.com")
    claims = jwt.decode(token, SECRET.encode(), algorithms=["HS256"])
    assert set(claims) == {"userId", "email", "iat", "exp"}  # no `sub`
    assert claims["userId"] == "64f0c0ffee0123456789abcd"
    assert claims["email"] == "a@b.com"
    assert claims["exp"] - claims["iat"] == 1800


def test_header_is_hs256():
    token = JwtService(SECRET, 60).generate_access_token("u", "e@x.com")
    assert jwt.get_unverified_header(token)["alg"] == "HS256"


def test_wrong_secret_does_not_verify():
    token = JwtService(SECRET, 60).generate_access_token("u", "e@x.com")
    with pytest.raises(jwt.InvalidSignatureError):
        jwt.decode(token, b"another-secret-that-is-long-enough!!", algorithms=["HS256"])


def test_expiry_is_configurable():
    claims = jwt.decode(
        JwtService(SECRET, 60).generate_access_token("u", "e@x.com"), SECRET.encode(), algorithms=["HS256"]
    )
    assert claims["exp"] - claims["iat"] == 60


@pytest.mark.parametrize("secret", ["", "short", "x" * 31])
def test_short_secret_is_refused(secret):
    with pytest.raises(ValueError, match="at least 32 bytes"):
        JwtService(secret, 1800)


def test_32_byte_secret_is_accepted():
    JwtService("x" * 32, 1800)
