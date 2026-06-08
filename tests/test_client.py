"""Unit tests for the synchronous Pictify client (mocked with respx)."""

import json as jsonlib

import httpx
import pytest
import respx
from httpx import Response

from pictify import Pictify
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
        client = Pictify(api_key="test-key")
        assert client.api_key == "test-key"
        client.close()

    def test_default_base_url(self):
        client = Pictify(api_key="k")
        assert client.base_url == BASE
        client.close()

    def test_custom_base_url_strips_trailing_slash(self):
        client = Pictify(api_key="k", base_url="https://custom.api.com/v1/")
        assert client.base_url == "https://custom.api.com/v1"
        client.close()

    def test_default_timeout_and_retries(self):
        client = Pictify(api_key="k")
        assert client.timeout == 30.0
        assert client.max_retries == 3
        client.close()

    def test_custom_timeout_and_retries(self):
        client = Pictify(api_key="k", timeout=60.0, max_retries=5)
        assert client.timeout == 60.0
        assert client.max_retries == 5
        client.close()


class TestContextManager:
    def test_enter_returns_self(self):
        with Pictify(api_key="k") as client:
            assert isinstance(client, Pictify)

    def test_exit_closes_client(self):
        client = Pictify(api_key="k")
        with client:
            pass
        assert client._client.is_closed


# --------------------------------------------------------------------------- #
# render_html
# --------------------------------------------------------------------------- #
class TestRenderHtml:
    @respx.mock
    def test_happy_path(self, mock_image_result):
        route = respx.post(f"{BASE}/image").mock(
            return_value=Response(200, json=mock_image_result)
        )
        client = Pictify(api_key="k")
        result = client.render_html(html="<div>Hi</div>", width=600, height=300)

        assert result.url == mock_image_result["url"]
        assert result.id == "img_abc123"
        assert result.created_at is not None
        body = _body(route)
        assert body["html"] == "<div>Hi</div>"
        assert body["fileExtension"] == "png"
        assert body["width"] == 600
        assert body["height"] == 300
        client.close()

    @respx.mock
    def test_css_is_prepended_as_style_tag(self, mock_image_result):
        route = respx.post(f"{BASE}/image").mock(
            return_value=Response(200, json=mock_image_result)
        )
        client = Pictify(api_key="k")
        client.render_html(html="<div>Hi</div>", css="div{color:red}")

        body = _body(route)
        assert body["html"] == "<style>div{color:red}</style><div>Hi</div>"
        client.close()

    @respx.mock
    def test_format_maps_to_file_extension(self, mock_image_result):
        route = respx.post(f"{BASE}/image").mock(
            return_value=Response(200, json=mock_image_result)
        )
        client = Pictify(api_key="k")
        client.render_html(html="<div>x</div>", format="pdf")

        body = _body(route)
        assert body["fileExtension"] == "pdf"
        assert "format" not in body
        client.close()

    @respx.mock
    def test_strips_none_fields(self, mock_image_result):
        route = respx.post(f"{BASE}/image").mock(
            return_value=Response(200, json=mock_image_result)
        )
        client = Pictify(api_key="k")
        client.render_html(html="<div>x</div>")

        body = _body(route)
        assert "width" not in body
        assert "height" not in body
        assert "selector" not in body
        client.close()

    @respx.mock
    def test_sends_auth_header(self, mock_image_result):
        route = respx.post(f"{BASE}/image").mock(
            return_value=Response(200, json=mock_image_result)
        )
        client = Pictify(api_key="secret")
        client.render_html(html="<div>x</div>")

        req = route.calls.last.request
        assert req.headers["Authorization"] == "Bearer secret"
        assert "pictify-python" in req.headers["User-Agent"]
        client.close()

    @respx.mock
    def test_error(self):
        respx.post(f"{BASE}/image").mock(
            return_value=Response(422, json={"error": "Render failed", "code": "x"})
        )
        client = Pictify(api_key="k", max_retries=0)
        with pytest.raises(RenderError):
            client.render_html(html="<div>x</div>")
        client.close()


