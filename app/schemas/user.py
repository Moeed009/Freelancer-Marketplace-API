import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.enums import UserRole


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    role: UserRole
    full_name: str | None
    avatar_url: str | None
    created_at: datetime


    model_config = {"from_attributes": True}


class UserPublicOut(BaseModel):
    
    id: uuid.UUID
    role: UserRole
    full_name: str | None

    model_config = {"from_attributes": True}


class UserUpdateRequest(BaseModel):
    full_name: str | None = None