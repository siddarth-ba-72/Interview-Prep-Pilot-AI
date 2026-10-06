from email_validator import EmailNotValidError, validate_email

from app.errors import ApiError
from app.schemas.base import CamelModel

MIN_PASSWORD_LENGTH = 8


def _blank(value: str | None) -> bool:
    """Jakarta @NotBlank: missing, null, empty or whitespace-only."""
    return value is None or value.strip() == ""


def _invalid(message: str) -> ApiError:
    return ApiError(400, "USER_INVALID_INPUT", message)


def _check_email(email: str | None) -> None:
    if _blank(email):
        raise _invalid("Email is required")
    try:
        validate_email(email, check_deliverability=False)
    except EmailNotValidError:
        raise _invalid("Invalid email format") from None


class RegisterRequest(CamelModel):
    email: str | None = None
    password: str | None = None
    display_name: str | None = None

    def ensure_valid(self) -> None:
        """Explicit checks in field order so the first failure wins and the messages match the Java ones."""
        _check_email(self.email)
        if _blank(self.password):
            raise _invalid("Password is required")
        if len(self.password) < MIN_PASSWORD_LENGTH:
            raise _invalid("Password must be at least 8 characters")
        if _blank(self.display_name):
            raise _invalid("Display name is required")


class LoginRequest(CamelModel):
    email: str | None = None
    password: str | None = None

    def ensure_valid(self) -> None:
        _check_email(self.email)
        if _blank(self.password):
            raise _invalid("Password is required")


class UserProfile(CamelModel):
    id: str
    email: str
    display_name: str


class AuthResponse(CamelModel):
    access_token: str
    user: UserProfile
