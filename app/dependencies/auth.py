import uuid

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import decode_supabase_access_token
from app.db.database import get_db
from app.models.enums import UserRole
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
   
    if credentials is None:
        raise UnauthorizedError("Missing bearer token.")

    decoded = decode_supabase_access_token(credentials.credentials)

    try:
        user_id = uuid.UUID(decoded.sub)
    except ValueError as exc:
        raise UnauthorizedError("Malformed subject claim in access token.") from exc

    user = db.get(User, user_id)
    if user is None:
        raise UnauthorizedError(
            
            "User not found."
        )
    return user


def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User | None:
  
    if credentials is None:
        return None

    decoded = decode_supabase_access_token(credentials.credentials)
    try:
        user_id = uuid.UUID(decoded.sub)
    except ValueError:
        return None

    return db.get(User, user_id)


def require_role(*allowed_roles: UserRole):
    def _dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise ForbiddenError(f"This action requires role(s): {', '.join(r.value for r in allowed_roles)}.")
        return current_user

    return _dependency


require_client = require_role(UserRole.CLIENT)
require_freelancer = require_role(UserRole.FREELANCER)
