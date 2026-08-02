"""Unit tests for the asynchronous Pictify client (mocked with respx)."""

import json as jsonlib

import httpx
import pytest
import respx
from httpx import Response

from pictify import AsyncPictify
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
)

BASE = "https://api.pictify.io"


def _body(route):
    """Decode the JSON body of the last request on a respx route."""
    return jsonlib.loads(route.calls.last.request.content.decode())


# --------------------------------------------------------------------------- #
# Initialization / config
# --------------------------------------------------------------------------- #
class TestInit:
    def test_stores_api_key(self):
        client = AsyncPictify(api_key="test-key")
        assert client.api_key == "test-key"

    def test_default_base_url(self):
        assert AsyncPictify(api_key="k").base_url == BASE

    def test_custom_base_url_strips_trailing_slash(self):
        client = AsyncPictify(api_key="k", base_url="https://custom.api.com/v1/")
        assert client.base_url == "https://custom.api.com/v1"

    def test_default_timeout_and_retries(self):
        client = AsyncPictify(api_key="k")
        assert client.timeout == 30.0
        assert client.max_retries == 3

    def test_custom_timeout_and_retries(self):
        client = AsyncPictify(api_key="k", timeout=60.0, max_retries=5)
        assert client.timeout == 60.0
        assert client.max_retries == 5


class TestContextManager:
    @pytest.mark.asyncio
    async def test_aenter_returns_self(self):
        async with AsyncPictify(api_key="k") as client:
            assert isinstance(client, AsyncPictify)

    @pytest.mark.asyncio
    async def test_aexit_closes_client(self):
        client = AsyncPictify(api_key="k")
        async with client:
            pass
        assert client._client.is_closed


# --------------------------------------------------------------------------- #
# render_html
# --------------------------------------------------------------------------- #
class TestRenderHtml:
    @pytest.mark.asyncio
    @respx.mock
    async def test_happy_path(self, mock_image_result):
        route = respx.post(f"{BASE}/image").mock(
            return_value=Response(200, json=mock_image_result)
        )
        async with AsyncPictify(api_key="k") as client:
            result = await client.render_html(html="<div>Hi</div>", width=600, height=300)
        assert result.url == mock_image_result["url"]
        assert result.id == "img_abc123"
        body = _body(route)
        assert body["html"] == "<div>Hi</div>"
        assert body["fileExtension"] == "png"

    @pytest.mark.asyncio
    @respx.mock
    async def test_css_is_prepended(self, mock_image_result):
        route = respx.post(f"{BASE}/image").mock(
            return_value=Response(200, json=mock_image_result)
        )
        async with AsyncPictify(api_key="k") as client:
            await client.render_html(html="<div>Hi</div>", css="div{color:red}")
        assert _body(route)["html"] == "<style>div{color:red}</style><div>Hi</div>"

    @pytest.mark.asyncio
    @respx.mock
    async def test_format_maps_to_file_extension(self, mock_image_result):
        route = respx.post(f"{BASE}/image").mock(
            return_value=Response(200, json=mock_image_result)
        )
        async with AsyncPictify(api_key="k") as client:
            await client.render_html(html="<div>x</div>", format="pdf")
        body = _body(route)
        assert body["fileExtension"] == "pdf"
        assert "format" not in body

    @pytest.mark.asyncio
    @respx.mock
    async def test_strips_none_fields(self, mock_image_result):
        route = respx.post(f"{BASE}/image").mock(
            return_value=Response(200, json=mock_image_result)
        )
        async with AsyncPictify(api_key="k") as client:
            await client.render_html(html="<div>x</div>")
        body = _body(route)
        assert "width" not in body and "selector" not in body

    @pytest.mark.asyncio
    @respx.mock
    async def test_sends_auth_header(self, mock_image_result):
        route = respx.post(f"{BASE}/image").mock(
            return_value=Response(200, json=mock_image_result)
        )
        async with AsyncPictify(api_key="secret") as client:
            await client.render_html(html="<div>x</div>")
        req = route.calls.last.request
        assert req.headers["Authorization"] == "Bearer secret"
        assert "pictify-python" in req.headers["User-Agent"]

    @pytest.mark.asyncio
    @respx.mock
    async def test_error(self):
        respx.post(f"{BASE}/image").mock(
            return_value=Response(422, json={"error": "Render failed"})
        )
        async with AsyncPictify(api_key="k", max_retries=0) as client:
            with pytest.raises(RenderError):
                await client.render_html(html="<div>x</div>")


