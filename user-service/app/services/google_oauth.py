from dataclasses import dataclass
from urllib.parse import quote, urlencode

import httpx

AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


class GoogleOAuthError(Exception):
    pass


@dataclass(frozen=True)
class GoogleUser:
    sub: str
    email: str
    name: str | None


class GoogleOAuthClient:
    """Hand-rolled authorization-code flow, replacing Spring Security's oauth2Login."""

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str, http: httpx.AsyncClient) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.http = http

    def authorize_url(self, state: str) -> str:
        query = urlencode(
            {
                "response_type": "code",
                "client_id": self.client_id,
                "redirect_uri": self.redirect_uri,
                "scope": "email profile",
                "state": state,
            },
            quote_via=quote,
        )
        return f"{AUTHORIZE_URL}?{query}"

    async def fetch_user(self, code: str) -> GoogleUser:
        try:
            token_response = await self.http.post(
                TOKEN_URL,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": self.redirect_uri,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
            )
            token_response.raise_for_status()
            access_token = token_response.json()["access_token"]
            info_response = await self.http.get(USERINFO_URL, headers={"Authorization": f"Bearer {access_token}"})
            info_response.raise_for_status()
            info = info_response.json()
            sub, email = info["sub"], info["email"]
        except (httpx.HTTPError, KeyError, ValueError, TypeError) as exc:
            raise GoogleOAuthError(f"Google sign-in failed: {type(exc).__name__}") from exc
        if not sub or not email:
            raise GoogleOAuthError("Google did not return a subject and email")
        return GoogleUser(sub=sub, email=email, name=info.get("name"))
