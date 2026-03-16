"""Tests for Pictify error classes."""

import pytest

from pictify.errors import (
    PictifyError,
    AuthenticationError,
    TemplateNotFoundError,
    RateLimitError,
    QuotaExceededError,
    RenderError,
    NetworkError,
    TimeoutError,
    create_error_from_response,
)


class TestPictifyError:
    """Tests for base PictifyError class."""

    def test_creates_error_with_message(self):
        error = PictifyError("Test error")
        assert str(error) == "Test error"
        assert error.message == "Test error"

    def test_creates_error_with_status_code(self):
        error = PictifyError("Test error", status_code=500)
        assert error.status_code == 500
        assert str(error) == "[500] Test error"

    def test_creates_error_with_response_body(self):
        body = {"field": "value"}
        error = PictifyError("Test", response_body=body)
        assert error.response_body == body

    def test_inherits_from_exception(self):
        error = PictifyError("Test")
        assert isinstance(error, Exception)


class TestAuthenticationError:
    """Tests for AuthenticationError class."""

    def test_default_message(self):
        error = AuthenticationError()
        assert error.message == "Invalid or missing API key"
        assert error.status_code == 401

    def test_custom_message(self):
        error = AuthenticationError("Custom auth error")
        assert error.message == "Custom auth error"

    def test_inherits_from_pictify_error(self):
        error = AuthenticationError()
        assert isinstance(error, PictifyError)


class TestTemplateNotFoundError:
    """Tests for TemplateNotFoundError class."""

    def test_creates_error_with_template_id(self):
        error = TemplateNotFoundError("tmpl_123")
        assert error.message == "Template not found: tmpl_123"
        assert error.template_id == "tmpl_123"
        assert error.status_code == 404

    def test_inherits_from_pictify_error(self):
        error = TemplateNotFoundError("tmpl_123")
        assert isinstance(error, PictifyError)


class TestRateLimitError:
    """Tests for RateLimitError class."""

    def test_default_values(self):
        error = RateLimitError()
        assert error.message == "Rate limit exceeded"
        assert error.status_code == 429
        assert error.retry_after is None

    def test_stores_retry_after(self):
        error = RateLimitError("Too many requests", retry_after=60)
        assert error.retry_after == 60


class TestQuotaExceededError:
    """Tests for QuotaExceededError class."""

    def test_default_message(self):
        error = QuotaExceededError()
        assert error.message == "Account quota exceeded"
        assert error.status_code == 402


class TestRenderError:
    """Tests for RenderError class."""

    def test_default_values(self):
        error = RenderError()
        assert error.message == "Render failed"
        assert error.status_code == 500
        assert error.render_id is None

    def test_stores_render_id(self):
        error = RenderError("Failed", render_id="render_123")
        assert error.render_id == "render_123"


class TestNetworkError:
    """Tests for NetworkError class."""

    def test_default_message(self):
        error = NetworkError()
        assert error.message == "Network error occurred"
        assert error.status_code is None

    def test_stores_original_error(self):
        original = Exception("Connection refused")
        error = NetworkError("Network failed", original_error=original)
        assert error.original_error == original


class TestTimeoutError:
    """Tests for TimeoutError class."""

    def test_default_message(self):
        error = TimeoutError()
        assert error.message == "Request timed out"
        assert error.timeout is None

    def test_stores_timeout_value(self):
        error = TimeoutError("Timeout after 30s", timeout=30.0)
        assert error.timeout == 30.0


class TestCreateErrorFromResponse:
    """Tests for create_error_from_response function."""

    def test_returns_authentication_error_for_401(self):
        error = create_error_from_response(401, {"message": "Invalid key"})
        assert isinstance(error, AuthenticationError)
        assert error.message == "Invalid key"

    def test_returns_quota_exceeded_for_402(self):
        error = create_error_from_response(402, {"message": "Quota exceeded"})
        assert isinstance(error, QuotaExceededError)
        assert error.message == "Quota exceeded"

    def test_returns_template_not_found_for_404(self):
        error = create_error_from_response(404, {"message": "Not found", "template_id": "tmpl_123"})
        assert isinstance(error, TemplateNotFoundError)
        assert error.template_id == "tmpl_123"

    def test_returns_rate_limit_error_for_429(self):
        error = create_error_from_response(429, {"message": "Too many requests", "retry_after": 60})
        assert isinstance(error, RateLimitError)
        assert error.retry_after == 60

    def test_returns_render_error_for_500(self):
        error = create_error_from_response(500, {"message": "Server error"})
        assert isinstance(error, RenderError)

    def test_returns_render_error_for_502(self):
        error = create_error_from_response(502, {"message": "Bad gateway"})
        assert isinstance(error, RenderError)

    def test_returns_render_error_for_503(self):
        error = create_error_from_response(503, {"message": "Unavailable"})
        assert isinstance(error, RenderError)

    def test_returns_render_error_for_504(self):
        error = create_error_from_response(504, {"message": "Gateway timeout"})
        assert isinstance(error, RenderError)

    def test_returns_generic_error_for_unknown_status(self):
        error = create_error_from_response(418, {"message": "I'm a teapot"})
        assert isinstance(error, PictifyError)
        assert not isinstance(error, (AuthenticationError, RenderError))

    def test_uses_default_message_when_none_provided(self):
        error = create_error_from_response(500, {})
        assert error.message == "Unknown error"

    def test_handles_error_field_as_message(self):
        error = create_error_from_response(500, {"error": "Something went wrong"})
        assert error.message == "Something went wrong"

    def test_handles_none_response_body(self):
        error = create_error_from_response(500, None)
        assert error.message == "Unknown error"
