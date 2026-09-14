from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.exceptions import UnauthorizedError
from app.db.database import get_db
from app.schemas.auth import (
    AuthUserOut,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
)
from app.services import auth_service

router = APIRouter(prefix="", tags=["Authentication"])
bearer_scheme = HTTPBearer(auto_error=True)

REFRESH_COOKIE_NAME = "refresh_token"
ACCESS_COOKIE_NAME = "access_token"
REFRESH_COOKIE_MAX_AGE = 60 * 60 * 24 * 30  


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str, expires_in: int) -> None:
    response.set_cookie(
        key=ACCESS_COOKIE_NAME,
        value=access_token,
        httponly=True,
        secure=False,      
        samesite="lax",
        max_age=expires_in,
        path="/",
    )
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=REFRESH_COOKIE_MAX_AGE,
        path="/",
    )


def _to_token_response(result: dict) -> TokenResponse:
    session = result["session"]
    local_user = result["local_user"]
    return TokenResponse(
        access_token=session["access_token"],
        expires_in=session.get("expires_in", 3600),
        user=AuthUserOut.model_validate(local_user),
    )


@router.post(
    "/Register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new account (role: CLIENT or FREELANCER)",
)
async def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    result = await auth_service.register(
        db,
        email=payload.email,
        password=payload.password,
        full_name=payload.full_name,
        role=payload.role,
    )
    return _to_token_response(result)


@router.post("/Login", response_model=TokenResponse, summary="Login with email + password")
async def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    result = await auth_service.login(db, email=payload.email, password=payload.password)
    session = result["session"]

    _set_auth_cookies(
        response,
        access_token=session["access_token"],
        refresh_token=session["refresh_token"],
        expires_in=session.get("expires_in", 3600),
    )

    return _to_token_response(result)


@router.post("/Refresh Token", summary="Exchange refresh cookie for a new access/refresh token pair (rotates both cookies)")
async def refresh(request: Request, response: Response):
    refresh_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if not refresh_token:
        raise UnauthorizedError("Missing refresh token.")

    session = await auth_service.refresh(refresh_token)

    _set_auth_cookies(
        response,
        access_token=session["access_token"],
        refresh_token=session["refresh_token"],
        expires_in=session.get("expires_in", 3600),
    )

    return {
        "access_token": session["access_token"],
        "token_type": "bearer",
        "expires_in": session.get("expires_in", 3600),
    }


@router.post("/Logout", status_code=status.HTTP_204_NO_CONTENT, summary="Revoke the current session's refresh token(s)")
async def logout(
    response: Response,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
):
    await auth_service.logout(credentials.credentials)
    response.delete_cookie(key=REFRESH_COOKIE_NAME, path="/")
    response.delete_cookie(key=ACCESS_COOKIE_NAME, path="/")