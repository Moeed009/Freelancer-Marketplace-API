from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.file_attachment import (
    FileAttachmentStatus,
    FileResourceType,
)


class FileAttachmentOut(BaseModel):
    id: UUID
    owner_id: UUID
    resource_type: FileResourceType
    resource_id: UUID
    original_filename: str
    storage_path: str
    mime_type: str
    size: int
    status: FileAttachmentStatus
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FileDownloadOut(BaseModel):
    file_id: UUID
    filename: str
    mime_type: str
    expires_in: int
    download_url: str