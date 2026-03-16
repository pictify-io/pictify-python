"""Tests for synchronous Pictify client."""

import pytest
import respx
from httpx import Response

from pictify import Pictify
from pictify.errors import (
    AuthenticationError,
    QuotaExceededError,
    RateLimitError,
    RenderError,
    NetworkError,
    TimeoutError,
    PictifyError,
)


class TestPictifyInit:
    """Tests for Pictify client initialization."""

    def test_stores_api_key(self):
        client = Pictify(api_key="test-key")
        assert client.api_key == "test-key"
        client.close()

    def test_default_base_url(self):
        client = Pictify(api_key="test-key")
        assert client.base_url == "https://api.pictify.io"
        client.close()

    def test_custom_base_url(self):
        client = Pictify(api_key="test-key", base_url="https://custom.api.com/v1")
        assert client.base_url == "https://custom.api.com/v1"
        client.close()

    def test_strips_trailing_slash(self):
        client = Pictify(api_key="test-key", base_url="https://custom.api.com/v1/")
        assert client.base_url == "https://custom.api.com/v1"
        client.close()

    def test_default_timeout(self):
        client = Pictify(api_key="test-key")
        assert client.timeout == 30.0
        client.close()

    def test_custom_timeout(self):
        client = Pictify(api_key="test-key", timeout=60.0)
        assert client.timeout == 60.0
        client.close()

    def test_default_max_retries(self):
        client = Pictify(api_key="test-key")
        assert client.max_retries == 3
        client.close()

    def test_custom_max_retries(self):
        client = Pictify(api_key="test-key", max_retries=5)
        assert client.max_retries == 5
        client.close()


class TestPictifyContextManager:
    """Tests for context manager functionality."""

    def test_enter_returns_self(self):
        with Pictify(api_key="test-key") as client:
            assert isinstance(client, Pictify)

    def test_exit_closes_client(self):
        client = Pictify(api_key="test-key")
        with client:
            pass
        assert client._client.is_closed

    @respx.mock
    def test_with_statement(self, mock_render_result):
        respx.post("https://api.pictify.io/render").mock(
            return_value=Response(200, json=mock_render_result)
        )

        with Pictify(api_key="test-key") as client:
            result = client.render(template_id="tmpl_123")
            assert result.image_url == mock_render_result["image_url"]


class TestRender:
    """Tests for render method."""

    @respx.mock
    def test_render_minimal_options(self, mock_render_result):
        respx.post("https://api.pictify.io/render").mock(
            return_value=Response(200, json=mock_render_result)
        )

        client = Pictify(api_key="test-key")
        result = client.render(template_id="tmpl_123")

        assert result.image_url == mock_render_result["image_url"]
        assert result.render_id == mock_render_result["render_id"]
        client.close()

    @respx.mock
    def test_render_all_options(self, mock_render_result):
        route = respx.post("https://api.pictify.io/render").mock(
            return_value=Response(200, json=mock_render_result)
        )

        client = Pictify(api_key="test-key")
        client.render(
            template_id="tmpl_123",
            variables={"title": "Hello"},
            format="jpg",
            width=1200,
            height=630,
            device_scale_factor=2.0,
            transparent=True,
            quality=85,
            download=True,
        )

        request = route.calls.last.request
        body = request.content.decode()
        assert '"template_id": "tmpl_123"' in body or '"template_id":"tmpl_123"' in body
        client.close()

    @respx.mock
    def test_render_returns_render_result(self, mock_render_result):
        respx.post("https://api.pictify.io/render").mock(
            return_value=Response(200, json=mock_render_result)
        )

        client = Pictify(api_key="test-key")
        result = client.render(template_id="tmpl_123")

        assert result.width == 1200
        assert result.height == 630
        assert result.format == "png"
        client.close()

    @respx.mock
    def test_render_sends_correct_headers(self, mock_render_result):
        route = respx.post("https://api.pictify.io/render").mock(
            return_value=Response(200, json=mock_render_result)
        )

        client = Pictify(api_key="my-secret-key")
        client.render(template_id="tmpl_123")

        request = route.calls.last.request
        assert request.headers["Authorization"] == "Bearer my-secret-key"
        assert request.headers["Content-Type"] == "application/json"
        assert "pictify-python" in request.headers["User-Agent"]
        client.close()


class TestRenderStream:
    """Tests for render_stream method."""

    @respx.mock
    def test_stream_yields_bytes(self):
        respx.post("https://api.pictify.io/render/stream").mock(
            return_value=Response(200, content=b"chunk1chunk2chunk3")
        )

        client = Pictify(api_key="test-key")
        chunks = list(client.render_stream(template_id="tmpl_123"))

        assert len(chunks) > 0
        assert all(isinstance(chunk, bytes) for chunk in chunks)
        client.close()

    @respx.mock
    def test_stream_handles_error_response(self):
        respx.post("https://api.pictify.io/render/stream").mock(
            return_value=Response(500, json={"message": "Server error"})
        )

        client = Pictify(api_key="test-key")

        with pytest.raises(RenderError):
            list(client.render_stream(template_id="tmpl_123"))

        client.close()


