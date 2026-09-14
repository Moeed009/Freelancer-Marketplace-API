import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import ProposalStatus


class Proposal(Base):
    __tablename__ = "proposals"
    __table_args__ = (
       
        UniqueConstraint("job_id", "freelancer_id", name="uq_proposal_job_freelancer"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    freelancer_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    cover_letter: Mapped[str] = mapped_column(Text, nullable=False)
    bid_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    estimated_duration_days: Mapped[int] = mapped_column(nullable=False)
    status: Mapped[ProposalStatus] = mapped_column(
        Enum(ProposalStatus, name="proposal_status"), default=ProposalStatus.PENDING, nullable=False, index=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    job = relationship("Job", back_populates="proposals")
    freelancer = relationship("User", back_populates="proposals", foreign_keys=[freelancer_id])
    contract = relationship("Contract", back_populates="proposal", uselist=False)
