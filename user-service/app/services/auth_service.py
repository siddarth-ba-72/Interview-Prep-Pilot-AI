import hashlib
import uuid
from dataclasses import dataclass
from datetime import timedelta

from pymongo.errors import DuplicateKeyError

from app.errors import ApiError
from app.models.refresh_token import RefreshToken
from app.models.user import AuthProvider, User
from app.repositories.refresh_tokens import RefreshTokensRepository
from app.repositories.users import UsersRepository
from app.schemas.auth import AuthResponse, LoginRequest, RegisterRequest, UserProfile
from app.services.jwt_service import JwtService
from app.services.passwords import hash_password, verify_password
from app.timeutil import utc_now


@dataclass
class TokenPair:
    auth_response: AuthResponse
    raw_refresh_token: str


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def to_profile(user: User) -> UserProfile:
    return UserProfile(id=user.id, email=user.email, display_name=user.display_name)


def _invalid_credentials() -> ApiError:
    return ApiError(401, "INVALID_CREDENTIALS", "Invalid credentials")


class AuthService:
    def __init__(
        self,
        users: UsersRepository,
        refresh_tokens: RefreshTokensRepository,
        jwt_service: JwtService,
        refresh_token_expiry_days: int,
    ) -> None:
        self.users = users
        self.refresh_tokens = refresh_tokens
        self.jwt_service = jwt_service
        self.refresh_token_expiry_days = refresh_token_expiry_days

    async def register(self, request: RegisterRequest) -> UserProfile:
        # Email is stored and looked up exactly as submitted: existing records were stored verbatim.
        if await self.users.exists_by_email(request.email):
            raise ApiError(409, "EMAIL_ALREADY_REGISTERED", "Email already registered")
        user = User(
            email=request.email,
            password_hash=await hash_password(request.password),
            auth_provider=AuthProvider.LOCAL,
            display_name=request.display_name,
        )
        try:
            user = await self.users.insert(user)
        except DuplicateKeyError:  # lost a race with a concurrent registration
            raise ApiError(409, "EMAIL_ALREADY_REGISTERED", "Email already registered") from None
        return to_profile(user)

    async def login(self, request: LoginRequest) -> TokenPair:
        user = await self.users.find_by_email(request.email)
        if user is None or user.password_hash is None:  # unknown email, or a Google-only account
            raise _invalid_credentials()
        if not await verify_password(request.password, user.password_hash):
            raise _invalid_credentials()
        return await self.issue_tokens(user)

    async def refresh(self, raw_refresh_token: str) -> TokenPair:
        stored = await self.refresh_tokens.find_by_hash(hash_token(raw_refresh_token))
        if stored is None:
            raise ApiError(401, "INVALID_REFRESH_TOKEN", "Invalid or expired refresh token")
        if stored.expires_at < utc_now():
            await self.refresh_tokens.delete(stored)
            raise ApiError(401, "INVALID_REFRESH_TOKEN", "Refresh token expired")

        # Rotation: the presented token is consumed before a new pair is issued.
        await self.refresh_tokens.delete(stored)
        user = await self.users.find_by_id(stored.user_id)
        if user is None:
            raise ApiError(401, "INVALID_REFRESH_TOKEN", "User not found")
        return await self.issue_tokens(user)

    async def logout(self, raw_refresh_token: str) -> None:
        stored = await self.refresh_tokens.find_by_hash(hash_token(raw_refresh_token))
        if stored is not None:
            await self.refresh_tokens.delete(stored)

    async def find_or_create_google_user(self, google_id: str, email: str, display_name: str) -> User:
        user = await self.users.find_by_google_id(google_id)
        if user is not None:
            return user
        existing = await self.users.find_by_email(email)
        if existing is not None:  # link the Google identity to the existing account
            existing.google_id = google_id
            return await self.users.save(existing)
        return await self.users.insert(
            User(email=email, auth_provider=AuthProvider.GOOGLE, google_id=google_id, display_name=display_name)
        )

    async def issue_tokens(self, user: User) -> TokenPair:
        access_token = self.jwt_service.generate_access_token(user.id, user.email)
        raw_refresh_token = str(uuid.uuid4())
        await self.refresh_tokens.insert(
            RefreshToken(
                user_id=user.id,
                token_hash=hash_token(raw_refresh_token),
                expires_at=utc_now() + timedelta(days=self.refresh_token_expiry_days),
            )
        )
        return TokenPair(AuthResponse(access_token=access_token, user=to_profile(user)), raw_refresh_token)
