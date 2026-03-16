"""Tests for asynchronous Pictify client."""

import pytest
import respx
from httpx import Response

from pictify import AsyncPictify
from pictify.errors import (
    AuthenticationError,
    QuotaExceededError,
    RateLimitError,
    RenderError,
)


class TestAsyncPictifyInit:
    """Tests for AsyncPictify client initialization."""

    def test_stores_api_key(self):
        client = AsyncPictify(api_key="test-key")
        assert client.api_key == "test-key"

    def test_default_base_url(self):
        client = AsyncPictify(api_key="test-key")
        assert client.base_url == "https://api.pictify.io"

    def test_custom_base_url(self):
        client = AsyncPictify(api_key="test-key", base_url="https://custom.api.com/v1")
        assert client.base_url == "https://custom.api.com/v1"

    def test_strips_trailing_slash(self):
        client = AsyncPictify(api_key="test-key", base_url="https://custom.api.com/v1/")
        assert client.base_url == "https://custom.api.com/v1"

    def test_default_timeout(self):
        client = AsyncPictify(api_key="test-key")
        assert client.timeout == 30.0

    def test_custom_timeout(self):
        client = AsyncPictify(api_key="test-key", timeout=60.0)
        assert client.timeout == 60.0

    def test_default_max_retries(self):
        client = AsyncPictify(api_key="test-key")
        assert client.max_retries == 3

    def test_custom_max_retries(self):
        client = AsyncPictify(api_key="test-key", max_retries=5)
        assert client.max_retries == 5


class TestAsyncPictifyContextManager:
    """Tests for async context manager functionality."""

    @pytest.mark.asyncio
    async def test_aenter_returns_self(self):
        async with AsyncPictify(api_key="test-key") as client:
            assert isinstance(client, AsyncPictify)

    @pytest.mark.asyncio
    async def test_aexit_closes_client(self):
        client = AsyncPictify(api_key="test-key")
        async with client:
            pass
        assert client._client.is_closed

    @pytest.mark.asyncio
    @respx.mock
    async def test_async_with_statement(self, mock_render_result):
        respx.post("https://api.pictify.io/render").mock(
            return_value=Response(200, json=mock_render_result)
        )

        async with AsyncPictify(api_key="test-key") as client:
            result = await client.render(template_id="tmpl_123")
            assert result.image_url == mock_render_result["image_url"]


class TestAsyncRender:
    """Tests for async render method."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_render_minimal_options(self, mock_render_result):
        respx.post("https://api.pictify.io/render").mock(
            return_value=Response(200, json=mock_render_result)
        )

        async with AsyncPictify(api_key="test-key") as client:
            result = await client.render(template_id="tmpl_123")

        assert result.image_url == mock_render_result["image_url"]
        assert result.render_id == mock_render_result["render_id"]

    @pytest.mark.asyncio
    @respx.mock
    async def test_render_all_options(self, mock_render_result):
        route = respx.post("https://api.pictify.io/render").mock(
            return_value=Response(200, json=mock_render_result)
        )

        async with AsyncPictify(api_key="test-key") as client:
            await client.render(
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

    @pytest.mark.asyncio
    @respx.mock
    async def test_render_sends_correct_headers(self, mock_render_result):
        route = respx.post("https://api.pictify.io/render").mock(
            return_value=Response(200, json=mock_render_result)
        )

        async with AsyncPictify(api_key="my-secret-key") as client:
            await client.render(template_id="tmpl_123")

        request = route.calls.last.request
        assert request.headers["Authorization"] == "Bearer my-secret-key"
        assert request.headers["Content-Type"] == "application/json"
        assert "pictify-python" in request.headers["User-Agent"]


class TestAsyncRenderStream:
    """Tests for async render_stream method."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_stream_yields_bytes(self):
        respx.post("https://api.pictify.io/render/stream").mock(
            return_value=Response(200, content=b"chunk1chunk2chunk3")
        )

        async with AsyncPictify(api_key="test-key") as client:
            chunks = []
            async for chunk in client.render_stream(template_id="tmpl_123"):
                chunks.append(chunk)

        assert len(chunks) > 0
        assert all(isinstance(chunk, bytes) for chunk in chunks)

    @pytest.mark.asyncio
    @respx.mock
    async def test_stream_handles_error_response(self):
        respx.post("https://api.pictify.io/render/stream").mock(
            return_value=Response(500, json={"message": "Server error"})
        )

        async with AsyncPictify(api_key="test-key") as client:
            with pytest.raises(RenderError):
                async for _ in client.render_stream(template_id="tmpl_123"):
                    pass


class TestAsyncRenderBatch:
    """Tests for async render_batch method."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_batch_single_item(self, mock_batch_result):
        respx.post("https://api.pictify.io/render/batch").mock(
            return_value=Response(200, json=mock_batch_result)
        )

        async with AsyncPictify(api_key="test-key") as client:
            result = await client.render_batch(
                template_id="tmpl_123",
                items=[{"variables": {"title": "Test"}}],
            )

        assert result.success_count == 1
        assert len(result.results) == 1


class TestAsyncRenderHtml:
    """Tests for async render_html method."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_html_minimal(self, mock_render_result):
        respx.post("https://api.pictify.io/render/html").mock(
            return_value=Response(200, json=mock_render_result)
        )

        async with AsyncPictify(api_key="test-key") as client:
            result = await client.render_html(html="<div>Hello</div>")

        assert result.image_url == mock_render_result["image_url"]

    @pytest.mark.asyncio
    @respx.mock
    async def test_html_with_css(self, mock_render_result):
        route = respx.post("https://api.pictify.io/render/html").mock(
            return_value=Response(200, json=mock_render_result)
        )

        async with AsyncPictify(api_key="test-key") as client:
            await client.render_html(html="<div>Hello</div>", css="div { color: red; }")

        request = route.calls.last.request
        body = request.content.decode()
        assert "color: red" in body


