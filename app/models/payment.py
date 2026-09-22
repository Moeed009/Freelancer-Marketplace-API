from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.enums import PaymentStatus
from app.models.milestone import Milestone
from app.models.user import User
from app.db.base import Base


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )

    milestone_id: Mapped[UUID] = mapped_column(
        ForeignKey("milestones.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    client_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    freelancer_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="USD",
    )

    status: Mapped[PaymentStatus] = mapped_column(
        nullable=False,
        default=PaymentStatus.PENDING,
    )

    stripe_checkout_session_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        unique=True,
    )

    stripe_payment_intent_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        unique=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    milestone: Mapped["Milestone"] = relationship(
        "Milestone",
    )

    client: Mapped["User"] = relationship(
        "User",
        foreign_keys=[client_id],
    )

    freelancer: Mapped["User"] = relationship(
        "User",
        foreign_keys=[freelancer_id],
    )