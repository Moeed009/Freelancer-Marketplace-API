import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import ProposalStatus


class ProposalCreateRequest(BaseModel):
    cover_letter: str = Field(min_length=10)
    bid_amount: float = Field(gt=0)
    estimated_duration_days: int = Field(gt=0)


class ProposalStatusUpdateRequest(BaseModel):
   
    status: ProposalStatus


class ProposalOut(BaseModel):
    id: uuid.UUID
    job_id: uuid.UUID
    freelancer_id: uuid.UUID
    cover_letter: str
    bid_amount: float
    estimated_duration_days: int
    status: ProposalStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