class TestRenderBatch:
    """Tests for render_batch method."""

    @respx.mock
    def test_batch_single_item(self, mock_batch_result):
        respx.post("https://api.pictify.io/render/batch").mock(
            return_value=Response(200, json=mock_batch_result)
        )

        client = Pictify(api_key="test-key")
        result = client.render_batch(
            template_id="tmpl_123",
            items=[{"variables": {"title": "Test"}}],
        )

        assert result.success_count == 1
        assert len(result.results) == 1
        client.close()

    @respx.mock
    def test_batch_max_items(self, mock_batch_result):
        respx.post("https://api.pictify.io/render/batch").mock(
            return_value=Response(200, json=mock_batch_result)
        )

        client = Pictify(api_key="test-key")
        items = [{"variables": {}} for _ in range(500)]
        result = client.render_batch(template_id="tmpl_123", items=items)

        assert result is not None
        client.close()

    @respx.mock
    def test_batch_returns_batch_result(self, mock_batch_result):
        respx.post("https://api.pictify.io/render/batch").mock(
            return_value=Response(200, json=mock_batch_result)
        )

        client = Pictify(api_key="test-key")
        result = client.render_batch(
            template_id="tmpl_123",
            items=[{"variables": {}}],
        )

        assert result.total_time == 500
        assert result.failed_count == 0
        client.close()


class TestRenderHtml:
    """Tests for render_html method."""

    @respx.mock
    def test_html_minimal(self, mock_render_result):
        respx.post("https://api.pictify.io/render/html").mock(
            return_value=Response(200, json=mock_render_result)
        )

        client = Pictify(api_key="test-key")
        result = client.render_html(html="<div>Hello</div>")

        assert result.image_url == mock_render_result["image_url"]
        client.close()

    @respx.mock
    def test_html_with_css(self, mock_render_result):
        route = respx.post("https://api.pictify.io/render/html").mock(
            return_value=Response(200, json=mock_render_result)
        )

        client = Pictify(api_key="test-key")
        client.render_html(html="<div>Hello</div>", css="div { color: red; }")

        request = route.calls.last.request
        body = request.content.decode()
        assert "color: red" in body
        client.close()

    @respx.mock
    def test_html_default_dimensions(self, mock_render_result):
        route = respx.post("https://api.pictify.io/render/html").mock(
            return_value=Response(200, json=mock_render_result)
        )

        client = Pictify(api_key="test-key")
        client.render_html(html="<div>Hello</div>")

        request = route.calls.last.request
        body = request.content.decode()
        assert '"width": 1200' in body or '"width":1200' in body
        assert '"height": 630' in body or '"height":630' in body
        client.close()


class TestRenderGif:
    """Tests for render_gif method."""

    @respx.mock
    def test_gif_with_template(self, mock_gif_result):
        respx.post("https://api.pictify.io/render/gif").mock(
            return_value=Response(200, json=mock_gif_result)
        )

        client = Pictify(api_key="test-key")
        result = client.render_gif(
            template_id="tmpl_123",
            frames=[{"variables": {"text": "Frame 1"}}],
        )

        assert result.gif_url == mock_gif_result["gif_url"]
        client.close()

    @respx.mock
    def test_gif_with_html(self, mock_gif_result):
        route = respx.post("https://api.pictify.io/render/gif").mock(
            return_value=Response(200, json=mock_gif_result)
        )

        client = Pictify(api_key="test-key")
        client.render_gif(
            html="<div>{{text}}</div>",
            frames=[{"variables": {"text": "Frame 1"}}],
        )

        request = route.calls.last.request
        body = request.content.decode()
        assert "{{text}}" in body
        client.close()

    def test_gif_empty_frames_raises(self):
        client = Pictify(api_key="test-key")

        with pytest.raises(ValueError, match="At least one frame is required"):
            client.render_gif(template_id="tmpl_123", frames=[])

        client.close()

    def test_gif_too_many_frames_raises(self):
        client = Pictify(api_key="test-key")
        frames = [{"variables": {}} for _ in range(101)]

        with pytest.raises(ValueError, match="GIF cannot exceed 100 frames"):
            client.render_gif(template_id="tmpl_123", frames=frames)

        client.close()


