import math
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import ForbiddenError
from app.db.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.pagination import PaginationParams
from app.models.user import User
from app.schemas.common import Page
from app.schemas.notification import (
    NotificationEventOut,
    NotificationPreferenceOut,
    NotificationPreferencesUpdateRequest,
    NotificationTestRequest,
    NotificationTestResponse,
)
from app.services import notification_dispatcher, notification_service

router = APIRouter(prefix="/api/notifications", tags=["Notifications"])


@router.get(
    "",
    response_model=Page[NotificationEventOut],
    summary="List your own notification history",
    description=(
        "Returns notifications addressed to the authenticated user only, newest first. "
        "There is no way to request another user's history: the recipient is taken from "
        "the access token, never from a query or path parameter."
    ),
)
def list_my_notifications(
    current_user: User = Depends(get_current_user),
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
):
    items, total = notification_service.list_my_notifications(
        db, current_user, pagination.offset, pagination.page_size
    )
    return Page(
        items=items,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        total_pages=math.ceil(total / pagination.page_size) if total else 0,
    )


@router.get(
    "/preferences",
    response_model=list[NotificationPreferenceOut],
    summary="Get your effective notification preferences",
    description=(
        "Effective values: stored overrides layered on top of the catalog defaults. "
        "Entries marked `mandatory` are transactional or security notifications and "
        "always report `enabled: true`."
    ),
)
def get_preferences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return notification_service.get_my_preferences(db, current_user)


@router.patch(
    "/preferences",
    response_model=list[NotificationPreferenceOut],
    summary="Update your notification preferences",
    description=(
        "Partial update by (category, channel). "
    ),
)
def update_preferences(
    payload: NotificationPreferencesUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return notification_service.update_my_preferences(db, current_user, payload.preferences)


@router.post(
    "/test",
    response_model=NotificationTestResponse,
    summary="Send yourself a test notification (non-production only)",
    description=(
        "Disabled when `ENVIRONMENT=production`. Sends only to the authenticated user; "
        
    ),
)
def send_test_notification(
    payload: NotificationTestRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if settings.ENVIRONMENT.lower() == "production":
        raise ForbiddenError("The notification test endpoint is disabled in production.")

    variables = {"full_name": current_user.full_name or current_user.email, **payload.payload}

    event_id = notification_service.emit(
        payload.event_type,
        current_user.id,
        variables,
        
        idempotency_key=notification_service.build_idempotency_key(
            payload.event_type, "test", current_user.id, uuid.uuid4()
        ),
    )

   
    processed = notification_dispatcher.process_due_deliveries()
    return NotificationTestResponse(event_id=event_id, processed=processed)
