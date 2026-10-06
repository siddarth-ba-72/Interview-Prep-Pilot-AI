import jwt

from app.errors import ApiError

ALGORITHMS = ["HS256", "HS384", "HS512"]  # JJWT picks the HMAC strength from the secret's length


def unauthorized() -> ApiError:
    return ApiError(401, "USER_UNAUTHORIZED", "Unauthorized")


def verify_token(token: str, secret: str) -> tuple[str, str]:
    """Return (user_id, email) from a valid access token. Any problem raises the 401 ApiError."""
    try:
        claims = jwt.decode(
            token,
            secret.encode("utf-8"),
            algorithms=ALGORITHMS,
            leeway=0,
            # Mirror JJWT: check the signature and exp (and nbf if present), nothing else.
            options={"verify_iat": False, "verify_aud": False, "verify_sub": False, "verify_jti": False},
        )
    except jwt.PyJWTError:
        raise unauthorized() from None

    user_id = claims.get("userId")
    if not isinstance(user_id, str) or not user_id:
        raise unauthorized()
    email = claims.get("email", "")
    if email is None:
        email = ""
    if not isinstance(email, str):
        raise unauthorized()
    return user_id, email


def authenticate(authorization: str | None, secret: str) -> tuple[str, str]:
    if not authorization or not authorization.startswith("Bearer "):
        raise unauthorized()
    return verify_token(authorization[len("Bearer "):].strip(), secret)
