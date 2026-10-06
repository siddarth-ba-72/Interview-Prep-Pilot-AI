import time

import jwt
import pytest

from app.auth import authenticate, verify_token
from app.errors import ApiError
from tests.conftest import SECRET, make_token


def assert_401(fn, *args):
    with pytest.raises(ApiError) as exc:
        fn(*args)
    assert exc.value.status_code == 401
    assert (exc.value.code, exc.value.message) == ("USER_UNAUTHORIZED", "Unauthorized")


@pytest.mark.parametrize("algorithm", ["HS256", "HS384", "HS512"])
def test_all_hmac_strengths_are_accepted(algorithm):
    token = make_token(algorithm=algorithm)
    assert verify_token(token, SECRET) == ("64f0c0ffee0123456789abcd", "ann@example.com")


def test_missing_email_defaults_to_empty_string():
    assert verify_token(make_token(email=...), SECRET) == ("64f0c0ffee0123456789abcd", "")


def test_null_email_defaults_to_empty_string():
    assert verify_token(make_token(email=None), SECRET)[1] == ""


def test_non_string_email_is_rejected():
    assert_401(verify_token, make_token(email=42), SECRET)


@pytest.mark.parametrize("user_id", [..., None, "", 123, ["x"]])
def test_user_id_must_be_a_non_empty_string(user_id):
    assert_401(verify_token, make_token(userId=user_id), SECRET)


def test_expired_token_is_rejected_with_no_leeway():
    assert_401(verify_token, make_token(exp=int(time.time()) - 1), SECRET)


def test_token_without_exp_is_accepted_like_jjwt():
    assert verify_token(make_token(exp=...), SECRET)[0]


def test_future_iat_is_not_checked_like_jjwt():
    assert verify_token(make_token(iat=int(time.time()) + 3600), SECRET)[0]


def test_extra_claims_such_as_aud_are_ignored():
    assert verify_token(make_token(aud="someone", sub="x"), SECRET)[0]


def test_wrong_secret_is_rejected():
    assert_401(verify_token, make_token(secret="a-completely-different-secret-of-32-bytes!!"), SECRET)


def test_tampered_payload_is_rejected():
    head, _, sig = make_token().split(".")
    forged = jwt.utils.base64url_encode(b'{"userId":"someone-else","email":"x@example.com"}').decode()
    assert_401(verify_token, f"{head}.{forged}.{sig}", SECRET)


def test_alg_none_is_rejected():
    unsigned = jwt.encode({"userId": "u", "email": "e", "exp": int(time.time()) + 60}, key=None, algorithm="none")
    assert_401(verify_token, unsigned, SECRET)


@pytest.mark.parametrize("token", ["", "not-a-jwt", "a.b.c", "....."])
def test_garbage_is_rejected(token):
    assert_401(verify_token, token, SECRET)


@pytest.mark.parametrize("header", [None, "", "Bearer", "Token abc", "bearer abc", "Basic abc"])
def test_authorization_header_must_be_bearer(header):
    assert_401(authenticate, header, SECRET)


def test_bearer_token_is_trimmed():
    assert authenticate(f"Bearer   {make_token()}  ", SECRET)[0]
