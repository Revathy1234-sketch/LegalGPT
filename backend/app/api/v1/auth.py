from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from jose import JWTError
from app.core.database import get_db
from app.core.config import settings
from app.auth.jwt_handler import create_access_token, decode_access_token
from app.auth.login import authenticate_user
from app.auth.register import register_user
from app.models.models import User
from app.schemas.schemas import UserCreate, UserResponse, Token
import uuid

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")


def resolve_user_from_token(token: str, db: Session) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        parsed_user_id = uuid.UUID(user_id)
    except (JWTError, TypeError, ValueError):
        raise credentials_exception
    
    user = db.query(User).filter(User.id == parsed_user_id).first()
    if user is None or not user.is_active:
        raise credentials_exception
    return user


def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)) -> User:
    return resolve_user_from_token(token, db)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    return register_user(user_in, db)

@router.post("/login", response_model=Token)
def login(user_credentials: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    try:
        print(f"Login attempt: {user_credentials.username}")

        user = authenticate_user(user_credentials.username, user_credentials.password, db)
        print(f"User found: {user is not None}")

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        print("Creating access token...")
        access_token = create_access_token(subject=user.id)
        return {"access_token": access_token, "token_type": "bearer"}

    except Exception as e:
        import traceback

        print("\n========== LOGIN ERROR ==========")
        print(str(e))
        traceback.print_exc()
        print("=================================\n")

        raise
