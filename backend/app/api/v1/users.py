from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict
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
    avatar_url: str | None = None

    model_config = ConfigDict(from_attributes=True)

class UserUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None

@router.get("/me", response_model=UserResponse)
def read_users_me(current_user: User = Depends(get_current_user)):
    """
    Get current authenticated user.
    """
    return current_user

@router.patch("/me", response_model=UserResponse)
def update_user_me(
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if payload.email:
        current_user.email = payload.email
    if payload.first_name or payload.last_name:
        fname = payload.first_name or current_user.full_name.split()[0]
        lname = payload.last_name or (current_user.full_name.split()[1] if len(current_user.full_name.split()) > 1 else "")
        current_user.full_name = f"{fname} {lname}".strip()
        
    db.commit()
    db.refresh(current_user)
    return current_user

from fastapi import UploadFile, File, HTTPException
import os
import shutil
from app.core.config import settings

@router.post("/me/avatar", response_model=UserResponse)
async def upload_avatar(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are allowed")
        
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    ext = os.path.splitext(file.filename)[1]
    filename = f"avatar_{current_user.id}{ext}"
    file_path = os.path.join(settings.UPLOAD_DIR, filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # Set a fake URL for now, could be an actual static URL or S3 link
    current_user.avatar_url = f"/uploads/{filename}"
    db.commit()
    db.refresh(current_user)
    
    return current_user
