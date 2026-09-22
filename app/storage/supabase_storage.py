from typing import BinaryIO

from supabase import Client, create_client

from app.core.config import settings


class SupabaseStorage:
    def __init__(self) -> None:
        self.client: Client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_ROLE_KEY,
        )
        self.bucket = "private-files"

    def upload(
        self,
        file: BinaryIO,
        path: str,
        content_type: str,
    ) -> None:
        file.seek(0)
        file_data = file.read()

        self.client.storage.from_(self.bucket).upload(
            path=path,
            file=file_data,
            file_options={
                "content-type": content_type,
                "upsert": False,
            },
        )

    def delete(self, path: str) -> None:
        self.client.storage.from_(self.bucket).remove([path])

    def create_signed_url(
        self,
        path: str,
        expires_in: int = 600,
    ) -> str:
        response = self.client.storage.from_(self.bucket).create_signed_url(
            path,
            expires_in,
        )

        return response["signedURL"]