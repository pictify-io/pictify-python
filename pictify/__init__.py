"""Pictify Python SDK.

Official SDK for generating images, PDFs, and GIFs from raw HTML, live URLs,
and reusable templates via the Pictify API.

Example:
    >>> from pictify import Pictify
    >>> client = Pictify(api_key="your-api-key")
    >>> image = client.render_html(html="<div>Hello World</div>")
    >>> print(image.url)
"""

from pictify.async_client import AsyncPictify
from pictify.client import Pictify
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
from pictify.types import (
    BatchItemStatus,
    BatchRenderResult,
    BatchResults,
    GenerateVideoTemplateResult,
    GifQuality,
    GifRenderResult,
    ImageFormat,
    ImageResult,
    ListTemplatesResult,
    Pagination,
    RenderErrorEntry,
    RenderResult,
    RenderResultItem,
    RenderVideoResult,
    Template,
    TemplateVariableDefinition,
    VideoFormat,
    VideoTemplate,
    VideoTemplateVariables,
)

__version__ = "1.0.0"
__all__ = [
    # Clients
    "Pictify",
    "AsyncPictify",
    # Types
    "ImageFormat",
    "GifQuality",
    "ImageResult",
    "RenderResult",
    "RenderResultItem",
    "RenderErrorEntry",
    "GifRenderResult",
    "BatchRenderResult",
    "BatchResults",
    "BatchItemStatus",
    "Template",
    "TemplateVariableDefinition",
    "Pagination",
    "ListTemplatesResult",
    "VideoFormat",
    "VideoTemplate",
    "VideoTemplateVariables",
    "RenderVideoResult",
    "GenerateVideoTemplateResult",
    # Errors
    "PictifyError",
    "AuthenticationError",
    "TemplateNotFoundError",
    "RateLimitError",
    "QuotaExceededError",
    "RenderError",
    "ServerError",
    "NetworkError",
    "TimeoutError",
]