# --------------------------------------------------------------------------- #
# render_url
# --------------------------------------------------------------------------- #
class TestRenderUrl:
    @pytest.mark.asyncio
    @respx.mock
    async def test_happy_path(self, mock_image_result):
        route = respx.post(f"{BASE}/image").mock(
            return_value=Response(200, json=mock_image_result)
        )
        async with AsyncPictify(api_key="k") as client:
            result = await client.render_url(url="https://example.com", selector=".hero")
        assert result.url == mock_image_result["url"]
        body = _body(route)
        assert body["url"] == "https://example.com"
        assert body["selector"] == ".hero"

    @pytest.mark.asyncio
    @respx.mock
    async def test_error(self):
        respx.post(f"{BASE}/image").mock(
            return_value=Response(401, json={"message": "Invalid Request"})
        )
        async with AsyncPictify(api_key="bad", max_retries=0) as client:
            with pytest.raises(AuthenticationError):
                await client.render_url(url="https://example.com")


# --------------------------------------------------------------------------- #
# render (template)
# --------------------------------------------------------------------------- #
class TestRender:
    @pytest.mark.asyncio
    @respx.mock
    async def test_happy_path(self, mock_render_result):
        route = respx.post(f"{BASE}/templates/XL13/render").mock(
            return_value=Response(200, json=mock_render_result)
        )
        async with AsyncPictify(api_key="k") as client:
            result = await client.render("XL13", variables={"name": "Ada", "company": "Pictify"})
        assert result.url == "https://cdn.pictify.io/renders/default.png"
        assert result.template_uid == "tmpl_abc123"
        body = _body(route)
        assert body["variables"] == {"name": "Ada", "company": "Pictify"}
        assert body["format"] == "png"

    @pytest.mark.asyncio
    @respx.mock
    async def test_url_encodes_template_id(self, mock_render_result):
        route = respx.post(f"{BASE}/templates/a%2Fb/render").mock(
            return_value=Response(200, json=mock_render_result)
        )
        async with AsyncPictify(api_key="k") as client:
            await client.render("a/b")
        assert route.called

    @pytest.mark.asyncio
    @respx.mock
    async def test_optional_params_sent(self, mock_render_result):
        route = respx.post(f"{BASE}/templates/XL13/render").mock(
            return_value=Response(200, json=mock_render_result)
        )
        async with AsyncPictify(api_key="k") as client:
            await client.render(
                "XL13", format="pdf", quality=0.7, width=800, height=600, layout="square"
            )
        body = _body(route)
        assert body["format"] == "pdf"
        assert body["quality"] == 0.7
        assert body["layout"] == "square"

    @pytest.mark.asyncio
    @respx.mock
    async def test_error(self):
        respx.post(f"{BASE}/templates/XL13/render").mock(
            return_value=Response(404, json={"message": "Template not found"})
        )
        async with AsyncPictify(api_key="k", max_retries=0) as client:
            with pytest.raises(TemplateNotFoundError):
                await client.render("XL13")


# --------------------------------------------------------------------------- #
# render_layouts
# --------------------------------------------------------------------------- #
class TestRenderLayouts:
    @pytest.mark.asyncio
    @respx.mock
    async def test_happy_path(self, mock_layout_render_result):
        route = respx.post(f"{BASE}/templates/XL13/render").mock(
            return_value=Response(200, json=mock_layout_render_result)
        )
        async with AsyncPictify(api_key="k") as client:
            result = await client.render_layouts(
                "XL13", layouts=["default", "square", "bogus"], variables={"name": "Ada"}
            )
        body = _body(route)
        assert body["layouts"] == ["default", "square", "bogus"]
        assert len(result.results) == 2
        assert result.errors[0].layout == "bogus"
        assert result.url == "https://cdn.pictify.io/renders/default.png"

    @pytest.mark.asyncio
    @respx.mock
    async def test_error(self):
        respx.post(f"{BASE}/templates/XL13/render").mock(
            return_value=Response(401, json={"message": "Invalid Request"})
        )
        async with AsyncPictify(api_key="bad", max_retries=0) as client:
            with pytest.raises(AuthenticationError):
                await client.render_layouts("XL13", layouts=["default"])


