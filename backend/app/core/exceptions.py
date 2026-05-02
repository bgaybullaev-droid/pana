"""Custom exceptions for RealEstate."""

from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status


class RealEstateException(HTTPException):
    """Base exception for RealEstate."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: Optional[List[Dict[str, Any]]] = None,
    ):
        self.code = code
        self.message = message
        self.details = details or []
        super().__init__(
            status_code=status_code,
            detail={
                "error": {
                    "code": code,
                    "message": message,
                    "details": self.details,
                }
            },
        )


class NotFoundException(RealEstateException):
    """Resource not found exception."""

    def __init__(
        self,
        resource: str = "Resource",
        resource_id: Optional[str] = None,
    ):
        message = f"{resource} not found"
        if resource_id:
            message = f"{resource} with ID '{resource_id}' not found"
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            code="NOT_FOUND",
            message=message,
        )


class UnauthorizedException(RealEstateException):
    """Authentication required exception."""

    def __init__(self, message: str = "Authentication required"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="UNAUTHORIZED",
            message=message,
        )


class ForbiddenException(RealEstateException):
    """Access forbidden exception."""

    def __init__(self, message: str = "Access forbidden"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            code="FORBIDDEN",
            message=message,
        )


class ValidationException(RealEstateException):
    """Validation error exception."""

    def __init__(
        self,
        message: str = "Validation error",
        details: Optional[List[Dict[str, Any]]] = None,
    ):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="VALIDATION_ERROR",
            message=message,
            details=details,
        )


class RateLimitException(RealEstateException):
    """Rate limit exceeded exception."""

    def __init__(self, message: str = "Too many requests"):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            code="RATE_LIMIT_EXCEEDED",
            message=message,
        )


class ConflictException(RealEstateException):
    """Resource conflict exception."""

    def __init__(self, message: str = "Resource already exists"):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            code="CONFLICT",
            message=message,
        )


class BadRequestException(RealEstateException):
    """Bad request exception."""

    def __init__(
        self,
        message: str = "Bad request",
        details: Optional[List[Dict[str, Any]]] = None,
    ):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="BAD_REQUEST",
            message=message,
            details=details,
        )


class ServiceUnavailableException(RealEstateException):
    """Service unavailable exception."""

    def __init__(self, message: str = "Service temporarily unavailable"):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="SERVICE_UNAVAILABLE",
            message=message,
        )


class PhoneRequiredException(RealEstateException):
    """
    Raised by /auth/telegram when the user has no phone on file AND no recent
    contact-share payload in Redis. The Mini App frontend reads the
    PHONE_REQUIRED code and renders the PhoneGate screen to drive the
    requestContact() flow.
    """

    def __init__(
        self,
        message: str = "To use this service, you must share your phone number.",
    ):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="PHONE_REQUIRED",
            message=message,
        )
