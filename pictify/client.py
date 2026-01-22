"""Synchronous Pictify client."""

import time
from typing import Any, Dict, Iterator, List, Optional

import httpx

from pictify.errors import (
    NetworkError,
    TimeoutError,
    create_error_from_response,
)
from pictify.types import (
    BatchItem,
    BatchRenderResult,
    ImageFormat,
    RenderResult,
    Template,
)


class Pictify:
    """Synchronous client for the Pictify API.

    Example:
        >>> client = Pictify(api_key="your-api-key")
        >>> result = client.render(
        ...     template_id="your-template-id",
        ...     variables={"title": "Hello World"}
        ... )
        >>> print(result.image_url)
    """

    DEFAULT_BASE_URL = "https://api.pictify.io/v1"
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
        """Initialize the Pictify client.

        Args:
            api_key: Your Pictify API key.
            base_url: Custom API base URL (optional).
            timeout: Request timeout in seconds (default: 30).
            max_retries: Maximum number of retries for failed requests (default: 3).
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
                "User-Agent": "pictify-python/1.0.0",
            },
            timeout=self.timeout,
        )

    def __enter__(self) -> "Pictify":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: Optional[Dict[str, Any]] = None,
        stream: bool = False,
    ) -> httpx.Response:
        """Make an HTTP request with retry logic."""
        last_error: Optional[Exception] = None

        for attempt in range(self.max_retries + 1):
            try:
                response = self._client.request(
                    method,
                    path,
                    json=json,
                )

                if response.status_code >= 400:
                    try:
                        body = response.json()
                    except Exception:
                        body = {"message": response.text}

                    # Retry on 5xx errors or rate limits
                    if response.status_code >= 500 or response.status_code == 429:
                        if attempt < self.max_retries:
                            retry_after = body.get("retry_after", self.RETRY_DELAY * (2**attempt))
                            time.sleep(retry_after)
                            continue

                    raise create_error_from_response(response.status_code, body)

                return response

            except httpx.TimeoutException as e:
                last_error = TimeoutError(f"Request timed out after {self.timeout}s", self.timeout)
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

        raise last_error or NetworkError("Request failed after all retries")

    def render(
        self,
        template_id: str,
        variables: Optional[Dict[str, Any]] = None,
        *,
        format: ImageFormat = "png",
        width: Optional[int] = None,
        height: Optional[int] = None,
        download: bool = False,
        device_scale_factor: float = 1.0,
        transparent: bool = False,
        quality: int = 90,
    ) -> RenderResult:
        """Render an image from a template.

        Args:
            template_id: The ID of the template to render.
            variables: Variables to inject into the template.
            format: Output format (png, jpg, jpeg, webp, gif, pdf).
            width: Output width in pixels.
            height: Output height in pixels.
            download: Whether to return image bytes instead of URL.
            device_scale_factor: Scale factor for retina images.
            transparent: Enable transparent background (PNG only).
            quality: Quality for JPEG/WebP (1-100).

        Returns:
            RenderResult with image URL and metadata.
        """
        payload: Dict[str, Any] = {
            "template_id": template_id,
            "variables": variables or {},
            "format": format,
            "download": download,
            "device_scale_factor": device_scale_factor,
            "transparent": transparent,
            "quality": quality,
        }

        if width is not None:
            payload["width"] = width
        if height is not None:
            payload["height"] = height

        response = self._request("POST", "/render", json=payload)
        return RenderResult.model_validate(response.json())

    def render_stream(
        self,
        template_id: str,
        variables: Optional[Dict[str, Any]] = None,
        *,
        format: ImageFormat = "png",
        width: Optional[int] = None,
        height: Optional[int] = None,
        device_scale_factor: float = 1.0,
        transparent: bool = False,
        quality: int = 90,
    ) -> Iterator[bytes]:
        """Render and stream image bytes.

        Args:
            template_id: The ID of the template to render.
            variables: Variables to inject into the template.
            format: Output format (png, jpg, jpeg, webp, gif, pdf).
            width: Output width in pixels.
            height: Output height in pixels.
            device_scale_factor: Scale factor for retina images.
            transparent: Enable transparent background (PNG only).
            quality: Quality for JPEG/WebP (1-100).

        Yields:
            Chunks of image bytes.
        """
        payload: Dict[str, Any] = {
            "template_id": template_id,
            "variables": variables or {},
            "format": format,
            "stream": True,
            "device_scale_factor": device_scale_factor,
            "transparent": transparent,
            "quality": quality,
        }

        if width is not None:
            payload["width"] = width
        if height is not None:
            payload["height"] = height

        with self._client.stream("POST", "/render/stream", json=payload) as response:
            if response.status_code >= 400:
                response.read()
                try:
                    body = response.json()
                except Exception:
                    body = {"message": response.text}
                raise create_error_from_response(response.status_code, body)

            for chunk in response.iter_bytes():
                yield chunk

    def render_batch(
        self,
        template_id: str,
        items: List[Dict[str, Any]],
        *,
        format: ImageFormat = "png",
        width: Optional[int] = None,
        height: Optional[int] = None,
    ) -> BatchRenderResult:
        """Render multiple images in a batch.

        Args:
            template_id: The ID of the template to use for all items.
            items: List of items, each with 'variables' and optional 'filename'.
            format: Output format for all items.
            width: Output width for all items.
            height: Output height for all items.

        Returns:
            BatchRenderResult with individual results and summary.
        """
        batch_items = [
            BatchItem(
                variables=item.get("variables", {}),
                filename=item.get("filename"),
            )
            for item in items
        ]

        payload: Dict[str, Any] = {
            "template_id": template_id,
            "items": [item.model_dump() for item in batch_items],
            "format": format,
        }

        if width is not None:
            payload["width"] = width
        if height is not None:
            payload["height"] = height

        response = self._request("POST", "/render/batch", json=payload)
        return BatchRenderResult.model_validate(response.json())

    def get_template(self, template_id: str) -> Template:
        """Get template information.

        Args:
            template_id: The ID of the template to retrieve.

        Returns:
            Template with metadata and variable definitions.
        """
        response = self._request("GET", f"/templates/{template_id}")
        return Template.model_validate(response.json())

    def list_templates(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Template]:
        """List all templates.

        Args:
            limit: Maximum number of templates to return.
            offset: Number of templates to skip.

        Returns:
            List of templates.
        """
        response = self._request(
            "GET",
            f"/templates?limit={limit}&offset={offset}",
        )
        data = response.json()
        return [Template.model_validate(t) for t in data.get("templates", [])]
