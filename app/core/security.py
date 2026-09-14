from datetime import datetime, timezone

import httpx
from jose import JWTError, jwt

from app.core.config import settings
from app.core.exceptions import UnauthorizedError

_jwks_cache: dict | None = None


class DecodedToken:
    def __init__(self, payload: dict):
        self.payload = payload
        self.sub: str = payload["sub"]
        self.email: str | None = payload.get("email")
        self.exp: int = payload["exp"]


def _get_jwks() -> dict:
    global _jwks_cache
    if _jwks_cache is None:
        url = f"{settings.SUPABASE_URL}/auth/v1/.well-known/jwks.json"
        response = httpx.get(url, timeout=10.0)
        response.raise_for_status()
        _jwks_cache = response.json()
    return _jwks_cache


def decode_supabase_access_token(token: str) -> DecodedToken:
    try:
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")

        jwks = _get_jwks()
        key = next((k for k in jwks["keys"] if k["kid"] == kid), None)
        if key is None:
            
            global _jwks_cache
            _jwks_cache = None
            jwks = _get_jwks()
            key = next((k for k in jwks["keys"] if k["kid"] == kid), None)
        if key is None:
            raise UnauthorizedError("Unable to find matching signing key.")

        payload = jwt.decode(
            token,
            key,
            algorithms=[unverified_header.get("alg", "ES256")],
            audience="authenticated",
        )
    except JWTError as exc:
        raise UnauthorizedError("Invalid or expired access token.") from exc

    exp = payload.get("exp")
    if exp is None or datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(timezone.utc):
        raise UnauthorizedError("Access token has expired.")

    if "sub" not in payload:
        raise UnauthorizedError("Malformed access token.")

    return DecodedToken(payload)