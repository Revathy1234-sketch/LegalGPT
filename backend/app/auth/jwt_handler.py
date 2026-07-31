from datetime import datetime, timedelta
from typing import Any, Union
from jose import jwt
from app.core.config import settings


def create_access_token(subject: Union[str, Any], expires_delta: timedelta = None) -> str:
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = {"exp": expire, "sub": str(subject)}
    secret_key = settings.JWT_SECRET or settings.SECRET_KEY
    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> dict:
    secret_key = settings.JWT_SECRET or settings.SECRET_KEY
    return jwt.decode(token, secret_key, algorithms=[settings.ALGORITHM])
