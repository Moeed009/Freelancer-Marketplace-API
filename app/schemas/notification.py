import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import (
    DeliveryStatus,
    NotificationCategory,
    NotificationChannel,
    NotificationEventType,
)


class NotificationDeliveryOut(BaseModel):
    

    model_config = ConfigDict(from_attributes=True)

    channel: NotificationChannel
    status: DeliveryStatus
    destination_masked: str | None
    attempt_count: int
    last_error: str | None
    last_attempt_at: datetime | None
    sent_at: datetime | None


class NotificationEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    event_type: str
    category: NotificationCategory
    payload: dict
    created_at: datetime
    deliveries: list[NotificationDeliveryOut]


class NotificationPreferenceOut(BaseModel):
    category: NotificationCategory
    channel: NotificationChannel
    enabled: bool
    
    mandatory: bool


class NotificationPreferenceUpdate(BaseModel):
    category: NotificationCategory
    channel: NotificationChannel
    enabled: bool


class NotificationPreferencesUpdateRequest(BaseModel):
    preferences: list[NotificationPreferenceUpdate] = Field(min_length=1, max_length=50)


class NotificationTestRequest(BaseModel):
    
    event_type: NotificationEventType = NotificationEventType.USER_REGISTERED
    payload: dict = Field(default_factory=dict)


class NotificationTestResponse(BaseModel):
    event_id: uuid.UUID | None
    processed: int
