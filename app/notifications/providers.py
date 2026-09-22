

from __future__ import annotations

import logging
from typing import Protocol

import httpx

from app.core.config import settings
from app.models.enums import NotificationChannel
from app.notifications.templates import RenderedMessage

logger = logging.getLogger(__name__)


class ProviderError(Exception):
    """Base class for delivery failures."""


class TransientProviderError(ProviderError):
    """Temporary failure - the dispatcher should retry with backoff."""


class PermanentProviderError(ProviderError):
    """Permanent failure - retrying is pointless."""


class NotificationProvider(Protocol):
    channel: NotificationChannel

    def send(self, destination: str, message: RenderedMessage) -> None:
        
        raise NotImplementedError


def _classify_http_status(status_code: int, body: str) -> ProviderError:
   
    if status_code in (408, 429) or status_code >= 500:
        return TransientProviderError(f"Provider returned {status_code}: {body[:300]}")
    return PermanentProviderError(f"Provider returned {status_code}: {body[:300]}")


class SupabaseEmailProvider:
   

    channel = NotificationChannel.EMAIL

    def send(self, destination: str, message: RenderedMessage) -> None:
        if not settings.SUPABASE_URL or not settings.NOTIFICATION_EMAIL_FUNCTION:
            raise PermanentProviderError("Email provider is not configured.")

        url = f"{settings.SUPABASE_URL}/functions/v1/{settings.NOTIFICATION_EMAIL_FUNCTION}"
        headers = {
            
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
            "Content-Type": "application/json",
        }
        payload = {"to": destination, "subject": message.subject, "body": message.body}

        try:
            response = httpx.post(
                url, json=payload, headers=headers, timeout=settings.NOTIFICATION_PROVIDER_TIMEOUT
            )
        except httpx.TimeoutException as exc:
            raise TransientProviderError(f"Email provider timed out: {exc}") from exc
        except httpx.HTTPError as exc:
            raise TransientProviderError(f"Email provider network error: {exc}") from exc

        if response.status_code >= 400:
            raise _classify_http_status(response.status_code, response.text)




class ConsoleProvider:
    
    def __init__(self, channel: NotificationChannel):
        self.channel = channel

    def send(self, destination: str, message: RenderedMessage) -> None:
        logger.info(
            "[%s] to=%s subject=%s body=%s",
            self.channel.value, destination, message.subject, message.body,
        )


class MemoryProvider:
    

    def __init__(self, channel: NotificationChannel):
        self.channel = channel
        self.sent: list[tuple[str, RenderedMessage]] = []

    def send(self, destination: str, message: RenderedMessage) -> None:
        self.sent.append((destination, message))



_registry: dict[NotificationChannel, NotificationProvider] = {}


def _build_default(channel: NotificationChannel) -> NotificationProvider:
    backend = (
        settings.NOTIFICATION_EMAIL_BACKEND
        if channel is NotificationChannel.EMAIL
        else settings.NOTIFICATION_SMS_BACKEND
    ).lower()

    if backend == "console":
        return ConsoleProvider(channel)
    if backend == "memory":
        return MemoryProvider(channel)
    return SupabaseEmailProvider() if channel is NotificationChannel.EMAIL else ()


def get_provider(channel: NotificationChannel) -> NotificationProvider:
    if channel not in _registry:
        _registry[channel] = _build_default(channel)
    return _registry[channel]


def set_provider(channel: NotificationChannel, provider: NotificationProvider) -> None:
    _registry[channel] = provider


def reset_providers() -> None:
    _registry.clear()