# --------------------------------------------------------------------------- #
# render_gif
# --------------------------------------------------------------------------- #
class TestRenderGif:
    @pytest.mark.asyncio
    @respx.mock
    async def test_from_html_flattens_envelope(self, mock_gif_result):
        route = respx.post(f"{BASE}/gif").mock(
            return_value=Response(200, json=mock_gif_result)
        )
        async with AsyncPictify(api_key="k") as client:
            result = await client.render_gif(
                html="<div>x</div>", width=400, height=200, quality="low"
            )
        assert result.url == "https://cdn.pictify.io/renders/abc123.gif"
        assert result.uid == "gif_abc123"
        assert result.animation_length == 2000
        body = _body(route)
        assert body["html"] == "<div>x</div>"
        assert body["quality"] == "low"

    @pytest.mark.asyncio
    @respx.mock
    async def test_from_template_uses_template_key(self, mock_gif_result):
        route = respx.post(f"{BASE}/gif").mock(
            return_value=Response(200, json=mock_gif_result)
        )
        async with AsyncPictify(api_key="k") as client:
            await client.render_gif(template_id="XL13", variables={"name": "Ada"})
        body = _body(route)
        assert body["template"] == "XL13"
        assert "template_id" not in body
        assert body["quality"] == "medium"

    @pytest.mark.asyncio
    @respx.mock
    async def test_error(self):
        respx.post(f"{BASE}/gif").mock(
            return_value=Response(422, json={"error": "Static source"})
        )
        async with AsyncPictify(api_key="k", max_retries=0) as client:
            with pytest.raises(RenderError):
                await client.render_gif(html="<div>x</div>")


# --------------------------------------------------------------------------- #
# render_batch + get_batch_results
# --------------------------------------------------------------------------- #
class TestRenderBatch:
    @pytest.mark.asyncio
    @respx.mock
    async def test_submit_happy_path(self, mock_batch_submit_result):
        route = respx.post(f"{BASE}/templates/XL13/batch-render").mock(
            return_value=Response(202, json=mock_batch_submit_result)
        )
        async with AsyncPictify(api_key="k") as client:
            result = await client.render_batch(
                "XL13", [{"name": "A"}, {"name": "B"}], format="png"
            )
        assert result.batch_id == "batch_abc123"
        assert result.total_items == 2
        body = _body(route)
        assert body["variableSets"] == [{"name": "A"}, {"name": "B"}]

    @pytest.mark.asyncio
    @respx.mock
    async def test_optional_params(self, mock_batch_submit_result):
        route = respx.post(f"{BASE}/templates/XL13/batch-render").mock(
            return_value=Response(202, json=mock_batch_submit_result)
        )
        async with AsyncPictify(api_key="k") as client:
            await client.render_batch(
                "XL13", [{"n": 1}], quality=0.8, concurrency=3, layouts=["default"]
            )
        body = _body(route)
        assert body["concurrency"] == 3
        assert body["layouts"] == ["default"]

    @pytest.mark.asyncio
    @respx.mock
    async def test_error(self):
        respx.post(f"{BASE}/templates/XL13/batch-render").mock(
            return_value=Response(402, json={"message": "Quota exceeded"})
        )
        async with AsyncPictify(api_key="k", max_retries=0) as client:
            with pytest.raises(QuotaExceededError):
                await client.render_batch("XL13", [{"n": 1}])


class TestGetBatchResults:
    @pytest.mark.asyncio
    @respx.mock
    async def test_happy_path(self, mock_batch_results):
        respx.get(f"{BASE}/templates/batch/batch_abc123/results").mock(
            return_value=Response(200, json=mock_batch_results)
        )
        async with AsyncPictify(api_key="k") as client:
            result = await client.get_batch_results("batch_abc123")
        assert result.batch_id == "batch_abc123"
        assert result.completed_items == 1
        assert result.results[0].success is True

    @pytest.mark.asyncio
    @respx.mock
    async def test_error(self):
        respx.get(f"{BASE}/templates/batch/missing/results").mock(
            return_value=Response(404, json={"message": "Batch not found"})
        )
        async with AsyncPictify(api_key="k", max_retries=0) as client:
            with pytest.raises(TemplateNotFoundError):
                await client.get_batch_results("missing")


