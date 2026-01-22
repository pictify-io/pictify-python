"""Custom exceptions for the Pictify SDK."""

from typing import Any, Dict, Optional


class PictifyError(Exception):
    """Base exception for all Pictify errors."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_body: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response_body = response_body

    def __str__(self) -> str:
        if self.status_code:
            return f"[{self.status_code}] {self.message}"
        return self.message


class AuthenticationError(PictifyError):
    """Raised when API key is invalid or missing."""

    def __init__(
        self,
        message: str = "Invalid or missing API key",
        status_code: int = 401,
        response_body: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message, status_code, response_body)


class TemplateNotFoundError(PictifyError):
    """Raised when the specified template does not exist."""

    def __init__(
        self,
        template_id: str,
        status_code: int = 404,
        response_body: Optional[Dict[str, Any]] = None,
    ) -> None:
        message = f"Template not found: {template_id}"
        super().__init__(message, status_code, response_body)
        self.template_id = template_id


class RateLimitError(PictifyError):
    """Raised when rate limit is exceeded."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        status_code: int = 429,
        response_body: Optional[Dict[str, Any]] = None,
        retry_after: Optional[int] = None,
    ) -> None:
        super().__init__(message, status_code, response_body)
        self.retry_after = retry_after


class QuotaExceededError(PictifyError):
    """Raised when account quota is exceeded."""

    def __init__(
        self,
        message: str = "Account quota exceeded",
        status_code: int = 402,
        response_body: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message, status_code, response_body)


class RenderError(PictifyError):
    """Raised when rendering fails."""

    def __init__(
        self,
        message: str = "Render failed",
        status_code: int = 500,
        response_body: Optional[Dict[str, Any]] = None,
        render_id: Optional[str] = None,
    ) -> None:
        super().__init__(message, status_code, response_body)
        self.render_id = render_id


class NetworkError(PictifyError):
    """Raised when a network error occurs."""

    def __init__(
        self,
        message: str = "Network error occurred",
        original_error: Optional[Exception] = None,
    ) -> None:
        super().__init__(message)
        self.original_error = original_error


class TimeoutError(PictifyError):
    """Raised when a request times out."""

    def __init__(
        self,
        message: str = "Request timed out",
        timeout: Optional[float] = None,
    ) -> None:
        super().__init__(message)
        self.timeout = timeout


def create_error_from_response(
    status_code: int,
    response_body: Optional[Dict[str, Any]] = None,
) -> PictifyError:
    """Create appropriate error instance from HTTP response."""
    body = response_body or {}
    message = body.get("message", body.get("error", "Unknown error"))

    if status_code == 401:
        return AuthenticationError(message, status_code, body)
    elif status_code == 402:
        return QuotaExceededError(message, status_code, body)
    elif status_code == 404:
        template_id = body.get("template_id", "unknown")
        return TemplateNotFoundError(template_id, status_code, body)
    elif status_code == 429:
        retry_after = body.get("retry_after")
        return RateLimitError(message, status_code, body, retry_after)
    elif status_code >= 500:
        render_id = body.get("render_id")
        return RenderError(message, status_code, body, render_id)
    else:
        return PictifyError(message, status_code, body)
