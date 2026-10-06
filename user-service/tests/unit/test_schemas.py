import pytest

from app.errors import ApiError
from app.schemas.auth import LoginRequest, RegisterRequest


def register(**overrides):
    base = {"email": "a@example.com", "password": "password1", "displayName": "Ann"}
    return RegisterRequest.model_validate({**base, **overrides})


def message_of(request) -> str:
    with pytest.raises(ApiError) as exc:
        request.ensure_valid()
    assert exc.value.status_code == 400
    assert exc.value.code == "USER_INVALID_INPUT"
    return exc.value.message


def test_valid_register_passes():
    register().ensure_valid()


@pytest.mark.parametrize(
    "overrides, expected",
    [
        ({"email": None}, "Email is required"),
        ({"email": ""}, "Email is required"),
        ({"email": "   "}, "Email is required"),
        ({"email": "not-an-email"}, "Invalid email format"),
        ({"email": "a@"}, "Invalid email format"),
        ({"password": None}, "Password is required"),
        ({"password": "        "}, "Password is required"),
        ({"password": "short"}, "Password must be at least 8 characters"),
        ({"displayName": None}, "Display name is required"),
        ({"displayName": "  "}, "Display name is required"),
    ],
)
def test_register_messages(overrides, expected):
    assert message_of(register(**overrides)) == expected


def test_register_reports_first_failure_in_field_order():
    assert message_of(register(email="", password="", displayName="")) == "Email is required"
    assert message_of(register(email="bad", password="", displayName="")) == "Invalid email format"
    assert message_of(register(password="", displayName="")) == "Password is required"
    assert message_of(register(password="short", displayName="")) == "Password must be at least 8 characters"
    assert message_of(register(displayName="")) == "Display name is required"


def test_password_of_exactly_eight_characters_is_valid():
    register(password="12345678").ensure_valid()


def test_email_is_not_normalised():
    request = register(email="Mixed.Case@Example.com")
    request.ensure_valid()
    assert request.email == "Mixed.Case@Example.com"


def test_plus_addressing_and_example_domain_are_valid():
    register(email="contract+abc123@example.com").ensure_valid()


@pytest.mark.parametrize(
    "payload, expected",
    [
        ({"password": "x"}, "Email is required"),
        ({"email": "nope", "password": "x"}, "Invalid email format"),
        ({"email": "a@example.com"}, "Password is required"),
        ({"email": "a@example.com", "password": ""}, "Password is required"),
    ],
)
def test_login_messages(payload, expected):
    assert message_of(LoginRequest.model_validate(payload)) == expected


def test_login_does_not_enforce_password_length():
    LoginRequest.model_validate({"email": "a@example.com", "password": "x"}).ensure_valid()