# --------------------------------------------------------------------------- #
# get_template
# --------------------------------------------------------------------------- #
class TestGetTemplate:
    @pytest.mark.asyncio
    @respx.mock
    async def test_unwraps_envelope(self, mock_template_envelope):
        respx.get(f"{BASE}/templates/XL13").mock(
            return_value=Response(200, json=mock_template_envelope)
        )
        async with AsyncPictify(api_key="k") as client:
            template = await client.get_template("XL13")
        assert template.uid == "tmpl_abc123"
        assert template.variable_definitions[0].name == "name"

    @pytest.mark.asyncio
    @respx.mock
    async def test_not_found(self):
        respx.get(f"{BASE}/templates/missing").mock(
            return_value=Response(404, json={"message": "Template not found"})
        )
        async with AsyncPictify(api_key="k", max_retries=0) as client:
            with pytest.raises(TemplateNotFoundError):
                await client.get_template("missing")


# --------------------------------------------------------------------------- #
# list_templates
# --------------------------------------------------------------------------- #
class TestListTemplates:
    @pytest.mark.asyncio
    @respx.mock
    async def test_happy_path(self, mock_list_templates_result):
        respx.get(f"{BASE}/templates").mock(
            return_value=Response(200, json=mock_list_templates_result)
        )
        async with AsyncPictify(api_key="k") as client:
            result = await client.list_templates()
        assert len(result.templates) == 1
        assert result.templates[0].uid == "tmpl_abc123"
        assert result.pagination.total == 1

    @pytest.mark.asyncio
    @respx.mock
    async def test_query_params(self, mock_list_templates_result):
        route = respx.get(f"{BASE}/templates").mock(
            return_value=Response(200, json=mock_list_templates_result)
        )
        async with AsyncPictify(api_key="k") as client:
            await client.list_templates(page=2, limit=50, sort="name")
        url = str(route.calls.last.request.url)
        assert "page=2" in url and "limit=50" in url and "sort=name" in url

    @pytest.mark.asyncio
    @respx.mock
    async def test_error(self):
        respx.get(f"{BASE}/templates").mock(
            return_value=Response(401, json={"message": "Invalid Request"})
        )
        async with AsyncPictify(api_key="bad", max_retries=0) as client:
            with pytest.raises(AuthenticationError):
                await client.list_templates()


# --------------------------------------------------------------------------- #
# create_template
# --------------------------------------------------------------------------- #
class TestCreateTemplate:
    @pytest.mark.asyncio
    @respx.mock
    async def test_happy_path(self, mock_template_envelope):
        route = respx.post(f"{BASE}/templates").mock(
            return_value=Response(200, json=mock_template_envelope)
        )
        async with AsyncPictify(api_key="k") as client:
            template = await client.create_template(
                html="<div>Hi {{name}}</div>", name="Welcome", width=400, height=150
            )
        assert template.uid == "tmpl_abc123"
        body = _body(route)
        assert body["html"] == "<div>Hi {{name}}</div>"
        assert body["name"] == "Welcome"

    @pytest.mark.asyncio
    @respx.mock
    async def test_error(self):
        respx.post(f"{BASE}/templates").mock(
            return_value=Response(422, json={"message": "Validation failed", "errors": ["x"]})
        )
        async with AsyncPictify(api_key="k", max_retries=0) as client:
            with pytest.raises(RenderError) as exc:
                await client.create_template(html="<div>x</div>")
        assert exc.value.errors == ["x"]


# --------------------------------------------------------------------------- #
# list_video_templates
# --------------------------------------------------------------------------- #
class TestListVideoTemplates:
    @pytest.mark.asyncio
    @respx.mock
    async def test_unwraps_envelope(self, mock_list_video_templates_result):
        respx.get(f"{BASE}/video/templates").mock(
            return_value=Response(200, json=mock_list_video_templates_result)
        )
        async with AsyncPictify(api_key="k") as client:
            templates = await client.list_video_templates()
        assert len(templates) == 1
        assert templates[0].uid == "vid_abc123"
        assert templates[0].duration_in_frames == 240

    @pytest.mark.asyncio
    @respx.mock
    async def test_error(self):
        respx.get(f"{BASE}/video/templates").mock(
            return_value=Response(401, json={"message": "Invalid Request"})
        )
        async with AsyncPictify(api_key="bad", max_retries=0) as client:
            with pytest.raises(AuthenticationError):
                await client.list_video_templates()