class TestAsyncRenderGif:
    """Tests for async render_gif method."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_gif_with_template(self, mock_gif_result):
        respx.post("https://api.pictify.io/render/gif").mock(
            return_value=Response(200, json=mock_gif_result)
        )

        async with AsyncPictify(api_key="test-key") as client:
            result = await client.render_gif(
                template_id="tmpl_123",
                frames=[{"variables": {"text": "Frame 1"}}],
            )

        assert result.gif_url == mock_gif_result["gif_url"]

    @pytest.mark.asyncio
    async def test_gif_empty_frames_raises(self):
        async with AsyncPictify(api_key="test-key") as client:
            with pytest.raises(ValueError, match="At least one frame is required"):
                await client.render_gif(template_id="tmpl_123", frames=[])

    @pytest.mark.asyncio
    async def test_gif_too_many_frames_raises(self):
        async with AsyncPictify(api_key="test-key") as client:
            frames = [{"variables": {}} for _ in range(101)]
            with pytest.raises(ValueError, match="GIF cannot exceed 100 frames"):
                await client.render_gif(template_id="tmpl_123", frames=frames)


class TestAsyncGetTemplate:
    """Tests for async get_template method."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_returns_template(self, mock_template):
        respx.get("https://api.pictify.io/templates/tmpl_123").mock(
            return_value=Response(200, json=mock_template)
        )

        async with AsyncPictify(api_key="test-key") as client:
            result = await client.get_template("tmpl_123")

        assert result.id == mock_template["id"]
        assert result.name == mock_template["name"]


class TestAsyncListTemplates:
    """Tests for async list_templates method."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_returns_templates(self, mock_template):
        respx.get("https://api.pictify.io/templates").mock(
            return_value=Response(200, json={"templates": [mock_template]})
        )

        async with AsyncPictify(api_key="test-key") as client:
            result = await client.list_templates()

        assert len(result) == 1
        assert result[0].id == mock_template["id"]

    @pytest.mark.asyncio
    @respx.mock
    async def test_empty_list(self):
        respx.get("https://api.pictify.io/templates").mock(
            return_value=Response(200, json={"templates": []})
        )

        async with AsyncPictify(api_key="test-key") as client:
            result = await client.list_templates()

        assert result == []


class TestAsyncErrorHandling:
    """Tests for async error handling."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_authentication_error_on_401(self):
        respx.post("https://api.pictify.io/render").mock(
            return_value=Response(401, json={"message": "Invalid API key"})
        )

        async with AsyncPictify(api_key="invalid-key") as client:
            with pytest.raises(AuthenticationError):
                await client.render(template_id="tmpl_123")

    @pytest.mark.asyncio
    @respx.mock
    async def test_quota_exceeded_on_402(self):
        respx.post("https://api.pictify.io/render").mock(
            return_value=Response(402, json={"message": "Quota exceeded"})
        )

        async with AsyncPictify(api_key="test-key") as client:
            with pytest.raises(QuotaExceededError):
                await client.render(template_id="tmpl_123")

    @pytest.mark.asyncio
    @respx.mock
    async def test_rate_limit_on_429(self):
        respx.post("https://api.pictify.io/render").mock(
            return_value=Response(429, json={"message": "Rate limit exceeded"})
        )

        async with AsyncPictify(api_key="test-key", max_retries=0) as client:
            with pytest.raises(RateLimitError):
                await client.render(template_id="tmpl_123")

    @pytest.mark.asyncio
    @respx.mock
    async def test_render_error_on_500(self):
        respx.post("https://api.pictify.io/render").mock(
            return_value=Response(500, json={"message": "Server error"})
        )

        async with AsyncPictify(api_key="test-key", max_retries=0) as client:
            with pytest.raises(RenderError):
                await client.render(template_id="tmpl_123")


class TestAsyncRetryLogic:
    """Tests for async retry logic."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_retries_on_5xx(self, mock_render_result):
        route = respx.post("https://api.pictify.io/render").mock(
            side_effect=[
                Response(500, json={"message": "Error 1"}),
                Response(500, json={"message": "Error 2"}),
                Response(200, json=mock_render_result),
            ]
        )

        async with AsyncPictify(api_key="test-key", max_retries=3) as client:
            result = await client.render(template_id="tmpl_123")

        assert result.image_url == mock_render_result["image_url"]
        assert len(route.calls) == 3

    @pytest.mark.asyncio
    @respx.mock
    async def test_retries_on_429(self, mock_render_result):
        route = respx.post("https://api.pictify.io/render").mock(
            side_effect=[
                Response(429, json={"message": "Rate limit", "retry_after": 0.01}),
                Response(200, json=mock_render_result),
            ]
        )

        async with AsyncPictify(api_key="test-key", max_retries=3) as client:
            result = await client.render(template_id="tmpl_123")

        assert result.image_url == mock_render_result["image_url"]
        assert len(route.calls) == 2

    @pytest.mark.asyncio
    @respx.mock
    async def test_max_retries_exhausted(self):
        respx.post("https://api.pictify.io/render").mock(
            return_value=Response(500, json={"message": "Server error"})
        )

        async with AsyncPictify(api_key="test-key", max_retries=2) as client:
            with pytest.raises(RenderError):
                await client.render(template_id="tmpl_123")
