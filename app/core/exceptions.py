from fastapi import status


class AppError(Exception):
    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "bad_request"

    def __init__(self, message: str, code: str | None = None, status_code: int | None = None):
        self.message = message
        if code:
            self.code = code
        if status_code:
            self.status_code = status_code
        super().__init__(message)


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "not_found"


class ConflictError(AppError):
    status_code = status.HTTP_409_CONFLICT
    code = "conflict"


class ValidationAppError(AppError):
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    code = "validation_error"


class UnauthorizedError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "unauthorized"


class ForbiddenError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "forbidden"


class AuthProviderError(AppError):
    
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "auth_provider_error"


class EmailNotConfirmedError(AppError):
    
    status_code = status.HTTP_403_FORBIDDEN
    code = "email_not_confirmed"

    def __init__(self, message: str = "Registration successful. Please confirm your email before logging in."):
        super().__init__(message)