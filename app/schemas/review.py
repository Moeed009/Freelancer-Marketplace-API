import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ReviewCreateRequest(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str | None = None


class ReviewUpdateRequest(BaseModel):
    rating: int | None = Field(default=None, ge=1, le=5)
    comment: str | None = None


class ReviewOut(BaseModel):
    id: uuid.UUID
    contract_id: uuid.UUID
    reviewer_id: uuid.UUID
    reviewee_id: uuid.UUID
    rating: int
    comment: str | None
    created_at: datetime

    model_config = {"from_attributes": True}