import uuid
from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from app.models.enums import JobStatus, RateType
from app.schemas.skill import SkillOut


class JobCreateRequest(BaseModel):
    title: str = Field(min_length=3, max_length=150)
    description: str = Field(min_length=10)
    rate_type: RateType
    budget_min: float = Field(ge=0)
    budget_max: float = Field(ge=0)
    skill_ids: list[uuid.UUID] = []

    @model_validator(mode="after")
    def check_budget_range(self):
        if self.budget_max < self.budget_min:
            raise ValueError("budget_max must be greater than or equal to budget_min")
        return self


class JobUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=150)
    description: str | None = Field(default=None, min_length=10)
    rate_type: RateType | None = None
    budget_min: float | None = Field(default=None, ge=0)
    budget_max: float | None = Field(default=None, ge=0)
    skill_ids: list[uuid.UUID] | None = None


class JobStatusUpdateRequest(BaseModel):
    status: JobStatus


class JobOut(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    title: str
    description: str
    rate_type: RateType
    budget_min: float
    budget_max: float
    status: JobStatus
    skills: list[SkillOut] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
