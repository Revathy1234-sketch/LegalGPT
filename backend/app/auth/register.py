from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.models import Organization, User
from app.schemas.schemas import UserCreate
from app.core.security import get_password_hash
from app.core.enums import UserRole


def register_user(user_in: UserCreate, db: Session) -> User:
    normalized_email = str(user_in.email).strip().lower()
    existing = db.query(User).filter(User.email == normalized_email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists"
        )

    org_id = None
    if user_in.organization_name:
        org = Organization(name=user_in.organization_name)
        db.add(org)
        db.commit()
        db.refresh(org)
        org_id = org.id

    hashed_password = get_password_hash(user_in.password)
    new_user = User(
        email=normalized_email,
        password_hash=hashed_password,
        full_name=user_in.full_name,
        role=UserRole.READER,
        is_active=True,
        organization_id=org_id
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user
