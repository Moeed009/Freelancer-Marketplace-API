import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.enums import DeliveryStatus, NotificationCategory, NotificationChannel
from app.models.notification import NotificationDelivery, NotificationEvent, NotificationPreference



def get_event_by_idempotency_key(db: Session, idempotency_key: str) -> NotificationEvent | None:
    return db.execute(
        select(NotificationEvent).where(NotificationEvent.idempotency_key == idempotency_key)
    ).scalar_one_or_none()


def create_event(
    db: Session,
    *,
    event_type: str,
    category: NotificationCategory,
    recipient_id: uuid.UUID,
    payload: dict,
    idempotency_key: str,
) -> NotificationEvent:
    event = NotificationEvent(
        event_type=event_type,
        category=category,
        recipient_id=recipient_id,
        payload=payload,
        idempotency_key=idempotency_key,
    )
    db.add(event)
    db.flush()  
    return event


def list_events_for_user(
    db: Session, user_id: uuid.UUID, offset: int, limit: int
) -> tuple[list[NotificationEvent], int]:
    
    total = db.execute(
        select(func.count(NotificationEvent.id)).where(NotificationEvent.recipient_id == user_id)
    ).scalar_one()

    items = (
        db.execute(
            select(NotificationEvent)
            .options(selectinload(NotificationEvent.deliveries))
            .where(NotificationEvent.recipient_id == user_id)
            .order_by(NotificationEvent.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        .scalars()
        .all()
    )
    return list(items), total




def create_delivery(
    db: Session,
    *,
    event_id: uuid.UUID,
    channel: NotificationChannel,
    destination_masked: str | None,
    status: DeliveryStatus,
    max_attempts: int,
    next_attempt_at: datetime | None,
    last_error: str | None = None,
) -> NotificationDelivery:
    delivery = NotificationDelivery(
        event_id=event_id,
        channel=channel,
        destination_masked=destination_masked,
        status=status,
        max_attempts=max_attempts,
        next_attempt_at=next_attempt_at,
        last_error=last_error,
    )
    db.add(delivery)
    db.flush()
    return delivery


def claim_due_deliveries(db: Session, now: datetime, limit: int) -> list[NotificationDelivery]:
    
    query = (
        select(NotificationDelivery)
        .options(selectinload(NotificationDelivery.event))
        .where(
            NotificationDelivery.status == DeliveryStatus.PENDING,
            NotificationDelivery.next_attempt_at <= now,
        )
        .order_by(NotificationDelivery.next_attempt_at)
        .limit(limit)
    )

    if db.bind is not None and db.bind.dialect.name == "postgresql":
        query = query.with_for_update(skip_locked=True, of=NotificationDelivery)

    return list(db.execute(query).scalars().all())


def get_delivery(db: Session, delivery_id: uuid.UUID) -> NotificationDelivery | None:
    return db.get(NotificationDelivery, delivery_id)





def list_preferences(db: Session, user_id: uuid.UUID) -> list[NotificationPreference]:
    return list(
        db.execute(
            select(NotificationPreference).where(NotificationPreference.user_id == user_id)
        )
        .scalars()
        .all()
    )


def get_preference(
    db: Session,
    user_id: uuid.UUID,
    category: NotificationCategory,
    channel: NotificationChannel,
) -> NotificationPreference | None:
    return db.execute(
        select(NotificationPreference).where(
            NotificationPreference.user_id == user_id,
            NotificationPreference.category == category,
            NotificationPreference.channel == channel,
        )
    ).scalar_one_or_none()


def upsert_preference(
    db: Session,
    *,
    user_id: uuid.UUID,
    category: NotificationCategory,
    channel: NotificationChannel,
    enabled: bool,
) -> NotificationPreference:
    preference = get_preference(db, user_id, category, channel)
    if preference is None:
        preference = NotificationPreference(
            user_id=user_id, category=category, channel=channel, enabled=enabled
        )
        db.add(preference)
    else:
        preference.enabled = enabled
    db.flush()
    return preference
