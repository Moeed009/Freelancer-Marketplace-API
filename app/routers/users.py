import uuid

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationAppError
from app.core.supabase_storage import upload_avatar
from app.db.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.repositories import user_repository
from app.schemas.user import UserOut, UserPublicOut, UserUpdateRequest

router = APIRouter(prefix="", tags=["Users"])

ALLOWED_AVATAR_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_AVATAR_SIZE = 5 * 1024 * 1024  


@router.get("/Account_Info", response_model=UserOut, summary="Get the authenticated user's own account")
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/Update_Profile", response_model=UserOut, summary="Update the authenticated user's own profile")
def update_me(
    payload: UserUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return user_repository.update_profile_fields(db, current_user, full_name=payload.full_name)


@router.delete("/Delete_Account", status_code=204, summary="Delete the authenticated user's own account")
def delete_me(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user_repository.delete(db, current_user)


@router.post(
    "/Upload_Pic",
    response_model=UserOut,
    summary="Upload or replace my profile picture",
)
async def upload_my_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if file.content_type not in ALLOWED_AVATAR_TYPES:
        raise ValidationAppError("Only JPEG, PNG, or WEBP images are allowed.")

    file_bytes = await file.read()
    if len(file_bytes) > MAX_AVATAR_SIZE:
        raise ValidationAppError("File size must not exceed 5MB.")

    avatar_url = await upload_avatar(file_bytes, file.content_type, current_user.id)
    user = user_repository.set_avatar(db, current_user, avatar_url)
    return user


