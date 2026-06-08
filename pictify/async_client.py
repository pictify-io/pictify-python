"""Asynchronous Pictify client.

Generate images, PDFs, and GIFs from raw HTML, live URLs, and reusable
templates via the real Pictify API (https://api.pictify.io).
"""

import asyncio
from typing import Any, Dict, List, Optional
from urllib.parse import quote, urlencode

import httpx

from pictify.errors import (
    NetworkError,
    TimeoutError,
    create_error_from_response,
)
from pictify.types import (
    BatchRenderResult,
    BatchResults,
    GifQuality,
    GifRenderResult,
    ImageFormat,
    ImageResult,
    ListTemplatesResult,
    RenderResult,
    Template,
)

__all__ = ["AsyncPictify"]

SDK_VERSION = "1.0.0"


def _strip_none(body: Dict[str, Any]) -> Dict[str, Any]:
    """Drop ``None`` fields so the backend applies its own defaults."""
    return {k: v for k, v in body.items() if v is not None}


class AsyncPictify:
    """Asynchronous client for the Pictify API.

    Example:
        >>> async with AsyncPictify(api_key="your-api-key") as client:
        ...     image = await client.render_html(html="<div>Hello World</div>")
        ...     print(image.url)
    """

    DEFAULT_BASE_URL = "https://api.pictify.io"
    DEFAULT_TIMEOUT = 30.0
    MAX_RETRIES = 3
    RETRY_DELAY = 1.0

    def __init__(
        self,
        api_key: str,
        *,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
    ) -> None:
        """Initialize the async Pictify client.

        Args:
            api_key: Your Pictify API key.
            base_url: Custom API base URL (default: https://api.pictify.io).
            timeout: Request timeout in seconds (default: 30).
            max_retries: Max retries for 5xx/network failures (default: 3).
        """
        self.api_key = api_key
        self.base_url = (base_url or self.DEFAULT_BASE_URL).rstrip("/")
        self.timeout = timeout or self.DEFAULT_TIMEOUT
        self.max_retries = max_retries if max_retries is not None else self.MAX_RETRIES

        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": f"pictify-python/{SDK_VERSION}",
            },
            timeout=self.timeout,
        )

    async def __aenter__(self) -> "AsyncPictify":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Make an authenticated JSON request with retries on 5xx/network.

        Retries ONLY on 5xx and network errors (never on 4xx). Returns the parsed
        JSON body, or raises a typed :class:`PictifyError` on HTTP errors.
        """
        payload = _strip_none(json) if json is not None else None
        last_error: Optional[Exception] = None

        for attempt in range(self.max_retries + 1):
            try:
                response = await self._client.request(method, path, json=payload)
            except httpx.TimeoutException as e:
                last_error = TimeoutError(
                    f"Request timed out after {self.timeout}s", self.timeout
                )
                if attempt < self.max_retries:
                    await asyncio.sleep(self.RETRY_DELAY * (2**attempt))
                    continue
                raise last_error from e
            except httpx.RequestError as e:
                last_error = NetworkError(str(e), e)
                if attempt < self.max_retries:
                    await asyncio.sleep(self.RETRY_DELAY * (2**attempt))
                    continue
                raise last_error from e

            # Retry on server errors only.
            if response.status_code >= 500 and attempt < self.max_retries:
                last_error = create_error_from_response(response.status_code, None)
                await asyncio.sleep(self.RETRY_DELAY * (2**attempt))
                continue

            if response.status_code >= 400:
                try:
                    body = response.json()
                except Exception:
                    body = {"message": response.text}
                raise create_error_from_response(response.status_code, body)

            try:
                return response.json()
            except Exception:
                return None

        raise last_error or NetworkError("Request failed after all retries")

    # ------------------------------------------------------------------ #
    # Image rendering (POST /image)
    # ------------------------------------------------------------------ #

    async def render_html(
        self,
        html: str,
        *,
        css: Optional[str] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        selector: Optional[str] = None,
        format: Optional[ImageFormat] = None,
    ) -> ImageResult:
        """Render an image (or PDF) directly from HTML. ``POST /image``.

        Args:
            html: Raw HTML content to render.
            css: Optional CSS — inlined into a ``<style>`` tag before the HTML.
            width: Output width in pixels (default: 1280).
            height: Output height in pixels (default: 720).
            selector: CSS selector to crop the screenshot to a specific element.
            format: Output format, mapped to ``fileExtension`` (default: png).

        Returns:
            ImageResult with ``url``, ``id``, and ``created_at``.
        """
        if css:
            html = f"<style>{css}</style>{html}"

        data = await self._request(
            "POST",
            "/image",
            json={
                "html": html,
                "width": width,
                "height": height,
                "selector": selector,
                "fileExtension": format or "png",
            },
        )
        return ImageResult.model_validate(data)

    async def render_url(
        self,
        url: str,
        *,
        width: Optional[int] = None,
        height: Optional[int] = None,
        selector: Optional[str] = None,
        format: Optional[ImageFormat] = None,
    ) -> ImageResult:
        """Screenshot a live URL. ``POST /image`` with ``url``.

        Args:
            url: The URL to screenshot.
            width: Output width in pixels (default: 1280).
            height: Output height in pixels (default: 720).
            selector: CSS selector to crop the screenshot to a specific element.
            format: Output format, mapped to ``fileExtension`` (default: png).

        Returns:
            ImageResult with ``url``, ``id``, and ``created_at``.
        """
        data = await self._request(
            "POST",
            "/image",
            json={
                "url": url,
                "width": width,
                "height": height,
                "selector": selector,
                "fileExtension": format or "png",
            },
        )
        return ImageResult.model_validate(data)

    # ------------------------------------------------------------------ #
    # Template rendering (POST /templates/:uid/render)
    # ------------------------------------------------------------------ #

    async def render(
        self,
        template_id: str,
        *,
        variables: Optional[Dict[str, Any]] = None,
        format: Optional[ImageFormat] = None,
        quality: Optional[float] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        layout: Optional[str] = None,
        layouts: Optional[List[str]] = None,
    ) -> RenderResult:
        """Render a single image (or PDF) from a template.

        ``POST /templates/:uid/render`` — returns the ``results[]`` envelope. Use
        the ``result.url`` property for ``results[0].url``.

        Args:
            template_id: The UID of the template to render.
            variables: Variables to inject into the template.
            format: Output format (default: png; ``pdf`` is supported).
            quality: Render quality for raster/JPEG output (0.1-1.0, default: 0.9).
            width: Output width in pixels.
            height: Output height in pixels.
            layout: Render a single named layout variant.
            layouts: Render multiple named layout variants (max 20).

        Returns:
            RenderResult with a ``results`` list and a ``url`` convenience property.
        """
        data = await self._request(
            "POST",
            f"/templates/{quote(template_id, safe='')}/render",
            json={
                "variables": variables or {},
                "format": format or "png",
                "quality": quality,
                "width": width,
                "height": height,
                "layout": layout,
                "layouts": layouts,
            },
        )
        return RenderResult.model_validate(data)

    async def render_layouts(
        self,
        template_id: str,
        layouts: List[str],
        *,
        variables: Optional[Dict[str, Any]] = None,
        format: Optional[ImageFormat] = None,
        quality: Optional[float] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
    ) -> RenderResult:
        """Render multiple layout variants of a template in a single call.

        Convenience wrapper around :meth:`render` with ``layouts``.
        ``POST /templates/:uid/render`` — one ``results[]`` item per successful
        layout; missing/invalid layouts appear in ``errors[]``.

        Args:
            template_id: The UID of the template to render.
            layouts: Layout variant names to render (max 20). Use ``default`` for base.
            variables: Variables to inject into the template.
            format: Output format (default: png).
            quality: Render quality (0.1-1.0).
            width: Output width in pixels.
            height: Output height in pixels.

        Returns:
            RenderResult with one ``results`` item per rendered layout.
        """
        return await self.render(
            template_id,
            variables=variables,
            format=format,
            quality=quality,
            width=width,
            height=height,
            layouts=layouts,
        )

    # ------------------------------------------------------------------ #
    # GIF rendering (POST /gif)
    # ------------------------------------------------------------------ #

    async def render_gif(
        self,
        *,
        html: Optional[str] = None,
        url: Optional[str] = None,
        template_id: Optional[str] = None,
        variables: Optional[Dict[str, Any]] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        quality: Optional[GifQuality] = None,
    ) -> GifRenderResult:
        """Render an animated GIF from raw HTML, a live URL, or a template.

        ``POST /gif`` — the ``{gif: {...}}`` envelope is flattened to
        ``{url, uid, width, height, animation_length}``. Provide exactly one
        source: ``html``, ``url``, or ``template_id``.

        Args:
            html: Raw HTML to render into a GIF (must contain CSS animation).
            url: A live URL to capture motion from.
            template_id: A template UID to render into a GIF.
            variables: Variables to inject when using ``template_id``.
            width: Output width in pixels (default: 800).
            height: Output height in pixels (default: 600).
            quality: Quality preset — ``low``, ``medium``, or ``high`` (default: medium).

        Returns:
            GifRenderResult with the flattened GIF fields.
        """
        body: Dict[str, Any] = {
            "width": width,
            "height": height,
            "quality": quality or "medium",
        }
        if html is not None:
            body["html"] = html
        if url is not None:
            body["url"] = url
        if template_id is not None:
            body["template"] = template_id
        if variables is not None:
            body["variables"] = variables

        data = await self._request("POST", "/gif", json=body)
        return GifRenderResult.model_validate((data or {}).get("gif", data))

    # ------------------------------------------------------------------ #
    # Batch rendering (async)
    # ------------------------------------------------------------------ #

    async def render_batch(
        self,
        template_id: str,
        variable_sets: List[Dict[str, Any]],
        *,
        format: Optional[ImageFormat] = None,
        quality: Optional[float] = None,
        concurrency: Optional[int] = None,
        layout: Optional[str] = None,
        layouts: Optional[List[str]] = None,
    ) -> BatchRenderResult:
        """Submit an async batch render of a template across many variable sets.

        ``POST /templates/:uid/batch-render`` — returns ``{batch_id, status,
        total_items}`` immediately (HTTP 202). Poll :meth:`get_batch_results` to
        track progress. Rendered URLs are NOT returned by the poll endpoint — they
        are delivered via the ``render.completed`` webhook.

        Args:
            template_id: The UID of the template to render.
            variable_sets: Variable sets — one render per set (max 100).
            format: Output format (default: png).
            quality: Render quality (0.1-1.0, default: 0.9).
            concurrency: Maximum parallel renders (1-10, default: 5).
            layout: Render a single named layout variant for every item.
            layouts: Render multiple named layout variants for every item (max 20).

        Returns:
            BatchRenderResult with ``batch_id``, ``status``, and ``total_items``.
        """
        data = await self._request(
            "POST",
            f"/templates/{quote(template_id, safe='')}/batch-render",
            json={
                "variableSets": variable_sets,
                "format": format or "png",
                "quality": quality,
                "concurrency": concurrency,
                "layout": layout,
                "layouts": layouts,
            },
        )
        return BatchRenderResult.model_validate(data)

    async def get_batch_results(self, batch_id: str) -> BatchResults:
        """Get the status, progress, and per-item results of a batch job.

        ``GET /templates/batch/:batchId/results``. Per-item records carry
        ``{index, success, variables}`` (and ``error`` on failures) but NOT
        rendered URLs.

        Args:
            batch_id: The batch job ID returned by :meth:`render_batch`.

        Returns:
            BatchResults with status, progress, and per-item records.
        """
        data = await self._request(
            "GET",
            f"/templates/batch/{quote(batch_id, safe='')}/results",
        )
        return BatchResults.model_validate(data)

    # ------------------------------------------------------------------ #
    # Template CRUD
    # ------------------------------------------------------------------ #

    async def get_template(self, template_id: str) -> Template:
        """Get a single template by its UID. ``GET /templates/:uid``.

        Unwraps the ``{template}`` envelope.

        Args:
            template_id: The UID of the template to retrieve.

        Returns:
            Template with metadata and variable definitions.
        """
        data = await self._request("GET", f"/templates/{quote(template_id, safe='')}")
        return Template.model_validate((data or {}).get("template", data))

    async def list_templates(
        self,
        *,
        page: Optional[int] = None,
        limit: Optional[int] = None,
        sort: Optional[str] = None,
    ) -> ListTemplatesResult:
        """List templates in your account. ``GET /templates``.

        Args:
            page: Page number (1-based, default: 1).
            limit: Items per page (max 100, default: 12).
            sort: Sort order (``newest`` | ``oldest`` | ``name``).

        Returns:
            ListTemplatesResult with ``templates`` and ``pagination``.
        """
        params: Dict[str, Any] = {}
        if page is not None:
            params["page"] = page
        if limit is not None:
            params["limit"] = limit
        if sort is not None:
            params["sort"] = sort
        query = f"?{urlencode(params)}" if params else ""

        data = await self._request("GET", f"/templates{query}")
        return ListTemplatesResult.model_validate(data)

    async def create_template(
        self,
        html: str,
        *,
        name: Optional[str] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        variable_definitions: Optional[List[Dict[str, Any]]] = None,
        output_format: Optional[str] = None,
    ) -> Template:
        """Create a template from HTML. ``POST /templates``.

        Variables are auto-discovered from ``{{variableName}}`` tokens in the HTML.
        Unwraps the ``{template}`` envelope.

        Args:
            html: Raw HTML body.
            name: Template name.
            width: Default width in pixels.
            height: Default height in pixels.
            variable_definitions: Explicit variable definitions (auto-extracted when omitted).
            output_format: Output format (``image`` | ``pdf``, default: image).

        Returns:
            The created Template.
        """
        data = await self._request(
            "POST",
            "/templates",
            json={
                "html": html,
                "name": name,
                "width": width,
                "height": height,
                "variableDefinitions": variable_definitions,
                "outputFormat": output_format,
            },
        )
        return Template.model_validate((data or {}).get("template", data))
