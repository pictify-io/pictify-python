"""Custom exceptions for the Pictify SDK.

There is no unified error envelope across the Pictify API: image/GIF endpoints
return ``{"error", "code"}`` while template/CRUD endpoints return ``{"message"}``
or ``{"message", "errors"}``. The SDK reads both keys.

Error message precedence: ``body["error"] or body["message"] or "; ".join(body["errors"])
or status_text`` — the joined ``errors`` list is the video compile gate's 422
shape, where the strings are the fix instructions.

Status mapping (mirrors the Node SDK reference):
    - 401 -> AuthenticationError
    - 402 -> QuotaExceededError
    - 404 -> TemplateNotFoundError
    - 422 -> RenderError (validation; includes ``errors``)
    - 429 -> QuotaExceededError when ``code == "quota_exceeded"``, else RateLimitError
    - other 4xx -> RenderError
    - 5xx -> ServerError
"""

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
    """Raised when the API key is invalid or missing (HTTP 401)."""

    def __init__(
        self,
        message: str = "Invalid or missing API key",
        status_code: int = 401,
        response_body: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message, status_code, response_body)


class TemplateNotFoundError(PictifyError):
    """Raised when the specified template is not found (HTTP 404)."""

    def __init__(
        self,
        message: str = "Template not found",
        status_code: int = 404,
        response_body: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message, status_code, response_body)


class RateLimitError(PictifyError):
    """Raised when the rate limit is exceeded (HTTP 429 without a quota code)."""

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
    """Raised when the render quota is exceeded (HTTP 402, or 429 with a quota code)."""

    def __init__(
        self,
        message: str = "Render quota exceeded",
        status_code: int = 402,
        response_body: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message, status_code, response_body)


class RenderError(PictifyError):
    """Raised when a render or input validation fails (HTTP 422 and non-quota 4xx).

    Carries field-level ``errors`` from the API when present (422 responses).
    """

    def __init__(
        self,
        message: str = "Render failed",
        status_code: int = 422,
        response_body: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message, status_code, response_body)
        self.errors = (response_body or {}).get("errors")


class ServerError(PictifyError):
    """Raised when the server fails (HTTP 5xx)."""

    def __init__(
        self,
        message: str = "Server error",
        status_code: int = 500,
        response_body: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message, status_code, response_body)


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
    """Map an HTTP error response to a typed :class:`PictifyError`.

    Message precedence: ``body["error"] or body["message"] or "..."``.
    """
    body = response_body or {}
    # The video compile gate returns 422 {"errors": ["..."]} with no
    # message/error key — those strings ARE the fix instructions, so they
    # join into the message rather than leaving a generic fallback.
    errors = body.get("errors")
    joined_errors = (
        "; ".join(errors)
        if isinstance(errors, list) and errors and all(isinstance(e, str) for e in errors)
        else None
    )
    message = (
        body.get("error") or body.get("message") or joined_errors or "An unexpected error occurred"
    )

    if status_code == 401:
        return AuthenticationError(message, status_code, body)
    if status_code == 402:
        return QuotaExceededError(message, status_code, body)
    if status_code == 404:
        return TemplateNotFoundError(message, status_code, body)
    if status_code == 422:
        return RenderError(message, status_code, body)
    if status_code == 429:
        if body.get("code") == "quota_exceeded":
            return QuotaExceededError(message, status_code, body)
        return RateLimitError(message, status_code, body, body.get("retry_after"))
    if status_code >= 500:
        return ServerError(message, status_code, body)
    if status_code >= 400:
        return RenderError(message, status_code, body)
    return PictifyError(message, status_code, body)
