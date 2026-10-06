from fastapi import APIRouter, Depends

from app.deps import current_user_id, get_user_service
from app.schemas.auth import UserProfile
from app.services.auth_service import to_profile
from app.services.user_service import UserService

router = APIRouter(prefix="/api/v1/users")


@router.get("/me", response_model=UserProfile)
async def me(user_id: str = Depends(current_user_id), users: UserService = Depends(get_user_service)):
    return to_profile(await users.get_user(user_id))
