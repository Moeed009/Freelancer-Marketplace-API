import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

class FileResourceType(str, enum.Enum):
    PROFILE = "PROFILE"
    JOB = "JOB"
    PROPOSAL = "PROPOSAL"
    CONTRACT = "CONTRACT"
    MILESTONE = "MILESTONE"


class FileAttachmentStatus(str, enum.Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"


class FileAttachment(Base):
    __tablename__ = "file_attachments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    resource_type: Mapped[FileResourceType] = mapped_column(
        Enum(FileResourceType, name="file_resource_type"),
        nullable=False,
    )

    resource_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )

    original_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    storage_path: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        unique=True,
    )

    mime_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    size: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    status: Mapped[FileAttachmentStatus] = mapped_column(
        Enum(FileAttachmentStatus, name="file_attachment_status"),
        nullable=False,
        default=FileAttachmentStatus.PENDING,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


Index(
    "ix_file_attachments_owner_id",
    FileAttachment.owner_id,
)

Index(
    "ix_file_attachments_resource",
    FileAttachment.resource_type,
    FileAttachment.resource_id,
)

Index(
    "ix_file_attachments_status",
    FileAttachment.status,
)