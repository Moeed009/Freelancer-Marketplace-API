import uuid

from pydantic import BaseModel, Field


class SkillCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class SkillOut(BaseModel):
    id: uuid.UUID
    name: str

    model_config = {"from_attributes": True}


class SkillUpdate(BaseModel):
    name: str




    class Config:
        from_attributes = True