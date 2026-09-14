import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import AvailabilityStatus
from app.schemas.skill import SkillOut


class FreelancerProfileCreate(BaseModel):
   

    headline: str | None = Field(default=None, max_length=150)
    bio: str | None = None
    hourly_rate: float | None = Field(default=None, ge=0)
    skill_ids: list[uuid.UUID]
    experience_years: int | None = Field(default=None, ge=0)
    availability: AvailabilityStatus | None = None


class FreelancerProfileUpdate(BaseModel):
   

    headline: str | None = Field(default=None, max_length=150)
    bio: str | None = None
    hourly_rate: float | None = Field(default=None, ge=0)
    skill_ids: list[uuid.UUID] | None = None
    experience_years: int | None = Field(default=None, ge=0)
    availability: AvailabilityStatus | None = None


class FreelancerProfileOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    headline: str | None
    bio: str | None
    hourly_rate: float | None
    experience_years: int | None
    availability: AvailabilityStatus
    skills: list[SkillOut] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}