# --------------------------------------------------------------------------- #
# render_url
# --------------------------------------------------------------------------- #
class TestRenderUrl:
    @respx.mock
    def test_happy_path(self, mock_image_result):
        route = respx.post(f"{BASE}/image").mock(
            return_value=Response(200, json=mock_image_result)
        )
        client = Pictify(api_key="k")
        result = client.render_url(url="https://example.com", selector=".hero")

        assert result.url == mock_image_result["url"]
        body = _body(route)
        assert body["url"] == "https://example.com"
        assert body["selector"] == ".hero"
        assert body["fileExtension"] == "png"
        client.close()

    @respx.mock
    def test_error(self):
        respx.post(f"{BASE}/image").mock(
            return_value=Response(401, json={"message": "Invalid Request"})
        )
        client = Pictify(api_key="bad", max_retries=0)
        with pytest.raises(AuthenticationError):
            client.render_url(url="https://example.com")
        client.close()


# --------------------------------------------------------------------------- #
# render (template)
# --------------------------------------------------------------------------- #
class TestRender:
    @respx.mock
    def test_happy_path(self, mock_render_result):
        route = respx.post(f"{BASE}/templates/XL13/render").mock(
            return_value=Response(200, json=mock_render_result)
        )
        client = Pictify(api_key="k")
        result = client.render("XL13", variables={"name": "Ada", "company": "Pictify"})

        assert result.url == "https://cdn.pictify.io/renders/default.png"
        assert result.template_uid == "tmpl_abc123"
        assert result.total_rendered == 1
        assert len(result.results) == 1
        body = _body(route)
        assert body["variables"] == {"name": "Ada", "company": "Pictify"}
        assert body["format"] == "png"
        client.close()

    @respx.mock
    def test_url_encodes_template_id(self, mock_render_result):
        route = respx.post(f"{BASE}/templates/a%2Fb/render").mock(
            return_value=Response(200, json=mock_render_result)
        )
        client = Pictify(api_key="k")
        client.render("a/b")
        assert route.called
        client.close()

    @respx.mock
    def test_optional_params_sent(self, mock_render_result):
        route = respx.post(f"{BASE}/templates/XL13/render").mock(
            return_value=Response(200, json=mock_render_result)
        )
        client = Pictify(api_key="k")
        client.render(
            "XL13", format="pdf", quality=0.7, width=800, height=600, layout="square"
        )
        body = _body(route)
        assert body["format"] == "pdf"
        assert body["quality"] == 0.7
        assert body["width"] == 800
        assert body["height"] == 600
        assert body["layout"] == "square"
        client.close()

    @respx.mock
    def test_default_variables_is_empty_dict(self, mock_render_result):
        route = respx.post(f"{BASE}/templates/XL13/render").mock(
            return_value=Response(200, json=mock_render_result)
        )
        client = Pictify(api_key="k")
        client.render("XL13")
        body = _body(route)
        assert body["variables"] == {}
        client.close()

    @respx.mock
    def test_error(self):
        respx.post(f"{BASE}/templates/XL13/render").mock(
            return_value=Response(404, json={"message": "Template not found"})
        )
        client = Pictify(api_key="k", max_retries=0)
        with pytest.raises(TemplateNotFoundError):
            client.render("XL13")
        client.close()


# --------------------------------------------------------------------------- #
# render_layouts
# --------------------------------------------------------------------------- #
class TestRenderLayouts:
    @respx.mock
    def test_happy_path(self, mock_layout_render_result):
        route = respx.post(f"{BASE}/templates/XL13/render").mock(
            return_value=Response(200, json=mock_layout_render_result)
        )
        client = Pictify(api_key="k")
        result = client.render_layouts(
            "XL13", layouts=["default", "square", "bogus"], variables={"name": "Ada"}
        )
        body = _body(route)
        assert body["layouts"] == ["default", "square", "bogus"]
        assert len(result.results) == 2
        assert len(result.errors) == 1
        assert result.errors[0].layout == "bogus"
        assert result.url == "https://cdn.pictify.io/renders/default.png"
        client.close()

    @respx.mock
    def test_error(self):
        respx.post(f"{BASE}/templates/XL13/render").mock(
            return_value=Response(401, json={"message": "Invalid Request"})
        )
        client = Pictify(api_key="bad", max_retries=0)
        with pytest.raises(AuthenticationError):
            client.render_layouts("XL13", layouts=["default"])
        client.close()


