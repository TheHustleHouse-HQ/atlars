from datetime import datetime
from pydantic import BaseModel, EmailStr, field_validator
import uuid


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    display_name: str

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters.")
        return v

    @field_validator("display_name")
    @classmethod
    def display_name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Display name cannot be empty.")
        return v.strip()


class UserResponse(BaseModel):
    user_id: str
    email: str
    display_name: str
    maturity_stage: str
    created_at: datetime


class UserInDB(BaseModel):
    user_id: str
    email: str
    hashed_password: str
    display_name: str
    created_at: datetime
    last_active_at: datetime
    maturity_stage: str
    entry_count: int
    first_entry_at: datetime | None
    namespace_config: dict
    framework_settings: dict
    # Refresh token management — list of valid token IDs
    active_refresh_token_ids: list[str]

    @classmethod
    def new(cls, email: str, hashed_password: str, display_name: str) -> "UserInDB":
        now = datetime.utcnow()
        return cls(
            user_id=str(uuid.uuid4()),
            email=email.lower(),
            hashed_password=hashed_password,
            display_name=display_name,
            created_at=now,
            last_active_at=now,
            maturity_stage="baseline",
            entry_count=0,
            first_entry_at=None,
            namespace_config={"compression_enabled": True, "data_retention_days": None},
            framework_settings={"ocean_enabled": True, "domain_scoring_enabled": True, "life_stage_enabled": True},
            active_refresh_token_ids=[],
        )
