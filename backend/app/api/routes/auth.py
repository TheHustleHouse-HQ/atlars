from datetime import datetime

from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from pydantic import BaseModel, field_validator

from app.core.database import get_users_collection
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
)
from app.models.user import UserCreate, UserResponse, UserInDB
from app.api.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])
bearer_scheme = HTTPBearer()


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class LoginRequest(BaseModel):
    email: str
    password: str


class UpdatePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters.")
        return v


def _user_response(user: dict) -> UserResponse:
    return UserResponse(
        user_id=user["user_id"],
        email=user["email"],
        display_name=user["display_name"],
        maturity_stage=user["maturity_stage"],
        created_at=user["created_at"],
    )


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: UserCreate):
    users = get_users_collection()

    existing = await users.find_one({"email": payload.email.lower()})
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered.")

    user = UserInDB.new(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        display_name=payload.display_name,
    )

    refresh_token, token_id = create_refresh_token(user.user_id)
    user.active_refresh_token_ids.append(token_id)

    await users.insert_one(user.model_dump())

    return AuthResponse(
        access_token=create_access_token(user.user_id),
        refresh_token=refresh_token,
        user=_user_response(user.model_dump()),
    )


@router.post("/login", response_model=AuthResponse)
async def login(payload: LoginRequest):
    users = get_users_collection()

    user = await users.find_one({"email": payload.email.lower()})
    if not user or not verify_password(payload.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    refresh_token, token_id = create_refresh_token(user["user_id"])

    await users.update_one(
        {"user_id": user["user_id"]},
        {
            "$push": {"active_refresh_token_ids": token_id},
            "$set": {"last_active_at": datetime.utcnow()},
        },
    )

    return AuthResponse(
        access_token=create_access_token(user["user_id"]),
        refresh_token=refresh_token,
        user=_user_response(user),
    )


@router.post("/refresh", response_model=AuthResponse)
async def refresh(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    invalid_exc = HTTPException(status_code=401, detail="Invalid or expired refresh token.")

    try:
        payload = decode_refresh_token(credentials.credentials)
        user_id = payload["sub"]
        token_id = payload["jti"]
    except JWTError:
        raise invalid_exc

    users = get_users_collection()
    user = await users.find_one({"user_id": user_id})

    if not user:
        raise invalid_exc

    if token_id not in user.get("active_refresh_token_ids", []):
        # Token reuse detected — invalidate all tokens for this user
        await users.update_one(
            {"user_id": user_id},
            {"$set": {"active_refresh_token_ids": []}},
        )
        raise HTTPException(status_code=401, detail="Refresh token reuse detected. Please log in again.")

    new_refresh_token, new_token_id = create_refresh_token(user_id)

    # Rotate: remove old token ID, add new one
    updated_ids = [tid for tid in user["active_refresh_token_ids"] if tid != token_id]
    updated_ids.append(new_token_id)

    await users.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "active_refresh_token_ids": updated_ids,
                "last_active_at": datetime.utcnow(),
            }
        },
    )

    return AuthResponse(
        access_token=create_access_token(user_id),
        refresh_token=new_refresh_token,
        user=_user_response(user),
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    try:
        payload = decode_refresh_token(credentials.credentials)
        user_id = payload["sub"]
        token_id = payload["jti"]
    except JWTError:
        return  # Already invalid — treat as success

    users = get_users_collection()
    await users.update_one(
        {"user_id": user_id},
        {"$pull": {"active_refresh_token_ids": token_id}},
    )


@router.post("/change-password", response_model=AuthResponse)
async def change_password(
    payload: UpdatePasswordRequest,
    current_user: dict = Depends(get_current_user)
):
    users = get_users_collection()
    
    # Verify current password
    if not verify_password(payload.current_password, current_user["hashed_password"]):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid current password.")
        
    if payload.current_password == payload.new_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="New password must be different from current password.")

    hashed_new_password = hash_password(payload.new_password)
    new_refresh_token, new_token_id = create_refresh_token(current_user["user_id"])
    
    # Invalidate all existing refresh tokens, so user has to login again on other devices
    await users.update_one(
        {"user_id": current_user["user_id"]},
        {
            "$set": {
                "hashed_password": hashed_new_password,
                "active_refresh_token_ids": [new_token_id],
                "last_active_at": datetime.utcnow()
            }
        }
    )
    
    return AuthResponse(
        access_token=create_access_token(current_user["user_id"]),
        refresh_token=new_refresh_token,
        user=_user_response(current_user),
    )
