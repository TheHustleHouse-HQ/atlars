from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError

from app.core.security import decode_access_token
from app.core.database import get_users_collection

bearer_scheme = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(credentials.credentials)
        user_id: str | None = payload.get("sub")
        if not user_id:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    users = get_users_collection()
    user = await users.find_one({"user_id": user_id})
    if not user:
        raise credentials_exception

    return user

def require_maturity_stage(required_stage: str):
    async def _dependency(current_user: dict = Depends(get_current_user)):
        stages = ["baseline", "extraction", "scoring", "inference"]
        current_stage = current_user.get("maturity_stage", "baseline")
        try:
            current_idx = stages.index(current_stage)
            req_idx = stages.index(required_stage)
        except ValueError:
            current_idx = 0
            req_idx = 0
            
        if current_idx < req_idx:
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail={
                    "code": "MATURITY_GATE",
                    "message": f"This feature requires the '{required_stage}' stage. You are currently at '{current_stage}'.",
                    "current_stage": current_stage,
                    "required_stage": required_stage
                }
            )
        return current_user
    return _dependency
