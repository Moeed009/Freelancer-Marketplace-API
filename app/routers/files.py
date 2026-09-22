import uuid

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.dependencies.auth import get_current_user
from app.models.file_attachment import FileResourceType
from app.models.user import User
from app.schemas.file_attachment import FileAttachmentOut, FileDownloadOut
from app.services.file_attachment_service import FileAttachmentService


router = APIRouter(tags=["Files"])

file_service = FileAttachmentService()


@router.post(
    "/Upload_file",
    response_model=FileAttachmentOut,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a private file",
)
def upload_file(
    resource_type: FileResourceType = Query(...),
    resource_id: uuid.UUID = Query(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return file_service.upload(
        db,
        current_user,
        file,
        resource_type,
        resource_id,
    )


@router.get(
    "/List_files",
    response_model=list[FileAttachmentOut],
    summary="List files uploaded by the authenticated user",
)
def list_files(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return file_service.list_my_files(
        db,
        current_user,
    )


@router.get(
    "/Download_file",
    response_model=FileDownloadOut,
    summary="Generate a temporary signed download URL",
)
def download_file(
    file_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    attachment, signed_url = file_service.create_download_url(
        db,
        current_user,
        file_id,
    )

    return FileDownloadOut(
        file_id=attachment.id,
        filename=attachment.original_filename,
        mime_type=attachment.mime_type,
        expires_in=600,
        download_url=signed_url,
    )


@router.delete(
    "/Delete_file",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a private file",
)
def delete_file(
    file_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    file_service.delete(
        db,
        current_user,
        file_id,
    )