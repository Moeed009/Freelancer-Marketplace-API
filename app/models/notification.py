import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import DeliveryStatus, NotificationCategory, NotificationChannel


class NotificationEvent(Base):
  

    __tablename__ = "notification_events"
    __table_args__ = (
       
        UniqueConstraint("idempotency_key", name="uq_notification_events_idempotency_key"),
        Index("ix_notification_events_recipient_created_at", "recipient_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    category: Mapped[NotificationCategory] = mapped_column(
        Enum(NotificationCategory, name="notification_category"), nullable=False, index=True
    )

    recipient_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    recipient = relationship("User", foreign_keys=[recipient_id])
    deliveries = relationship(
        "NotificationDelivery",
        back_populates="event",
        cascade="all, delete-orphan",
        order_by="NotificationDelivery.channel",
    )


class NotificationDelivery(Base):
   
    __tablename__ = "notification_deliveries"
    __table_args__ = (
       
        UniqueConstraint("event_id", "channel", name="uq_notification_deliveries_event_channel"),
       
        Index("ix_notification_deliveries_status_next_attempt_at", "status", "next_attempt_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("notification_events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    channel: Mapped[NotificationChannel] = mapped_column(
        Enum(NotificationChannel, name="notification_channel"), nullable=False
    )

    
    destination_masked: Mapped[str | None] = mapped_column(String(255), nullable=True)

    status: Mapped[DeliveryStatus] = mapped_column(
        Enum(DeliveryStatus, name="notification_delivery_status"),
        default=DeliveryStatus.PENDING,
        nullable=False,
        index=True,
    )

    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3, nullable=False)

    
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    event = relationship("NotificationEvent", back_populates="deliveries")


class NotificationPreference(Base):
    
    __tablename__ = "notification_preferences"
    __table_args__ = (
        UniqueConstraint("user_id", "category", "channel", name="uq_notification_pref_user_category_channel"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category: Mapped[NotificationCategory] = mapped_column(
        Enum(NotificationCategory, name="notification_category"), nullable=False
    )
    channel: Mapped[NotificationChannel] = mapped_column(
        Enum(NotificationChannel, name="notification_channel"), nullable=False
    )
    enabled: Mapped[bool] = mapped_column(default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user = relationship("User", foreign_keys=[user_id])
