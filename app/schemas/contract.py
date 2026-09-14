import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.enums import ContractStatus


class ContractStatusUpdateRequest(BaseModel):
    
    status: ContractStatus


class ContractOut(BaseModel):
    id: uuid.UUID
    job_id: uuid.UUID
    proposal_id: uuid.UUID
    client_id: uuid.UUID
    freelancer_id: uuid.UUID
    agreed_amount: float
    status: ContractStatus
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}