# --------------------------------------------------------------------------- #
# get_video_template_variables
# --------------------------------------------------------------------------- #
class TestGetVideoTemplateVariables:
    @pytest.mark.asyncio
    @respx.mock
    async def test_happy_path(self, mock_video_variables_result):
        respx.get(f"{BASE}/video/templates/vid_abc123/variables").mock(
            return_value=Response(200, json=mock_video_variables_result)
        )
        async with AsyncPictify(api_key="k") as client:
            result = await client.get_video_template_variables("vid_abc123")
        assert result.template_uid == "vid_abc123"
        assert result.variables[0].name == "title"
        assert result.referenced == ["title", "accent"]

    @pytest.mark.asyncio
    @respx.mock
    async def test_not_found(self):
        respx.get(f"{BASE}/video/templates/missing/variables").mock(
            return_value=Response(404, json={"message": "Template not found"})
        )
        async with AsyncPictify(api_key="k", max_retries=0) as client:
            with pytest.raises(TemplateNotFoundError):
                await client.get_video_template_variables("missing")


# --------------------------------------------------------------------------- #
# render_video
# --------------------------------------------------------------------------- #
class TestRenderVideo:
    @pytest.mark.asyncio
    @respx.mock
    async def test_happy_path(self, mock_render_video_result):
        route = respx.post(f"{BASE}/video/templates/vid_abc123/render").mock(
            return_value=Response(200, json=mock_render_video_result)
        )
        async with AsyncPictify(api_key="k") as client:
            result = await client.render_video("vid_abc123", variables={"title": "Hi"})
        assert result.url == "https://media.pictify.io/videos/abc123.mp4"
        assert result.duration_in_frames == 240
        body = _body(route)
        assert body["variables"] == {"title": "Hi"}
        assert body["format"] == "mp4"

    @pytest.mark.asyncio
    @respx.mock
    async def test_gif_format(self, mock_render_video_result):
        route = respx.post(f"{BASE}/video/templates/vid_abc123/render").mock(
            return_value=Response(200, json=mock_render_video_result)
        )
        async with AsyncPictify(api_key="k") as client:
            await client.render_video("vid_abc123", format="gif")
        assert _body(route)["format"] == "gif"

    @pytest.mark.asyncio
    @respx.mock
    async def test_uses_video_render_timeout_not_client_default(self, mock_render_video_result):
        route = respx.post(f"{BASE}/video/templates/vid_abc123/render").mock(
            return_value=Response(200, json=mock_render_video_result)
        )
        async with AsyncPictify(api_key="k") as client:  # client-wide default is 30s
            await client.render_video("vid_abc123")
        assert route.calls.last.request.extensions["timeout"]["read"] == 300.0

    @pytest.mark.asyncio
    @respx.mock
    async def test_per_call_timeout_override(self, mock_render_video_result):
        route = respx.post(f"{BASE}/video/templates/vid_abc123/render").mock(
            return_value=Response(200, json=mock_render_video_result)
        )
        async with AsyncPictify(api_key="k") as client:
            await client.render_video("vid_abc123", timeout=600.0)
        assert route.calls.last.request.extensions["timeout"]["read"] == 600.0

    @pytest.mark.asyncio
    @respx.mock
    async def test_url_encodes_template_id(self, mock_render_video_result):
        route = respx.post(f"{BASE}/video/templates/a%2Fb/render").mock(
            return_value=Response(200, json=mock_render_video_result)
        )
        async with AsyncPictify(api_key="k") as client:
            await client.render_video("a/b")
        assert route.called

    @pytest.mark.asyncio
    @respx.mock
    async def test_invalid_variable_error(self):
        respx.post(f"{BASE}/video/templates/vid_abc123/render").mock(
            return_value=Response(
                422, json={"message": "Unknown variable: bogus", "code": "invalid_variable"}
            )
        )
        async with AsyncPictify(api_key="k", max_retries=0) as client:
            with pytest.raises(RenderError):
                await client.render_video("vid_abc123", variables={"bogus": "x"})


