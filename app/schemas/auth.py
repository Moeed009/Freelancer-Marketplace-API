import uuid

from pydantic import BaseModel, EmailStr, Field

from app.models.enums import UserRole
from app.models.enums import UserRole

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None
    role: UserRole   

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None
    role: UserRole   

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    
    pass


class AuthUserOut(BaseModel):
    id: uuid.UUID
    email: str
    role: UserRole
    full_name: str | None

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: AuthUserOut