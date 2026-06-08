"""Unit tests for Pictify error classes and the response -> error mapping."""

from pictify.errors import (
    AuthenticationError,
    NetworkError,
    PictifyError,
    QuotaExceededError,
    RateLimitError,
    RenderError,
    ServerError,
    TemplateNotFoundError,
    TimeoutError,
    create_error_from_response,
)


class TestPictifyError:
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
        assert isinstance(PictifyError("Test"), Exception)


class TestTypedErrors:
    def test_authentication_default(self):
        error = AuthenticationError()
        assert error.message == "Invalid or missing API key"
        assert error.status_code == 401
        assert isinstance(error, PictifyError)

    def test_template_not_found_default(self):
        error = TemplateNotFoundError()
        assert error.message == "Template not found"
        assert error.status_code == 404
        assert isinstance(error, PictifyError)

    def test_rate_limit_default(self):
        error = RateLimitError()
        assert error.message == "Rate limit exceeded"
        assert error.status_code == 429
        assert error.retry_after is None

    def test_rate_limit_stores_retry_after(self):
        error = RateLimitError("Too many requests", retry_after=60)
        assert error.retry_after == 60

    def test_quota_default(self):
        error = QuotaExceededError()
        assert error.message == "Render quota exceeded"
        assert error.status_code == 402

    def test_render_default_is_422(self):
        error = RenderError()
        assert error.message == "Render failed"
        assert error.status_code == 422
        assert error.errors is None

    def test_render_carries_field_errors(self):
        error = RenderError("bad", 422, {"errors": [{"field": "name"}]})
        assert error.errors == [{"field": "name"}]

    def test_server_default(self):
        error = ServerError()
        assert error.status_code == 500
        assert isinstance(error, PictifyError)

    def test_network_default(self):
        error = NetworkError()
        assert error.message == "Network error occurred"
        assert error.status_code is None

    def test_network_stores_original_error(self):
        original = Exception("Connection refused")
        error = NetworkError("Network failed", original_error=original)
        assert error.original_error == original

    def test_timeout_default(self):
        error = TimeoutError()
        assert error.message == "Request timed out"
        assert error.timeout is None

    def test_timeout_stores_value(self):
        error = TimeoutError("Timeout after 30s", timeout=30.0)
        assert error.timeout == 30.0


class TestCreateErrorFromResponse:
    def test_401_authentication(self):
        error = create_error_from_response(401, {"message": "Invalid Request"})
        assert isinstance(error, AuthenticationError)
        assert error.message == "Invalid Request"

    def test_402_quota(self):
        error = create_error_from_response(402, {"message": "Quota exceeded"})
        assert isinstance(error, QuotaExceededError)

    def test_404_template_not_found(self):
        error = create_error_from_response(404, {"message": "Template not found"})
        assert isinstance(error, TemplateNotFoundError)

    def test_422_render_with_errors(self):
        error = create_error_from_response(
            422, {"message": "Validation failed", "errors": [{"field": "name"}]}
        )
        assert isinstance(error, RenderError)
        assert error.errors == [{"field": "name"}]

    def test_429_quota_code_is_quota(self):
        error = create_error_from_response(429, {"message": "limit", "code": "quota_exceeded"})
        assert isinstance(error, QuotaExceededError)
        assert error.status_code == 429

    def test_429_without_quota_code_is_rate_limit(self):
        error = create_error_from_response(429, {"message": "slow down"})
        assert isinstance(error, RateLimitError)

    def test_5xx_is_server_error(self):
        for status in (500, 502, 503, 504):
            assert isinstance(create_error_from_response(status, {"message": "x"}), ServerError)

    def test_other_4xx_is_render_error(self):
        # Per the Node reference, ALL non-mapped 4xx (incl. 400, 418) -> RenderError.
        for status in (400, 403, 418):
            assert isinstance(create_error_from_response(status, {"error": "x"}), RenderError)

    def test_non_http_error_status_is_base_error(self):
        # A status below 400 (shouldn't occur as an error) falls through to the base type.
        error = create_error_from_response(399, {"message": "weird"})
        assert isinstance(error, PictifyError)
        assert not isinstance(error, (AuthenticationError, RenderError, ServerError))

    def test_message_precedence_error_over_message(self):
        error = create_error_from_response(422, {"error": "E", "message": "M"})
        assert error.message == "E"

    def test_falls_back_to_message_when_no_error_key(self):
        error = create_error_from_response(422, {"message": "M"})
        assert error.message == "M"

    def test_default_message_when_empty(self):
        error = create_error_from_response(500, {})
        assert error.message == "An unexpected error occurred"

    def test_handles_none_body(self):
        error = create_error_from_response(500, None)
        assert error.message == "An unexpected error occurred"