# --------------------------------------------------------------------------- #
# generate_video_template
# --------------------------------------------------------------------------- #
class TestGenerateVideoTemplate:
    @pytest.mark.asyncio
    @respx.mock
    async def test_happy_path(self, mock_generate_video_result):
        route = respx.post(f"{BASE}/video/templates/generate").mock(
            return_value=Response(200, json=mock_generate_video_result)
        )
        async with AsyncPictify(api_key="k") as client:
            result = await client.generate_video_template("A launch teaser")
        assert result.template.uid == "vid_abc123"
        assert result.preview_url == "https://media.pictify.io/previews/vid_abc123.png"
        body = _body(route)
        assert body["prompt"] == "A launch teaser"
        assert body["durationSeconds"] == 8
        assert "brandColor" not in body

    @pytest.mark.asyncio
    @respx.mock
    async def test_uses_generate_timeout(self, mock_generate_video_result):
        route = respx.post(f"{BASE}/video/templates/generate").mock(
            return_value=Response(200, json=mock_generate_video_result)
        )
        async with AsyncPictify(api_key="k") as client:
            await client.generate_video_template("A promo", brand_color="#ff5500")
        assert route.calls.last.request.extensions["timeout"]["read"] == 180.0
        assert _body(route)["brandColor"] == "#ff5500"

    @pytest.mark.asyncio
    @respx.mock
    async def test_error(self):
        respx.post(f"{BASE}/video/templates/generate").mock(
            return_value=Response(429, json={"message": "limit", "code": "quota_exceeded"})
        )
        async with AsyncPictify(api_key="k", max_retries=0) as client:
            with pytest.raises(QuotaExceededError):
                await client.generate_video_template("A promo")


# --------------------------------------------------------------------------- #
# create_video_template
# --------------------------------------------------------------------------- #
class TestCreateVideoTemplate:
    @pytest.mark.asyncio
    @respx.mock
    async def test_happy_path_computes_duration_in_frames(self, mock_video_template_envelope):
        route = respx.post(f"{BASE}/video/templates").mock(
            return_value=Response(200, json=mock_video_template_envelope)
        )
        async with AsyncPictify(api_key="k") as client:
            template = await client.create_video_template(
                "Own scene", "export default () => null"
            )
        assert template.uid == "vid_abc123"
        body = _body(route)
        assert body["kind"] == "tsx"
        assert body["status"] == "draft"
        assert body["durationInFrames"] == 240  # round(8 * 30)
        assert route.calls.last.request.extensions["timeout"]["read"] == 180.0

    @pytest.mark.asyncio
    @respx.mock
    async def test_custom_fps_and_duration(self, mock_video_template_envelope):
        route = respx.post(f"{BASE}/video/templates").mock(
            return_value=Response(200, json=mock_video_template_envelope)
        )
        async with AsyncPictify(api_key="k") as client:
            await client.create_video_template(
                "Scene", "export default () => null", fps=24, duration_seconds=2.5
            )
        assert _body(route)["durationInFrames"] == 60  # round(2.5 * 24)

    @pytest.mark.asyncio
    @respx.mock
    async def test_compile_gate_422_carries_errors(self):
        respx.post(f"{BASE}/video/templates").mock(
            return_value=Response(
                422, json={"message": "Compilation failed", "errors": ["Unexpected token"]}
            )
        )
        async with AsyncPictify(api_key="k", max_retries=0) as client:
            with pytest.raises(RenderError) as exc:
                await client.create_video_template("Broken", "not valid tsx")
        assert exc.value.errors == ["Unexpected token"]


