"""In-memory stand-ins for the Mongo repositories, with the same async interface."""
from app.models.refresh_token import RefreshToken
from app.models.user import User


class FakeUsers:
    def __init__(self) -> None:
        self.items: dict[str, User] = {}

    def _next_id(self) -> str:
        return f"{len(self.items) + 1:024x}"

    async def find_by_id(self, user_id: str) -> User | None:
        return self.items.get(user_id)

    async def find_by_email(self, email: str) -> User | None:
        return next((u for u in self.items.values() if u.email == email), None)

    async def find_by_google_id(self, google_id: str) -> User | None:
        return next((u for u in self.items.values() if u.google_id == google_id), None)

    async def exists_by_email(self, email: str) -> bool:
        return await self.find_by_email(email) is not None

    async def insert(self, user: User) -> User:
        user.id = self._next_id()
        self.items[user.id] = user
        return user

    async def save(self, user: User) -> User:
        if user.id is None:
            return await self.insert(user)
        self.items[user.id] = user
        return user


class FakeRefreshTokens:
    def __init__(self) -> None:
        self.items: dict[str, RefreshToken] = {}

    async def find_by_hash(self, token_hash: str) -> RefreshToken | None:
        return next((t for t in self.items.values() if t.token_hash == token_hash), None)

    async def insert(self, token: RefreshToken) -> RefreshToken:
        token.id = f"{len(self.items) + 1:024x}"
        self.items[token.id] = token
        return token

    async def delete(self, token: RefreshToken) -> None:
        self.items.pop(token.id, None)
