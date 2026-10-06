import time

import jwt

MIN_SECRET_BYTES = 32


class JwtService:
    def __init__(self, secret: str, access_token_expiry_seconds: int) -> None:
        key = secret.encode("utf-8")
        # Same rule as JJWT's Keys.hmacShaKeyFor: refuse a short HMAC secret.
        if len(key) < MIN_SECRET_BYTES:
            raise ValueError("JWT_SECRET must be at least 32 bytes")
        self._key = key
        self._expiry = access_token_expiry_seconds

    def generate_access_token(self, user_id: str, email: str) -> str:
        # Exactly the Java claims: no `sub`. The gateway reads userId and email.
        issued_at = int(time.time())
        claims = {"userId": user_id, "email": email, "iat": issued_at, "exp": issued_at + self._expiry}
        return jwt.encode(claims, self._key, algorithm="HS256")
