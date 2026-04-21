"""User bootstrap — just echoes back the authenticated user."""
from fastapi import APIRouter, Depends

from ..deps import get_or_create_user
from ..models import User
from ..schemas import UserOut

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_or_create_user)) -> User:
    """Return (creating if needed) the user identified by the header."""
    return user
