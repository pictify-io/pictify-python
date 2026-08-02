"""Synchronous Pictify client.

Generate images, PDFs, and GIFs from raw HTML, live URLs, and reusable
templates via the real Pictify API (https://api.pictify.io).
"""

import time
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
    GenerateVideoTemplateResult,
    GifQuality,
    GifRenderResult,
    ImageFormat,
    ImageResult,
    ListTemplatesResult,
    RenderResult,
    RenderVideoResult,
    Template,
    VideoFormat,
    VideoTemplate,
    VideoTemplateVariables,
)

__all__ = ["Pictify"]

SDK_VERSION = "1.0.0"


def _strip_none(body: Dict[str, Any]) -> Dict[str, Any]:
    """Drop ``None`` fields so the backend applies its own defaults."""
    return {k: v for k, v in body.items() if v is not None}


class Pictify:
    """Synchronous client for the Pictify API.

    Example:
        >>> client = Pictify(api_key="your-api-key")
        >>> image = client.render_html(html="<div>Hello World</div>")
        >>> print(image.url)
    """

    DEFAULT_BASE_URL = "https://api.pictify.io"
    DEFAULT_TIMEOUT = 30.0
    # Video renders legitimately run minutes — per-call defaults, independent
    # of the client-wide `timeout`.
    VIDEO_RENDER_TIMEOUT = 300.0
    VIDEO_TEMPLATE_TIMEOUT = 180.0
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
        """Initialize the Pictify client.

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

        self._client = httpx.Client(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": f"pictify-python/{SDK_VERSION}",
            },
            timeout=self.timeout,
        )

    def __enter__(self) -> "Pictify":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._client.close()

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> Any:
        """Make an authenticated JSON request with retries on 5xx/network.

        Retries ONLY on 5xx and network errors (never on 4xx). Returns the parsed
        JSON body, or raises a typed :class:`PictifyError` on HTTP errors.

        ``timeout`` overrides the client-wide timeout for this request only —
        video renders legitimately run minutes.
        """
        payload = _strip_none(json) if json is not None else None
        request_timeout = self.timeout if timeout is None else timeout
        last_error: Optional[Exception] = None

        for attempt in range(self.max_retries + 1):
            try:
                response = self._client.request(
                    method, path, json=payload, timeout=request_timeout
                )
            except httpx.TimeoutException as e:
                last_error = TimeoutError(
                    f"Request timed out after {request_timeout}s", request_timeout
                )
                if attempt < self.max_retries:
                    time.sleep(self.RETRY_DELAY * (2**attempt))
                    continue
                raise last_error from e
            except httpx.RequestError as e:
                last_error = NetworkError(str(e), e)
                if attempt < self.max_retries:
                    time.sleep(self.RETRY_DELAY * (2**attempt))
                    continue
                raise last_error from e

            # Retry on server errors only.
            if response.status_code >= 500 and attempt < self.max_retries:
                last_error = create_error_from_response(response.status_code, None)
                time.sleep(self.RETRY_DELAY * (2**attempt))
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

    def render_html(
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

        data = self._request(
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

    def render_url(
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
        data = self._request(
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

    def render(
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
        data = self._request(
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

    def render_layouts(
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
        return self.render(
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

    def render_gif(
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

        data = self._request("POST", "/gif", json=body)
        return GifRenderResult.model_validate((data or {}).get("gif", data))

    # ------------------------------------------------------------------ #
    # Batch rendering (async)
    # ------------------------------------------------------------------ #

    def render_batch(
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
        data = self._request(
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

    def get_batch_results(self, batch_id: str) -> BatchResults:
        """Get the status, progress, and per-item results of a batch job.

        ``GET /templates/batch/:batchId/results``. Per-item records carry
        ``{index, success, variables}`` (and ``error`` on failures) but NOT
        rendered URLs.

        Args:
            batch_id: The batch job ID returned by :meth:`render_batch`.

        Returns:
            BatchResults with status, progress, and per-item records.
        """
        data = self._request(
            "GET",
            f"/templates/batch/{quote(batch_id, safe='')}/results",
        )
        return BatchResults.model_validate(data)

    # ------------------------------------------------------------------ #
    # Template CRUD
    # ------------------------------------------------------------------ #

    def get_template(self, template_id: str) -> Template:
        """Get a single template by its UID. ``GET /templates/:uid``.

        Unwraps the ``{template}`` envelope.

        Args:
            template_id: The UID of the template to retrieve.

        Returns:
            Template with metadata and variable definitions.
        """
        data = self._request("GET", f"/templates/{quote(template_id, safe='')}")
        return Template.model_validate((data or {}).get("template", data))

    def list_templates(
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

        data = self._request("GET", f"/templates{query}")
        return ListTemplatesResult.model_validate(data)

    def create_template(
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
        data = self._request(
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

    # ------------------------------------------------------------------ #
    # Video templates
    # ------------------------------------------------------------------ #

    def list_video_templates(self) -> List[VideoTemplate]:
        """List your video templates. ``GET /video/templates``.

        Unwraps the ``{templates}`` envelope.

        Returns:
            List of VideoTemplate.
        """
        data = self._request("GET", "/video/templates")
        return [
            VideoTemplate.model_validate(t) for t in (data or {}).get("templates") or []
        ]

    def get_video_template_variables(self, template_id: str) -> VideoTemplateVariables:
        """Get a video template's variable definitions — what you can set when
        rendering it. Call before :meth:`render_video` to know what to pass.

        ``GET /video/templates/:uid/variables``.

        Args:
            template_id: The UID of the video template.

        Returns:
            VideoTemplateVariables with ``variables`` and ``referenced`` names.
        """
        data = self._request(
            "GET", f"/video/templates/{quote(template_id, safe='')}/variables"
        )
        return VideoTemplateVariables.model_validate(data)

    def render_video(
        self,
        template_id: str,
        *,
        variables: Optional[Dict[str, Any]] = None,
        format: Optional[VideoFormat] = None,
        timeout: Optional[float] = None,
    ) -> RenderVideoResult:
        """Render a video template to MP4 — or an animated GIF — with variables.

        ``POST /video/templates/:uid/render``. The request WAITS for the finished
        file (up to a few minutes) and returns its hosted URL. Each render
        consumes one video credit. Omitted variables render their defaults;
        unknown variable names fail with a 422.

        Args:
            template_id: The UID of the video template to render.
            variables: Variables to inject into the template.
            format: Output format (default: mp4). ``gif`` is a palette-optimised
                animated GIF capped at 15fps / 720px wide.
            timeout: Per-call timeout in seconds (default: 300 — video renders
                take minutes).

        Returns:
            RenderVideoResult with ``url``, ``duration_in_frames``, and ``format``.
        """
        data = self._request(
            "POST",
            f"/video/templates/{quote(template_id, safe='')}/render",
            json={
                "variables": variables or {},
                "format": format or "mp4",
            },
            timeout=timeout if timeout is not None else self.VIDEO_RENDER_TIMEOUT,
        )
        return RenderVideoResult.model_validate(data)

    def generate_video_template(
        self,
        prompt: str,
        *,
        width: int = 1080,
        height: int = 1080,
        duration_seconds: float = 8,
        brand_color: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> GenerateVideoTemplateResult:
        """Generate a new video template from a prompt using AI.

        ``POST /video/templates/generate``. The service designs a motion brief,
        writes the scene as code, compiles it, renders preview frames and reviews
        them visually — then saves a draft template whose texts, colors and
        optional image are editable variables. Takes 30-60 seconds; metered as
        one render.

        Args:
            prompt: What the video is for, with any mood/style guidance (max 2000 chars).
            width: Canvas width in pixels (default: 1080).
            height: Canvas height in pixels (default: 1080).
            duration_seconds: Video length in seconds, 1-60 (default: 8).
            brand_color: Optional brand color (hex) to build the palette around.
            timeout: Per-call timeout in seconds (default: 180).

        Returns:
            GenerateVideoTemplateResult with ``template`` and ``preview_url``.
        """
        data = self._request(
            "POST",
            "/video/templates/generate",
            json={
                "prompt": prompt,
                "width": width,
                "height": height,
                "durationSeconds": duration_seconds,
                "brandColor": brand_color,
            },
            timeout=timeout if timeout is not None else self.VIDEO_TEMPLATE_TIMEOUT,
        )
        return GenerateVideoTemplateResult.model_validate(data)

    def create_video_template(
        self,
        name: str,
        tsx: str,
        *,
        width: int = 1080,
        height: int = 1080,
        fps: int = 30,
        duration_seconds: float = 8,
        timeout: Optional[float] = None,
    ) -> VideoTemplate:
        """Upload a Remotion scene you wrote as a new video template.

        ``POST /video/templates`` — unwraps the ``{template}`` envelope. Sends
        ``kind="tsx"``, ``status="draft"``, and ``durationInFrames`` computed as
        ``round(duration_seconds * fps)``.

        The source passes a compile gate BEFORE anything is saved: invalid tsx
        rejects with a 422 carrying the compiler errors (``error.errors``) and
        creates NOTHING, so retrying cannot litter the account with broken
        templates.

        Args:
            name: Template name shown in the dashboard.
            tsx: The complete single-file Remotion scene source. Must export a
                zod ``schema`` (flat fields with defaults — they become the
                template's variables) and a default React component; imports
                limited to ``remotion``, ``react`` and ``zod``.
            width: Canvas width in pixels (default: 1080).
            height: Canvas height in pixels (default: 1080).
            fps: Frames per second (default: 30).
            duration_seconds: Video length in seconds (default: 8).
            timeout: Per-call timeout in seconds (default: 180 — the compile
                gate bundles the scene).

        Returns:
            The created VideoTemplate.
        """
        data = self._request(
            "POST",
            "/video/templates",
            json={
                "name": name,
                "kind": "tsx",
                "tsx": tsx,
                "width": width,
                "height": height,
                "fps": fps,
                "durationInFrames": round(duration_seconds * fps),
                "status": "draft",
            },
            timeout=timeout if timeout is not None else self.VIDEO_TEMPLATE_TIMEOUT,
        )
        return VideoTemplate.model_validate((data or {}).get("template", data))
