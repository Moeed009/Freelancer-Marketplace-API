import uuid

from sqlalchemy.orm import Session

from app.core import supabase_client
from app.core.exceptions import ConflictError, UnauthorizedError
from app.models.enums import UserRole
from app.repositories import user_repository


async def register(db: Session, *, email: str, password: str, full_name: str | None, role: UserRole) -> dict:
    if user_repository.get_by_email(db, email):
        raise ConflictError("A user with this email is already registered.")

    supabase_result = await supabase_client.sign_up(
        email=email, password=password, user_metadata={"role": role.value, "full_name": full_name}
    )

    supabase_user = supabase_result.get("user") or supabase_result
    user_id = uuid.UUID(supabase_user["id"])

    local_user = user_repository.create(db, user_id=user_id, email=email, role=role, full_name=full_name)

    
    session = supabase_result.get("session")
    if session is None and "access_token" in supabase_result:
        session = {
            "access_token": supabase_result["access_token"],
            "refresh_token": supabase_result["refresh_token"],
            "expires_in": supabase_result.get("expires_in", 3600),
        }

    return {"local_user": local_user, "session": session}


async def login(db: Session, *, email: str, password: str) -> dict:
    session = await supabase_client.sign_in_with_password(email, password)
    local_user = user_repository.get_by_email(db, email)
    if local_user is None:
        raise UnauthorizedError("Account exists in the auth provider but not in the application database.")
    return {"local_user": local_user, "session": session}


async def refresh(refresh_token: str) -> dict:
    return await supabase_client.refresh_session(refresh_token)


_revoked_tokens: set[str] = set()


async def logout(access_token: str) -> None:
    _revoked_tokens.add(access_token)

    await supabase_client.sign_out(access_token)


def is_token_revoked(access_token: str) -> bool:
    return access_token in _revoked_tokens

