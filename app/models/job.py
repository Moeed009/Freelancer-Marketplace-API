import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from app.db.base import Base
from app.models.enums import JobStatus, RateType


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        Index("ix_jobs_status_created_at", "status", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    title: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    rate_type: Mapped[RateType] = mapped_column(Enum(RateType, name="rate_type"), nullable=False)
    budget_min: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    budget_max: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="job_status"), default=JobStatus.DRAFT, nullable=False, index=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    published_at: Mapped[datetime | None] = mapped_column(
    DateTime(timezone=True), nullable=True
)

    closed_at: Mapped[datetime | None] = mapped_column(
    DateTime(timezone=True), nullable=True
)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    client = relationship("User", back_populates="jobs_posted", foreign_keys=[client_id])
    job_skills = relationship("JobSkill", back_populates="job", cascade="all, delete-orphan")
    proposals = relationship("Proposal", back_populates="job", cascade="all, delete-orphan")
    contract = relationship("Contract", back_populates="job", uselist=False)
