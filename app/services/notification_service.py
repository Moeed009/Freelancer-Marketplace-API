from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import session_scope
from app.models.enums import (
    DeliveryStatus,
    NotificationCategory,
    NotificationChannel,
    NotificationEventType,
)
from app.models.notification import NotificationEvent
from app.models.user import User
from app.notifications import events as event_catalog
from app.notifications import templates
from app.repositories import notification_repository

logger = logging.getLogger(__name__)


def build_idempotency_key(event_type: NotificationEventType, *parts: object) -> str:
    return ":".join([event_type.value, *(str(part) for part in parts)])


def mask_email(email: str) -> str:
    local, _, domain = email.partition("@")
    if not domain:
        return "***"
    if len(local) <= 2:
        return f"{local[0]}***@{domain}"
    return f"{local[0]}***{local[-1]}@{domain}"


def _destination_for(user: User, channel: NotificationChannel) -> str | None:
    
    if channel is NotificationChannel.EMAIL:
        return user.email
    return None


def _mask(destination: str, channel: NotificationChannel) -> str:
    return mask_email(destination)


def resolve_channels(
    db: Session,
    user: User,
    event_type: NotificationEventType,
) -> dict[NotificationChannel, str | None]:

    spec = event_catalog.get_spec(event_type)
    result: dict[NotificationChannel, str | None] = {}

    for channel in spec.default_channels:
        if not templates.has_template(event_type, channel):
            result[channel] = "no_template_for_channel"
            continue

        if not spec.mandatory:
            preference = notification_repository.get_preference(db, user.id, spec.category, channel)
            if preference is not None and not preference.enabled:
                result[channel] = "disabled_by_preference"
                continue

        if not _destination_for(user, channel):
            result[channel] = "no_destination_on_file"
            continue

        result[channel] = None

    return result


def emit(
    event_type: NotificationEventType,
    recipient_id: uuid.UUID,
    payload: dict,
    *,
    idempotency_key: str,
) -> uuid.UUID | None:

    try:
        event_catalog.validate_payload(event_type, payload)
        spec = event_catalog.get_spec(event_type)

        with session_scope() as db:
            existing = notification_repository.get_event_by_idempotency_key(db, idempotency_key)
            if existing is not None:
                logger.info("Duplicate notification event suppressed: %s", idempotency_key)
                return existing.id

            recipient = db.get(User, recipient_id)
            if recipient is None:
                logger.warning("Notification recipient %s not found; skipping", recipient_id)
                return None

            channels = resolve_channels(db, recipient, event_type)

            event = notification_repository.create_event(
                db,
                event_type=event_type.value,
                category=spec.category,
                recipient_id=recipient_id,
                payload=payload,
                idempotency_key=idempotency_key,
            )

            now = datetime.now(timezone.utc)
            for channel, skip_reason in channels.items():
                destination = _destination_for(recipient, channel)
                notification_repository.create_delivery(
                    db,
                    event_id=event.id,
                    channel=channel,
                    destination_masked=_mask(destination, channel) if destination else None,
                    status=DeliveryStatus.SKIPPED if skip_reason else DeliveryStatus.PENDING,
                    max_attempts=settings.NOTIFICATION_MAX_ATTEMPTS,
                    next_attempt_at=None if skip_reason else now,
                    last_error=skip_reason,
                )

            return event.id

    except IntegrityError:
        logger.info("Concurrent duplicate notification event suppressed: %s", idempotency_key)
        return None
    except Exception:  
        logger.exception("Failed to record notification event %s", event_type)
        return None


def list_my_notifications(db: Session, user: User, offset: int, limit: int):
    return notification_repository.list_events_for_user(db, user.id, offset, limit)


def get_my_preferences(db: Session, user: User) -> list[dict]:

    stored = {
        (pref.category, pref.channel): pref.enabled
        for pref in notification_repository.list_preferences(db, user.id)
    }

    rows: list[dict] = []
    for category in NotificationCategory:
        for channel in NotificationChannel:
            
            used = any(
                spec.category is category and channel in spec.default_channels
                for spec in event_catalog.EVENT_CATALOG.values()
            )
            if not used:
                continue
            mandatory = any(
                spec.category is category and spec.mandatory
                for spec in event_catalog.EVENT_CATALOG.values()
            )
            rows.append(
                {
                    "category": category,
                    "channel": channel,
                    "enabled": True if mandatory else stored.get((category, channel), True),
                    "mandatory": mandatory,
                }
            )
    return rows


def update_my_preferences(db: Session, user: User, updates: list) -> list[dict]:

    from app.core.exceptions import ValidationAppError

    for update in updates:
        mandatory = any(
            spec.category is update.category and spec.mandatory
            for spec in event_catalog.EVENT_CATALOG.values()
        )
        if mandatory and not update.enabled:
            raise ValidationAppError(
                f"{update.category.value} notifications are transactional and cannot be disabled."
            )

        notification_repository.upsert_preference(
            db,
            user_id=user.id,
            category=update.category,
            channel=update.channel,
            enabled=update.enabled,
        )

    db.commit()
    return get_my_preferences(db, user)


def compute_backoff(attempt_count: int) -> timedelta:

    seconds = settings.NOTIFICATION_RETRY_BACKOFF_SECONDS * (2 ** max(attempt_count - 1, 0))
    return timedelta(seconds=seconds)


def get_event(db: Session, event_id: uuid.UUID) -> NotificationEvent | None:
    return db.get(NotificationEvent, event_id)