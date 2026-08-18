from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
import uuid

from app.api.v1.auth import get_current_user
from app.core.database import get_db
from app.models.models import User

router = APIRouter()

class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    is_active: bool
    is_superuser: bool = False

    class Config:
        from_attributes = True  # Pydantic v2 equivalent of orm_mode

@router.get("/me", response_model=UserResponse)
def read_users_me(current_user: User = Depends(get_current_user)):
    """
    Get current authenticated user.
    """
    return current_user
