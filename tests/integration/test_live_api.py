"""Live integration tests against the REAL Pictify API.

Every public method on both the synchronous ``Pictify`` and asynchronous
``AsyncPictify`` client is exercised here. These make real network calls and
create real renders (which consumes quota), so the suite is SKIPPED entirely
when ``PICTIFY_API_KEY`` is absent — safe to collect in CI without credentials.

Run live::

    PICTIFY_API_KEY=xxx PICTIFY_TEMPLATE_ID=XL13XACH2V \\
        .venv/bin/python -m pytest tests/integration -v

Optional environment variables:

- ``PICTIFY_API_KEY``     (required) API key used for all requests.
- ``PICTIFY_BASE_URL``    (optional) override the API base URL.
- ``PICTIFY_TEMPLATE_ID`` (optional) a real template UID (variables: name, company).
                          Template-dependent cases skip when it is absent.
"""

import os
import re

import pytest

from pictify import (
    BatchRenderResult,
    BatchResults,
    GifRenderResult,
    ImageResult,
    ListTemplatesResult,
    RenderResult,
    Template,
)
from pictify.errors import PictifyError, TemplateNotFoundError

# Mark the whole module so `pytest -m integration` / `-m "not integration"` work.
pytestmark = pytest.mark.integration

requires_api_key = pytest.mark.skipif(
    not os.environ.get("PICTIFY_API_KEY"),
    reason="PICTIFY_API_KEY not set; skipping live integration tests",
)
requires_template = pytest.mark.skipif(
    not os.environ.get("PICTIFY_TEMPLATE_ID"),
    reason="PICTIFY_TEMPLATE_ID not set; skipping template-dependent integration test",
)

URL_RE = re.compile(r"^https?://")

ANIMATED_HTML = (
    "<style>@keyframes p{0%{opacity:.2}50%{opacity:1}100%{opacity:.2}}"
    "div{font-size:40px;padding:30px;background:#fff;animation:p 2s infinite}</style>"
    "<div>gif test</div>"
)

BATCH_STATUSES = {"pending", "processing", "completed", "partial", "failed", "cancelled"}


# --------------------------------------------------------------------------- #
# Synchronous client
# --------------------------------------------------------------------------- #
@requires_api_key
class TestSyncLive:
    """Live coverage for every public method on the sync Pictify client."""

    def test_render_html(self, client):
        result = client.render_html(
            html="<div style='font-size:48px;padding:40px;background:#fff'>Integration test</div>",
            width=600,
            height=300,
        )
        assert isinstance(result, ImageResult)
        assert URL_RE.match(result.url)
        assert result.id
        print("[integration][sync] render_html ->", result.url)

    def test_render_url(self, client):
        result = client.render_url(url="https://example.com", width=800, height=600)
        assert isinstance(result, ImageResult)
        assert URL_RE.match(result.url)
        print("[integration][sync] render_url ->", result.url)

    @requires_template
    def test_render(self, client, template_id):
        result = client.render(
            template_id, variables={"name": "Ada", "company": "Pictify"}, format="png"
        )
        assert isinstance(result, RenderResult)
        assert len(result.results) > 0
        assert URL_RE.match(result.url)
        assert result.template_uid == template_id
        print("[integration][sync] render ->", result.url)

    @requires_template
    def test_render_layouts(self, client, template_id):
        result = client.render_layouts(
            template_id,
            layouts=["default", "definitely-not-a-real-layout"],
            variables={"name": "Ada", "company": "Pictify"},
        )
        assert isinstance(result, RenderResult)
        default_item = next((r for r in result.results if r.layout == "default"), None)
        assert default_item is not None
        assert URL_RE.match(default_item.url)
        assert any(e.layout == "definitely-not-a-real-layout" for e in result.errors)
        print(
            "[integration][sync] render_layouts -> default:",
            default_item.url,
            "| errors:",
            [e.layout for e in result.errors],
        )

    def test_render_gif(self, client):
        result = client.render_gif(html=ANIMATED_HTML, width=400, height=200, quality="low")
        assert isinstance(result, GifRenderResult)
        assert URL_RE.match(result.url)
        assert result.uid
        print("[integration][sync] render_gif ->", result.url)

    def test_list_templates(self, client):
        result = client.list_templates(limit=5)
        assert isinstance(result, ListTemplatesResult)
        assert isinstance(result.templates, list)
        assert result.pagination is not None
        print(
            "[integration][sync] list_templates -> total:",
            result.pagination.total,
            "| page size:",
            len(result.templates),
        )

    @requires_template
    def test_get_template(self, client, template_id):
        template = client.get_template(template_id)
        assert isinstance(template, Template)
        assert template.uid == template_id
        print("[integration][sync] get_template ->", template.uid, template.name)

    def test_create_template(self, client):
        import time

        template = client.create_template(
            html="<div style='padding:20px;font-size:24px'>Hi {{firstName}}</div>",
            name=f"SDK py integration throwaway {int(time.time())}",
            width=400,
            height=150,
        )
        assert isinstance(template, Template)
        assert template.uid
        names = [v.name for v in (template.variable_definitions or [])]
        assert "firstName" in names
        print("[integration][sync] create_template -> uid:", template.uid)

    @requires_template
    def test_render_batch_and_results(self, client, template_id):
        submit = client.render_batch(
            template_id,
            [{"name": "A", "company": "X"}, {"name": "B", "company": "Y"}],
            format="png",
        )
        assert isinstance(submit, BatchRenderResult)
        assert submit.batch_id
        assert submit.total_items == 2
        print("[integration][sync] render_batch -> batchId:", submit.batch_id, submit.status)

        results = client.get_batch_results(submit.batch_id)
        assert isinstance(results, BatchResults)
        assert results.batch_id == submit.batch_id
        assert results.total_items == 2
        assert results.status in BATCH_STATUSES
        print(
            "[integration][sync] get_batch_results -> status:",
            results.status,
            "| completed:",
            results.completed_items,
        )

    def test_template_not_found(self, client):
        with pytest.raises(PictifyError) as exc:
            client.get_template("definitely-not-a-real-template-id-xyz")
        assert isinstance(exc.value, TemplateNotFoundError)