# --------------------------------------------------------------------------- #
# render_gif
# --------------------------------------------------------------------------- #
class TestRenderGif:
    @respx.mock
    def test_from_html_flattens_envelope(self, mock_gif_result):
        route = respx.post(f"{BASE}/gif").mock(
            return_value=Response(200, json=mock_gif_result)
        )
        client = Pictify(api_key="k")
        result = client.render_gif(html="<div>x</div>", width=400, height=200, quality="low")

        assert result.url == "https://cdn.pictify.io/renders/abc123.gif"
        assert result.uid == "gif_abc123"
        assert result.animation_length == 2000
        body = _body(route)
        assert body["html"] == "<div>x</div>"
        assert body["quality"] == "low"
        client.close()

    @respx.mock
    def test_from_template_uses_template_key(self, mock_gif_result):
        route = respx.post(f"{BASE}/gif").mock(
            return_value=Response(200, json=mock_gif_result)
        )
        client = Pictify(api_key="k")
        client.render_gif(template_id="XL13", variables={"name": "Ada"})

        body = _body(route)
        assert body["template"] == "XL13"
        assert "template_id" not in body
        assert body["variables"] == {"name": "Ada"}
        assert body["quality"] == "medium"
        client.close()

    @respx.mock
    def test_from_url(self, mock_gif_result):
        route = respx.post(f"{BASE}/gif").mock(
            return_value=Response(200, json=mock_gif_result)
        )
        client = Pictify(api_key="k")
        client.render_gif(url="https://example.com")
        body = _body(route)
        assert body["url"] == "https://example.com"
        client.close()

    @respx.mock
    def test_error(self):
        respx.post(f"{BASE}/gif").mock(
            return_value=Response(422, json={"error": "Static source"})
        )
        client = Pictify(api_key="k", max_retries=0)
        with pytest.raises(RenderError):
            client.render_gif(html="<div>x</div>")
        client.close()


# --------------------------------------------------------------------------- #
# render_batch + get_batch_results
# --------------------------------------------------------------------------- #
class TestRenderBatch:
    @respx.mock
    def test_submit_happy_path(self, mock_batch_submit_result):
        route = respx.post(f"{BASE}/templates/XL13/batch-render").mock(
            return_value=Response(202, json=mock_batch_submit_result)
        )
        client = Pictify(api_key="k")
        result = client.render_batch(
            "XL13",
            [{"name": "A", "company": "X"}, {"name": "B", "company": "Y"}],
            format="png",
        )
        assert result.batch_id == "batch_abc123"
        assert result.status == "pending"
        assert result.total_items == 2
        body = _body(route)
        assert body["variableSets"] == [
            {"name": "A", "company": "X"},
            {"name": "B", "company": "Y"},
        ]
        assert body["format"] == "png"
        client.close()

    @respx.mock
    def test_optional_params(self, mock_batch_submit_result):
        route = respx.post(f"{BASE}/templates/XL13/batch-render").mock(
            return_value=Response(202, json=mock_batch_submit_result)
        )
        client = Pictify(api_key="k")
        client.render_batch(
            "XL13", [{"n": 1}], quality=0.8, concurrency=3, layouts=["default"]
        )
        body = _body(route)
        assert body["quality"] == 0.8
        assert body["concurrency"] == 3
        assert body["layouts"] == ["default"]
        client.close()

    @respx.mock
    def test_error(self):
        respx.post(f"{BASE}/templates/XL13/batch-render").mock(
            return_value=Response(402, json={"message": "Quota exceeded"})
        )
        client = Pictify(api_key="k", max_retries=0)
        with pytest.raises(QuotaExceededError):
            client.render_batch("XL13", [{"n": 1}])
        client.close()


class TestGetBatchResults:
    @respx.mock
    def test_happy_path(self, mock_batch_results):
        respx.get(f"{BASE}/templates/batch/batch_abc123/results").mock(
            return_value=Response(200, json=mock_batch_results)
        )
        client = Pictify(api_key="k")
        result = client.get_batch_results("batch_abc123")
        assert result.batch_id == "batch_abc123"
        assert result.status == "processing"
        assert result.total_items == 2
        assert result.completed_items == 1
        assert result.results[0].success is True
        client.close()

    @respx.mock
    def test_error(self):
        respx.get(f"{BASE}/templates/batch/missing/results").mock(
            return_value=Response(404, json={"message": "Batch not found"})
        )
        client = Pictify(api_key="k", max_retries=0)
        with pytest.raises(TemplateNotFoundError):
            client.get_batch_results("missing")
        client.close()