class TestGetTemplate:
    """Tests for get_template method."""

    @respx.mock
    def test_returns_template(self, mock_template):
        respx.get("https://api.pictify.io/templates/tmpl_123").mock(
            return_value=Response(200, json=mock_template)
        )

        client = Pictify(api_key="test-key")
        result = client.get_template("tmpl_123")

        assert result.id == mock_template["id"]
        assert result.name == mock_template["name"]
        client.close()

    @respx.mock
    def test_template_with_variables(self, mock_template):
        respx.get("https://api.pictify.io/templates/tmpl_123").mock(
            return_value=Response(200, json=mock_template)
        )

        client = Pictify(api_key="test-key")
        result = client.get_template("tmpl_123")

        assert len(result.variables) == 2
        assert result.variables[0].name == "title"
        client.close()


class TestListTemplates:
    """Tests for list_templates method."""

    @respx.mock
    def test_returns_templates(self, mock_template):
        respx.get("https://api.pictify.io/templates").mock(
            return_value=Response(200, json={"templates": [mock_template]})
        )

        client = Pictify(api_key="test-key")
        result = client.list_templates()

        assert len(result) == 1
        assert result[0].id == mock_template["id"]
        client.close()

    @respx.mock
    def test_empty_list(self):
        respx.get("https://api.pictify.io/templates").mock(
            return_value=Response(200, json={"templates": []})
        )

        client = Pictify(api_key="test-key")
        result = client.list_templates()

        assert result == []
        client.close()

    @respx.mock
    def test_pagination_params(self, mock_template):
        route = respx.get("https://api.pictify.io/templates").mock(
            return_value=Response(200, json={"templates": [mock_template]})
        )

        client = Pictify(api_key="test-key")
        client.list_templates(limit=50, offset=10)

        request = route.calls.last.request
        assert "limit=50" in str(request.url)
        assert "offset=10" in str(request.url)
        client.close()


class TestErrorHandling:
    """Tests for error handling."""

    @respx.mock
    def test_authentication_error_on_401(self):
        respx.post("https://api.pictify.io/render").mock(
            return_value=Response(401, json={"message": "Invalid API key"})
        )

        client = Pictify(api_key="invalid-key")

        with pytest.raises(AuthenticationError):
            client.render(template_id="tmpl_123")

        client.close()

    @respx.mock
    def test_quota_exceeded_on_402(self):
        respx.post("https://api.pictify.io/render").mock(
            return_value=Response(402, json={"message": "Quota exceeded"})
        )

        client = Pictify(api_key="test-key")

        with pytest.raises(QuotaExceededError):
            client.render(template_id="tmpl_123")

        client.close()

    @respx.mock
    def test_template_not_found_on_404(self):
        from pictify.errors import TemplateNotFoundError

        respx.post("https://api.pictify.io/render").mock(
            return_value=Response(404, json={"message": "Not found", "template_id": "tmpl_123"})
        )

        client = Pictify(api_key="test-key")

        with pytest.raises(TemplateNotFoundError):
            client.render(template_id="tmpl_123")

        client.close()

    @respx.mock
    def test_rate_limit_on_429(self):
        respx.post("https://api.pictify.io/render").mock(
            return_value=Response(429, json={"message": "Rate limit exceeded"})
        )

        client = Pictify(api_key="test-key", max_retries=0)

        with pytest.raises(RateLimitError):
            client.render(template_id="tmpl_123")

        client.close()

    @respx.mock
    def test_render_error_on_500(self):
        respx.post("https://api.pictify.io/render").mock(
            return_value=Response(500, json={"message": "Server error"})
        )

        client = Pictify(api_key="test-key", max_retries=0)

        with pytest.raises(RenderError):
            client.render(template_id="tmpl_123")

        client.close()


class TestRetryLogic:
    """Tests for retry logic."""

    @respx.mock
    def test_retries_on_5xx(self, mock_render_result):
        route = respx.post("https://api.pictify.io/render").mock(
            side_effect=[
                Response(500, json={"message": "Error 1"}),
                Response(500, json={"message": "Error 2"}),
                Response(200, json=mock_render_result),
            ]
        )

        client = Pictify(api_key="test-key", max_retries=3)
        result = client.render(template_id="tmpl_123")

        assert result.image_url == mock_render_result["image_url"]
        assert len(route.calls) == 3
        client.close()

    @respx.mock
    def test_retries_on_429(self, mock_render_result):
        route = respx.post("https://api.pictify.io/render").mock(
            side_effect=[
                Response(429, json={"message": "Rate limit", "retry_after": 0.1}),
                Response(200, json=mock_render_result),
            ]
        )

        client = Pictify(api_key="test-key", max_retries=3)
        result = client.render(template_id="tmpl_123")

        assert result.image_url == mock_render_result["image_url"]
        assert len(route.calls) == 2
        client.close()

    @respx.mock
    def test_max_retries_exhausted(self):
        respx.post("https://api.pictify.io/render").mock(
            return_value=Response(500, json={"message": "Server error"})
        )

        client = Pictify(api_key="test-key", max_retries=2)

        with pytest.raises(RenderError):
            client.render(template_id="tmpl_123")

        client.close()
