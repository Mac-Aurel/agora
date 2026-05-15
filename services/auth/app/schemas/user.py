import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    """Payload for user registration."""

    username: str = Field(
        min_length=3,
        max_length=50,
        pattern=r"^[a-zA-Z0-9_]+$",
        description="3-50 chars, alphanumeric and underscores only",
    )
    password: str = Field(min_length=8, description="Minimum 8 characters")


class LoginRequest(BaseModel):
    """Payload for user login. No creation constraints applied."""

    username: str
    password: str


class UserResponse(BaseModel):
    """Public user representation. Never exposes password_hash."""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    username: str
    bio: Optional[str] = None
    reputation: int
    created_at: datetime


class Token(BaseModel):
    """JWT access token response."""

    access_token: str
    token_type: str = "bearer"


class UserUpdate(BaseModel):
    """Payload for updating the authenticated user's profile."""

    bio: Optional[str] = None
