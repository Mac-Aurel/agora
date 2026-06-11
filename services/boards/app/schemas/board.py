import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.board import ContributionType, ValidationStatus


class BoardBase(BaseModel):
    """Shared fields for board creation and representation."""

    title: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    tags: Optional[list[str]] = None
    is_public: bool = True


class BoardCreate(BoardBase):
    """Payload for creating a board."""


class BoardUpdate(BaseModel):
    """Payload for partially updating a board. All fields optional."""

    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    tags: Optional[list[str]] = None
    is_public: Optional[bool] = None


class BoardResponse(BoardBase):
    """Public representation of a board."""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    owner_id: uuid.UUID
    created_at: datetime
    updated_at: Optional[datetime] = None


class BoardItemResponse(BaseModel):
    """Public representation of a board item."""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    board_id: uuid.UUID
    content_id: uuid.UUID
    added_by: uuid.UUID
    status: ValidationStatus
    created_at: datetime


class BoardDetailResponse(BoardResponse):
    """Board representation including its items, for the detail endpoint."""

    items: list[BoardItemResponse] = []


class BoardItemCreate(BaseModel):
    """Payload for adding an item to a board."""

    content_id: uuid.UUID


class ItemConnectionCreate(BaseModel):
    """Payload for connecting two items of the same board."""

    item_a_id: uuid.UUID
    item_b_id: uuid.UUID
    label: Optional[str] = Field(default=None, max_length=255)


class ItemConnectionResponse(BaseModel):
    """Public representation of a connection between two items."""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    item_a_id: uuid.UUID
    item_b_id: uuid.UUID
    label: Optional[str] = None
    created_by: uuid.UUID
    created_at: datetime


class ContributionCreate(BaseModel):
    """Payload for submitting a contribution on a board item."""

    type: ContributionType
    body: str = Field(min_length=1)


class ContributionResponse(BaseModel):
    """Public representation of a contribution."""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    board_item_id: uuid.UUID
    contributor_id: uuid.UUID
    type: ContributionType
    body: str
    status: ValidationStatus
    created_at: datetime