# --------------------------------------------------------------------------- #
# get_template
# --------------------------------------------------------------------------- #
class TestGetTemplate:
    @respx.mock
    def test_unwraps_envelope(self, mock_template_envelope):
        respx.get(f"{BASE}/templates/XL13").mock(
            return_value=Response(200, json=mock_template_envelope)
        )
        client = Pictify(api_key="k")
        template = client.get_template("XL13")
        assert template.uid == "tmpl_abc123"
        assert template.name == "OG Image Template"
        assert template.engine == "html"
        assert template.variable_definitions[0].name == "name"
        client.close()

    @respx.mock
    def test_not_found(self):
        respx.get(f"{BASE}/templates/missing").mock(
            return_value=Response(404, json={"message": "Template not found"})
        )
        client = Pictify(api_key="k", max_retries=0)
        with pytest.raises(TemplateNotFoundError):
            client.get_template("missing")
        client.close()


# --------------------------------------------------------------------------- #
# list_templates
# --------------------------------------------------------------------------- #
class TestListTemplates:
    @respx.mock
    def test_happy_path(self, mock_list_templates_result):
        respx.get(f"{BASE}/templates").mock(
            return_value=Response(200, json=mock_list_templates_result)
        )
        client = Pictify(api_key="k")
        result = client.list_templates()
        assert len(result.templates) == 1
        assert result.templates[0].uid == "tmpl_abc123"
        assert result.pagination.total == 1
        assert result.pagination.has_next is False
        client.close()

    @respx.mock
    def test_query_params(self, mock_list_templates_result):
        route = respx.get(f"{BASE}/templates").mock(
            return_value=Response(200, json=mock_list_templates_result)
        )
        client = Pictify(api_key="k")
        client.list_templates(page=2, limit=50, sort="name")
        url = str(route.calls.last.request.url)
        assert "page=2" in url
        assert "limit=50" in url
        assert "sort=name" in url
        client.close()

    @respx.mock
    def test_no_params_no_query(self, mock_list_templates_result):
        route = respx.get(f"{BASE}/templates").mock(
            return_value=Response(200, json=mock_list_templates_result)
        )
        client = Pictify(api_key="k")
        client.list_templates()
        assert str(route.calls.last.request.url) == f"{BASE}/templates"
        client.close()

    @respx.mock
    def test_error(self):
        respx.get(f"{BASE}/templates").mock(
            return_value=Response(401, json={"message": "Invalid Request"})
        )
        client = Pictify(api_key="bad", max_retries=0)
        with pytest.raises(AuthenticationError):
            client.list_templates()
        client.close()


# --------------------------------------------------------------------------- #
# create_template
# --------------------------------------------------------------------------- #
class TestCreateTemplate:
    @respx.mock
    def test_happy_path(self, mock_template_envelope):
        route = respx.post(f"{BASE}/templates").mock(
            return_value=Response(200, json=mock_template_envelope)
        )
        client = Pictify(api_key="k")
        template = client.create_template(
            html="<div>Hi {{name}}</div>", name="Welcome", width=400, height=150
        )
        assert template.uid == "tmpl_abc123"
        body = _body(route)
        assert body["html"] == "<div>Hi {{name}}</div>"
        assert body["name"] == "Welcome"
        assert body["width"] == 400
        client.close()

    @respx.mock
    def test_with_variable_definitions(self, mock_template_envelope):
        route = respx.post(f"{BASE}/templates").mock(
            return_value=Response(200, json=mock_template_envelope)
        )
        client = Pictify(api_key="k")
        client.create_template(
            html="<div>{{x}}</div>",
            variable_definitions=[{"name": "x", "type": "string"}],
            output_format="pdf",
        )
        body = _body(route)
        assert body["variableDefinitions"] == [{"name": "x", "type": "string"}]
        assert body["outputFormat"] == "pdf"
        client.close()

    @respx.mock
    def test_error(self):
        respx.post(f"{BASE}/templates").mock(
            return_value=Response(422, json={"message": "Validation failed", "errors": ["x"]})
        )
        client = Pictify(api_key="k", max_retries=0)
        with pytest.raises(RenderError) as exc:
            client.create_template(html="<div>x</div>")
        assert exc.value.errors == ["x"]
        client.close()


