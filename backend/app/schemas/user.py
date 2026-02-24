"""
User Pydantic Schemas
"""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserBase(BaseModel):
    """Base user schema."""
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=255)


class UserCreate(UserBase):
    """Schema for user registration."""
    password: str = Field(..., min_length=8, max_length=128, description="Password (min 8 characters)")

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserUpdate(BaseModel):
    """Schema for updating user profile."""
    full_name: Optional[str] = Field(None, min_length=2, max_length=255)
    email: Optional[EmailStr] = None


class UserResponse(UserBase):
    """Schema for user response."""
    id: uuid.UUID
    is_active: bool
    is_verified: bool
    has_api_key: bool = False
    created_at: datetime
    updated_at: datetime
    api_key: Optional[str] = None

    @classmethod
    def model_validate(cls, obj, **kw):
        instance = super().model_validate(obj, **kw)
        # has_api_key derived from api_key presence
        instance.has_api_key = bool(getattr(obj, "api_key", None))
        return instance

    model_config = {"from_attributes": True}


class UserInDB(UserBase):
    """Schema for user stored in database."""
    id: uuid.UUID
    password_hash: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime
    api_key: Optional[str] = None

    model_config = {"from_attributes": True}
