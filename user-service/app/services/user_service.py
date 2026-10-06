from app.errors import ApiError
from app.models.user import User
from app.repositories.users import UsersRepository


class UserService:
    def __init__(self, users: UsersRepository) -> None:
        self.users = users

    async def get_user(self, user_id: str) -> User:
        user = await self.users.find_by_id(user_id)
        if user is None:
            raise ApiError(404, "USER_NOT_FOUND", "User not found")
        return user
