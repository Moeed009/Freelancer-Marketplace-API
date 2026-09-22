from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from app.core.config import settings
from app.db.database import session_scope
from app.models.enums import DeliveryStatus, NotificationChannel, NotificationEventType
from app.models.notification import NotificationDelivery
from app.models.user import User
from app.notifications import providers, templates
from app.repositories import notification_repository
from app.services import notification_service

logger = logging.getLogger(__name__)


def _fail(delivery: NotificationDelivery, error: str, now: datetime) -> None:
    delivery.status = DeliveryStatus.FAILED
    delivery.last_error = error[:1000]
    delivery.last_attempt_at = now
    delivery.next_attempt_at = None


def _attempt(delivery: NotificationDelivery, db, now: datetime) -> None:
    
    event = delivery.event
    delivery.attempt_count += 1
    delivery.last_attempt_at = now

    try:
        event_type = NotificationEventType(event.event_type)
    except ValueError:
        
        _fail(delivery, f"Unknown event type: {event.event_type}", now)
        return

    recipient = db.get(User, event.recipient_id)
    if recipient is None:
        _fail(delivery, "Recipient no longer exists.", now)
        return

    destination = (
        recipient.email if delivery.channel is NotificationChannel.EMAIL else recipient.phone
    )
    if not destination:
        _fail(delivery, "No destination on file for this channel.", now)
        return

    try:
        message = templates.render(
            event_type, delivery.channel, event.payload, app_name=settings.APP_NAME
        )
    except templates.TemplateRenderError as exc:
       
        _fail(delivery, f"Template error: {exc}", now)
        return

    provider = providers.get_provider(delivery.channel)

    try:
        provider.send(destination, message)
    except providers.PermanentProviderError as exc:
        _fail(delivery, f"Permanent: {exc}", now)
        return
    except providers.TransientProviderError as exc:
        if delivery.attempt_count >= delivery.max_attempts:
            _fail(delivery, f"Retries exhausted. Last error: {exc}", now)
        else:
            delivery.last_error = f"Transient: {exc}"[:1000]
            delivery.next_attempt_at = now + notification_service.compute_backoff(
                delivery.attempt_count
            )
            
        return
    except Exception as exc:  
        logger.exception("Unexpected provider error on delivery %s", delivery.id)
        if delivery.attempt_count >= delivery.max_attempts:
            _fail(delivery, f"Unexpected error: {exc}", now)
        else:
            delivery.last_error = f"Unexpected: {exc}"[:1000]
            delivery.next_attempt_at = now + notification_service.compute_backoff(
                delivery.attempt_count
            )
        return

    delivery.status = DeliveryStatus.SENT
    delivery.sent_at = now
    delivery.next_attempt_at = None
    delivery.last_error = None


def process_due_deliveries(limit: int | None = None, now: datetime | None = None) -> int:
    
    now = now or datetime.now(timezone.utc)
    limit = limit or settings.NOTIFICATION_WORKER_BATCH_SIZE

    with session_scope() as db:
        due = notification_repository.claim_due_deliveries(db, now, limit)
        for delivery in due:
            _attempt(delivery, db, now)
        
        return len(due)


async def worker_loop(stop_event: asyncio.Event) -> None:
   
    logger.info("Notification dispatcher started.")
    while not stop_event.is_set():
        try:
            
            await asyncio.to_thread(process_due_deliveries)
        except Exception:  
            logger.exception("Notification dispatcher tick failed.")

        try:
            await asyncio.wait_for(
                stop_event.wait(), timeout=settings.NOTIFICATION_WORKER_INTERVAL_SECONDS
            )
        except asyncio.TimeoutError:
            continue

    logger.info("Notification dispatcher stopped.")
