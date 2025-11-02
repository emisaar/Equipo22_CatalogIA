from datetime import datetime, timedelta, timezone
from typing import Optional
import hashlib
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def verify_password(plain_password: str, hashed_password: str) -> bool:
    # Pre-hash with SHA256 to ensure we never exceed bcrypt's 72-byte limit
    password_sha256 = hashlib.sha256(plain_password.encode("utf-8")).hexdigest()
    return pwd_context.verify(password_sha256, hashed_password)


def get_password_hash(password: str) -> str:
    # Pre-hash with SHA256 to ensure we never exceed bcrypt's 72-byte limit
    # SHA256 always produces a fixed-length output (64 hex characters)
    password_sha256 = hashlib.sha256(password.encode("utf-8")).hexdigest()
    return pwd_context.hash(password_sha256)


def verify_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        return email
    except JWTError:
        return None