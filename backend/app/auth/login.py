from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.core.security import verify_password
from app.models.models import User


def authenticate_user(email: str, password: str, db: Session) -> User | None:
    normalized_email = email.strip().lower()
    user = db.query(User).filter(User.email == normalized_email).first()
    if not user or not verify_password(password, user.password_hash):
        return None
    if not user.is_active:
        return None
    return user
