from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.file_attachment import FileAttachment, FileResourceType


def create(
    db: Session,
    *,
    owner_id: UUID,
    resource_type: FileResourceType,
    resource_id: UUID,
    original_filename: str,
    storage_path: str,
    mime_type: str,
    size: int,
) -> FileAttachment:
    file_attachment = FileAttachment(
        owner_id=owner_id,
        resource_type=resource_type,
        resource_id=resource_id,
        original_filename=original_filename,
        storage_path=storage_path,
        mime_type=mime_type,
        size=size,
    )

    db.add(file_attachment)
    db.flush()

    return file_attachment


def get_by_id(
    db: Session,
    file_id: UUID,
) -> FileAttachment | None:
    return db.get(FileAttachment, file_id)


def list_by_owner(
    db: Session,
    *,
    owner_id: UUID,
) -> list[FileAttachment]:
    statement = (
        select(FileAttachment)
        .where(
            FileAttachment.owner_id == owner_id,
        )
        .order_by(FileAttachment.created_at.desc())
    )

    return list(db.scalars(statement).all())

def delete(
    db: Session,
    file_attachment: FileAttachment,
) -> None:
    db.delete(file_attachment)
    db.flush()