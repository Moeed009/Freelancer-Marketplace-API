import uuid

import httpx

from app.core.config import settings
from app.core.exceptions import AppError


async def upload_file(file_bytes: bytes, content_type: str, bucket: str, folder: str) -> str:
    file_ext = content_type.split("/")[-1]
    path = f"{folder}/{uuid.uuid4()}.{file_ext}"

    url = f"{settings.SUPABASE_URL}/storage/v1/object/{bucket}/{path}"
    headers = {
        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": content_type,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, content=file_bytes, headers=headers)

    if response.status_code >= 400:
        raise AppError(f"Failed to upload file: {response.text}", code="upload_failed", status_code=500)

    return f"{settings.SUPABASE_URL}/storage/v1/object/public/{bucket}/{path}"


async def upload_avatar(file_bytes: bytes, content_type: str, user_id: uuid.UUID) -> str:
    return await upload_file(file_bytes, content_type, bucket="avatars", folder=str(user_id))


async def upload_deliverable(file_bytes: bytes, content_type: str, milestone_id: uuid.UUID) -> str:
    return await upload_file(file_bytes, content_type, bucket="deliverables", folder=str(milestone_id))