# --------------------------------------------------------------------------- #
# Asynchronous client
# --------------------------------------------------------------------------- #
@requires_api_key
class TestAsyncLive:
    """Live coverage for every public method on the AsyncPictify client."""

    @pytest.mark.asyncio
    async def test_render_html(self, async_client):
        result = await async_client.render_html(
            html="<div style='font-size:48px;padding:40px;background:#fff'>Async integration</div>",
            width=600,
            height=300,
        )
        assert isinstance(result, ImageResult)
        assert URL_RE.match(result.url)
        print("[integration][async] render_html ->", result.url)

    @pytest.mark.asyncio
    async def test_render_url(self, async_client):
        result = await async_client.render_url(url="https://example.com", width=800, height=600)
        assert URL_RE.match(result.url)
        print("[integration][async] render_url ->", result.url)

    @requires_template
    @pytest.mark.asyncio
    async def test_render(self, async_client, template_id):
        result = await async_client.render(
            template_id, variables={"name": "Ada", "company": "Pictify"}, format="png"
        )
        assert isinstance(result, RenderResult)
        assert URL_RE.match(result.url)
        assert result.template_uid == template_id
        print("[integration][async] render ->", result.url)

    @requires_template
    @pytest.mark.asyncio
    async def test_render_layouts(self, async_client, template_id):
        result = await async_client.render_layouts(
            template_id,
            layouts=["default", "definitely-not-a-real-layout"],
            variables={"name": "Ada", "company": "Pictify"},
        )
        default_item = next((r for r in result.results if r.layout == "default"), None)
        assert default_item is not None
        assert URL_RE.match(default_item.url)
        assert any(e.layout == "definitely-not-a-real-layout" for e in result.errors)
        print(
            "[integration][async] render_layouts -> default:",
            default_item.url,
            "| errors:",
            [e.layout for e in result.errors],
        )

    @pytest.mark.asyncio
    async def test_render_gif(self, async_client):
        result = await async_client.render_gif(
            html=ANIMATED_HTML, width=400, height=200, quality="low"
        )
        assert isinstance(result, GifRenderResult)
        assert URL_RE.match(result.url)
        assert result.uid
        print("[integration][async] render_gif ->", result.url)

    @pytest.mark.asyncio
    async def test_list_templates(self, async_client):
        result = await async_client.list_templates(limit=5)
        assert isinstance(result, ListTemplatesResult)
        assert result.pagination is not None
        print(
            "[integration][async] list_templates -> total:",
            result.pagination.total,
            "| page size:",
            len(result.templates),
        )

    @requires_template
    @pytest.mark.asyncio
    async def test_get_template(self, async_client, template_id):
        template = await async_client.get_template(template_id)
        assert isinstance(template, Template)
        assert template.uid == template_id
        print("[integration][async] get_template ->", template.uid, template.name)

    @pytest.mark.asyncio
    async def test_create_template(self, async_client):
        import time

        template = await async_client.create_template(
            html="<div style='padding:20px;font-size:24px'>Hi {{firstName}}</div>",
            name=f"SDK py async throwaway {int(time.time())}",
            width=400,
            height=150,
        )
        assert isinstance(template, Template)
        assert template.uid
        names = [v.name for v in (template.variable_definitions or [])]
        assert "firstName" in names
        print("[integration][async] create_template -> uid:", template.uid)

    @requires_template
    @pytest.mark.asyncio
    async def test_render_batch_and_results(self, async_client, template_id):
        submit = await async_client.render_batch(
            template_id,
            [{"name": "A", "company": "X"}, {"name": "B", "company": "Y"}],
            format="png",
        )
        assert isinstance(submit, BatchRenderResult)
        assert submit.batch_id
        assert submit.total_items == 2
        print("[integration][async] render_batch -> batchId:", submit.batch_id, submit.status)

        results = await async_client.get_batch_results(submit.batch_id)
        assert isinstance(results, BatchResults)
        assert results.batch_id == submit.batch_id
        assert results.status in BATCH_STATUSES
        print(
            "[integration][async] get_batch_results -> status:",
            results.status,
            "| completed:",
            results.completed_items,
        )

    @pytest.mark.asyncio
    async def test_template_not_found(self, async_client):
        with pytest.raises(PictifyError) as exc:
            await async_client.get_template("definitely-not-a-real-template-id-xyz")
        assert isinstance(exc.value, TemplateNotFoundError)