# --------------------------------------------------------------------------- #
# Error mapping, retries, transport
# --------------------------------------------------------------------------- #
class TestErrorMapping:
    @pytest.mark.asyncio
    @respx.mock
    async def test_429_quota_code_is_quota_error(self):
        respx.post(f"{BASE}/image").mock(
            return_value=Response(429, json={"message": "limit", "code": "quota_exceeded"})
        )
        async with AsyncPictify(api_key="k", max_retries=0) as client:
            with pytest.raises(QuotaExceededError):
                await client.render_html(html="<div>x</div>")

    @pytest.mark.asyncio
    @respx.mock
    async def test_429_without_quota_code_is_rate_limit(self):
        respx.post(f"{BASE}/image").mock(
            return_value=Response(429, json={"message": "slow down"})
        )
        async with AsyncPictify(api_key="k", max_retries=0) as client:
            with pytest.raises(RateLimitError):
                await client.render_html(html="<div>x</div>")

    @pytest.mark.asyncio
    @respx.mock
    async def test_5xx_is_server_error(self):
        respx.post(f"{BASE}/image").mock(
            return_value=Response(500, json={"message": "boom"})
        )
        async with AsyncPictify(api_key="k", max_retries=0) as client:
            with pytest.raises(ServerError):
                await client.render_html(html="<div>x</div>")

    @pytest.mark.asyncio
    @respx.mock
    async def test_error_message_precedence(self):
        respx.post(f"{BASE}/image").mock(
            return_value=Response(422, json={"error": "E", "message": "M"})
        )
        async with AsyncPictify(api_key="k", max_retries=0) as client:
            with pytest.raises(RenderError) as exc:
                await client.render_html(html="<div>x</div>")
        assert exc.value.message == "E"

    @pytest.mark.asyncio
    @respx.mock
    async def test_non_json_error_uses_text(self):
        respx.post(f"{BASE}/image").mock(return_value=Response(403, text="Forbidden"))
        async with AsyncPictify(api_key="k", max_retries=0) as client:
            with pytest.raises(PictifyError) as exc:
                await client.render_html(html="<div>x</div>")
        assert exc.value.status_code == 403


class TestRetries:
    @pytest.mark.asyncio
    @respx.mock
    async def test_retries_on_5xx_then_succeeds(self, monkeypatch, mock_image_result):
        async def _no_sleep(_s):
            return None

        monkeypatch.setattr("pictify.async_client.asyncio.sleep", _no_sleep)
        route = respx.post(f"{BASE}/image").mock(
            side_effect=[
                Response(500, json={"message": "e1"}),
                Response(500, json={"message": "e2"}),
                Response(200, json=mock_image_result),
            ]
        )
        async with AsyncPictify(api_key="k", max_retries=3) as client:
            result = await client.render_html(html="<div>x</div>")
        assert result.url == mock_image_result["url"]
        assert len(route.calls) == 3

    @pytest.mark.asyncio
    @respx.mock
    async def test_does_not_retry_on_4xx(self):
        route = respx.post(f"{BASE}/image").mock(
            return_value=Response(422, json={"error": "bad"})
        )
        async with AsyncPictify(api_key="k", max_retries=3) as client:
            with pytest.raises(RenderError):
                await client.render_html(html="<div>x</div>")
        assert len(route.calls) == 1

    @pytest.mark.asyncio
    @respx.mock
    async def test_max_retries_exhausted_raises_server_error(self, monkeypatch):
        async def _no_sleep(_s):
            return None

        monkeypatch.setattr("pictify.async_client.asyncio.sleep", _no_sleep)
        respx.post(f"{BASE}/image").mock(
            return_value=Response(500, json={"message": "boom"})
        )
        async with AsyncPictify(api_key="k", max_retries=2) as client:
            with pytest.raises(ServerError):
                await client.render_html(html="<div>x</div>")


class TestTransportErrors:
    @pytest.mark.asyncio
    @respx.mock
    async def test_timeout_raises_timeout_error(self):
        respx.post(f"{BASE}/image").mock(side_effect=httpx.TimeoutException("t"))
        async with AsyncPictify(api_key="k", max_retries=0) as client:
            with pytest.raises(TimeoutError):
                await client.render_html(html="<div>x</div>")

    @pytest.mark.asyncio
    @respx.mock
    async def test_network_error_raises_network_error(self):
        respx.post(f"{BASE}/image").mock(side_effect=httpx.ConnectError("refused"))
        async with AsyncPictify(api_key="k", max_retries=0) as client:
            with pytest.raises(NetworkError):
                await client.render_html(html="<div>x</div>")

    @pytest.mark.asyncio
    @respx.mock
    async def test_network_error_retries_then_succeeds(self, monkeypatch, mock_image_result):
        async def _no_sleep(_s):
            return None

        monkeypatch.setattr("pictify.async_client.asyncio.sleep", _no_sleep)
        route = respx.post(f"{BASE}/image").mock(
            side_effect=[httpx.ConnectError("refused"), Response(200, json=mock_image_result)]
        )
        async with AsyncPictify(api_key="k", max_retries=3) as client:
            result = await client.render_html(html="<div>x</div>")
        assert result.url == mock_image_result["url"]
        assert len(route.calls) == 2
