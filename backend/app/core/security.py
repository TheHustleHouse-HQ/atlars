from datetime import datetime, timedelta, timezone
from typing import Any
import uuid

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"
ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def _create_token(token_type: str, user_id: str, expires_delta: timedelta, token_id: str | None = None) -> str:
    tid = token_id or str(uuid.uuid4())
    expire = datetime.now(timezone.utc) + expires_delta
    payload = {
        "sub": user_id,
        "type": token_type,
        "jti": tid,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def create_access_token(user_id: str) -> str:
    return _create_token(
        ACCESS_TOKEN_TYPE,
        user_id,
        timedelta(minutes=settings.access_token_expire_minutes),
    )


def create_refresh_token(user_id: str) -> tuple[str, str]:
    """Returns (token, token_id). Store token_id in DB to enable rotation/invalidation."""
    token_id = str(uuid.uuid4())
    token = _create_token(
        REFRESH_TOKEN_TYPE,
        user_id,
        timedelta(days=settings.refresh_token_expire_days),
        token_id=token_id,
    )
    return token, token_id


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT. Raises JWTError if invalid or expired."""
    return jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])


def decode_access_token(token: str) -> dict[str, Any]:
    payload = decode_token(token)
    if payload.get("type") != ACCESS_TOKEN_TYPE:
        raise JWTError("Not an access token")
    return payload


def decode_refresh_token(token: str) -> dict[str, Any]:
    payload = decode_token(token)
    if payload.get("type") != REFRESH_TOKEN_TYPE:
        raise JWTError("Not a refresh token")
    return payload
