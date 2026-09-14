import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field, computed_field

from app.models.enums import MilestoneStatus


class MilestoneCreateRequest(BaseModel):
    title: str = Field(min_length=2, max_length=150)
    description: str | None = None
    amount: float = Field(gt=0)
    due_date: date | None = None


class MilestoneUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=150)
    description: str | None = None
    amount: float | None = Field(default=None, gt=0)
    due_date: date | None = None


class MilestoneStatusUpdateRequest(BaseModel):
    status: MilestoneStatus


class MilestoneOut(BaseModel):
    id: uuid.UUID
    contract_id: uuid.UUID
    title: str
    description: str | None
    amount: float
    due_date: date | None
    status: MilestoneStatus
    deliverable_url: str | None
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def is_complete(self) -> bool:
        return self.status == MilestoneStatus.APPROVED

    model_config = {"from_attributes": True}