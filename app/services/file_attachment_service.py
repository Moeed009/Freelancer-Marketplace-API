import uuid
from pathlib import Path
from typing import BinaryIO

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.models.contract import Contract
from app.models.file_attachment import (
    FileAttachment,
    FileAttachmentStatus,
    FileResourceType,
)
from app.models.job import Job
from app.models.milestone import Milestone
from app.models.proposal import Proposal
from app.models.user import User
from app.repositories import file_attachment_repository
from app.storage.supabase_storage import SupabaseStorage


MAX_FILE_SIZE = 10 * 1024 * 1024

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "image/png",
    "image/jpeg",
    "image/webp",
}


class FileAttachmentService:
    def __init__(self) -> None:
        self.storage = SupabaseStorage()

    def _validate_file(self, file: UploadFile) -> None:
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Filename is required",
            )

        if file.content_type not in ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File type is not allowed",
            )

    def _check_file_size(self, file: BinaryIO) -> int:
        file.seek(0, 2)
        size = file.tell()
        file.seek(0)

        if size == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Empty files are not allowed",
            )

        if size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="File size cannot exceed 10 MB",
            )

        return size

    def _authorize_resource(
        self,
        db: Session,
        current_user: User,
        resource_type: FileResourceType,
        resource_id: uuid.UUID,
    ) -> None:
        if resource_type == FileResourceType.PROFILE:
            if resource_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You are not authorized to access this profile",
                )
            return

        if resource_type == FileResourceType.JOB:
            job = db.get(Job, resource_id)

            if not job:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Job not found",
                )

            if job.client_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You are not authorized to access this job",
                )

            return

        if resource_type == FileResourceType.PROPOSAL:
            proposal = db.get(Proposal, resource_id)

            if not proposal:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Proposal not found",
                )

            if (
                proposal.freelancer_id != current_user.id
                and proposal.job.client_id != current_user.id
            ):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You are not authorized to access this proposal",
                )

            return

        if resource_type == FileResourceType.CONTRACT:
            contract = db.get(Contract, resource_id)

            if not contract:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Contract not found",
                )

            if (
                contract.client_id != current_user.id
                and contract.freelancer_id != current_user.id
            ):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You are not authorized to access this contract",
                )

            return

        if resource_type == FileResourceType.MILESTONE:
            milestone = db.get(Milestone, resource_id)

            if not milestone:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Milestone not found",
                )

            contract = milestone.contract

            if not contract:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Contract not found",
                )

            if (
                contract.client_id != current_user.id
                and contract.freelancer_id != current_user.id
            ):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You are not authorized to access this milestone",
                )

            return

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid resource type",
        )

    def upload(
        self,
        db: Session,
        current_user: User,
        file: UploadFile,
        resource_type: FileResourceType,
        resource_id: uuid.UUID,
    ) -> FileAttachment:
        self._validate_file(file)

        self._authorize_resource(
            db,
            current_user,
            resource_type,
            resource_id,
        )

        size = self._check_file_size(file.file)

        extension = Path(file.filename).suffix.lower()
        file_id = uuid.uuid4()

        storage_path = (
            f"{current_user.id}/"
            f"{resource_type.value.lower()}/"
            f"{resource_id}/"
            f"{file_id}{extension}"
        )

        attachment = file_attachment_repository.create(
            db,
            owner_id=current_user.id,
            resource_type=resource_type,
            resource_id=resource_id,
            original_filename=file.filename,
            storage_path=storage_path,
            mime_type=file.content_type,
            size=size,
        )

        db.commit()
        db.refresh(attachment)

        try:
            self.storage.upload(
                file=file.file,
                path=storage_path,
                content_type=file.content_type,
            )
        except Exception as exc:
            print(
                "SUPABASE STORAGE UPLOAD ERROR:",
                repr(exc),
            )

            db.delete(attachment)
            db.commit()

            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="File upload failed",
            )

        attachment.status = FileAttachmentStatus.CONFIRMED

        db.commit()
        db.refresh(attachment)

        return attachment

    def list_my_files(
        self,
        db: Session,
        current_user: User,
    ) -> list[FileAttachment]:
        files = file_attachment_repository.list_by_owner(
            db,
            owner_id=current_user.id,
        )

        return [
            file
            for file in files
            if file.status == FileAttachmentStatus.CONFIRMED
        ]

    def get_file_for_user(
        self,
        db: Session,
        current_user: User,
        file_id: uuid.UUID,
    ) -> FileAttachment:
        attachment = file_attachment_repository.get_by_id(
            db,
            file_id,
        )

        if not attachment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found",
            )

        if attachment.status != FileAttachmentStatus.CONFIRMED:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File is not available",
            )

        self._authorize_resource(db,current_user,attachment.resource_type,attachment.resource_id,)
        return attachment

    def create_download_url(
        self,
        db: Session,
        current_user: User,
        file_id: uuid.UUID,
    ) -> tuple[FileAttachment, str]:
        attachment = self.get_file_for_user(
            db,
            current_user,
            file_id,
        )

        try:signed_url = self.storage.create_signed_url(attachment.storage_path,expires_in=600,)
        except Exception as exc:
            print("SUPABASE SIGNED URL ERROR:", repr(exc), )
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Unable to generate download URL", )

        return attachment, signed_url

    def delete(
        self,
        db: Session,
        current_user: User,
        file_id: uuid.UUID,
    ) -> None:
        attachment = self.get_file_for_user(
            db,
            current_user,
            file_id,
        )

        try:
            self.storage.delete(
                attachment.storage_path,
            )
        except Exception as exc:
            print(
                "SUPABASE STORAGE DELETE ERROR:",
                repr(exc),
            )

            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Unable to delete file from storage",
            )

        file_attachment_repository.delete(
            db,
            attachment,
        )

        db.commit()