# --------------------------------------------------------------------------- #
# Error mapping, retries, transport
# --------------------------------------------------------------------------- #
class TestErrorMapping:
    @respx.mock
    def test_429_quota_code_is_quota_error(self):
        respx.post(f"{BASE}/image").mock(
            return_value=Response(429, json={"message": "limit", "code": "quota_exceeded"})
        )
        client = Pictify(api_key="k", max_retries=0)
        with pytest.raises(QuotaExceededError):
            client.render_html(html="<div>x</div>")
        client.close()

    @respx.mock
    def test_429_without_quota_code_is_rate_limit(self):
        respx.post(f"{BASE}/image").mock(
            return_value=Response(429, json={"message": "slow down"})
        )
        client = Pictify(api_key="k", max_retries=0)
        with pytest.raises(RateLimitError):
            client.render_html(html="<div>x</div>")
        client.close()

    @respx.mock
    def test_5xx_is_server_error(self):
        respx.post(f"{BASE}/image").mock(
            return_value=Response(500, json={"message": "boom"})
        )
        client = Pictify(api_key="k", max_retries=0)
        with pytest.raises(ServerError):
            client.render_html(html="<div>x</div>")
        client.close()

    @respx.mock
    def test_error_message_precedence_error_over_message(self):
        respx.post(f"{BASE}/image").mock(
            return_value=Response(422, json={"error": "E", "message": "M"})
        )
        client = Pictify(api_key="k", max_retries=0)
        with pytest.raises(RenderError) as exc:
            client.render_html(html="<div>x</div>")
        assert exc.value.message == "E"
        client.close()

    @respx.mock
    def test_non_json_error_uses_text(self):
        respx.post(f"{BASE}/image").mock(
            return_value=Response(403, text="Forbidden")
        )
        client = Pictify(api_key="k", max_retries=0)
        with pytest.raises(PictifyError) as exc:
            client.render_html(html="<div>x</div>")
        assert exc.value.status_code == 403
        client.close()


class TestRetries:
    @respx.mock
    def test_retries_on_5xx_then_succeeds(self, monkeypatch, mock_image_result):
        monkeypatch.setattr("pictify.client.time.sleep", lambda _s: None)
        route = respx.post(f"{BASE}/image").mock(
            side_effect=[
                Response(500, json={"message": "e1"}),
                Response(500, json={"message": "e2"}),
                Response(200, json=mock_image_result),
            ]
        )
        client = Pictify(api_key="k", max_retries=3)
        result = client.render_html(html="<div>x</div>")
        assert result.url == mock_image_result["url"]
        assert len(route.calls) == 3
        client.close()

    @respx.mock
    def test_does_not_retry_on_4xx(self):
        route = respx.post(f"{BASE}/image").mock(
            return_value=Response(422, json={"error": "bad"})
        )
        client = Pictify(api_key="k", max_retries=3)
        with pytest.raises(RenderError):
            client.render_html(html="<div>x</div>")
        assert len(route.calls) == 1
        client.close()

    @respx.mock
    def test_max_retries_exhausted_raises_server_error(self, monkeypatch):
        monkeypatch.setattr("pictify.client.time.sleep", lambda _s: None)
        respx.post(f"{BASE}/image").mock(
            return_value=Response(500, json={"message": "boom"})
        )
        client = Pictify(api_key="k", max_retries=2)
        with pytest.raises(ServerError):
            client.render_html(html="<div>x</div>")
        client.close()


class TestTransportErrors:
    @respx.mock
    def test_timeout_raises_timeout_error(self):
        respx.post(f"{BASE}/image").mock(side_effect=httpx.TimeoutException("t"))
        client = Pictify(api_key="k", max_retries=0)
        with pytest.raises(TimeoutError):
            client.render_html(html="<div>x</div>")
        client.close()

    @respx.mock
    def test_network_error_raises_network_error(self):
        respx.post(f"{BASE}/image").mock(side_effect=httpx.ConnectError("refused"))
        client = Pictify(api_key="k", max_retries=0)
        with pytest.raises(NetworkError):
            client.render_html(html="<div>x</div>")
        client.close()

    @respx.mock
    def test_network_error_retries_then_succeeds(self, monkeypatch, mock_image_result):
        monkeypatch.setattr("pictify.client.time.sleep", lambda _s: None)
        route = respx.post(f"{BASE}/image").mock(
            side_effect=[httpx.ConnectError("refused"), Response(200, json=mock_image_result)]
        )
        client = Pictify(api_key="k", max_retries=3)
        result = client.render_html(html="<div>x</div>")
        assert result.url == mock_image_result["url"]
        assert len(route.calls) == 2
        client.close()
