"""
Sumatic Modern IoT - Custom Exceptions
Application-specific exception classes.
"""
from typing import Any, Optional


class AppException(Exception):
    """
    Base application exception.
    All custom exceptions inherit from this class.
    """

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class UnauthorizedException(AppException):
    """
    Raised when authentication is required but not provided.
    HTTP 401 Unauthorized
    """

    def __init__(
        self,
        message: str = "Could not validate credentials",
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message, status_code=401, details=details)


class ForbiddenException(AppException):
    """
    Raised when user lacks permission for an action.
    HTTP 403 Forbidden
    """

    def __init__(
        self,
        message: str = "You don't have permission to perform this action",
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message, status_code=403, details=details)


class NotFoundException(AppException):
    """
    Raised when a requested resource is not found.
    HTTP 404 Not Found
    """

    def __init__(
        self,
        message: str = "Resource not found",
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message, status_code=404, details=details)


class BadRequestException(AppException):
    """
    Raised when the request is malformed or invalid.
    HTTP 400 Bad Request
    """

    def __init__(
        self,
        message: str = "Bad request",
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message, status_code=400, details=details)


class ConflictException(AppException):
    """
    Raised when a request conflicts with existing data.
    HTTP 409 Conflict
    """

    def __init__(
        self,
        message: str = "Resource already exists",
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message, status_code=409, details=details)


class ValidationException(AppException):
    """
    Raised when request validation fails.
    HTTP 422 Unprocessable Entity
    """

    def __init__(
        self,
        message: str = "Validation error",
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message, status_code=422, details=details)


class RateLimitException(AppException):
    """
    Raised when rate limit is exceeded.
    HTTP 429 Too Many Requests
    """

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message, status_code=429, details=details)


class ServiceUnavailableException(AppException):
    """
    Raised when a service is temporarily unavailable.
    HTTP 503 Service Unavailable
    """

    def __init__(
        self,
        message: str = "Service temporarily unavailable",
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message, status_code=503, details=details)
