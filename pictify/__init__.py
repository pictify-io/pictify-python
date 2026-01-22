"""
Pictify Python SDK

Official SDK for generating images from HTML templates using the Pictify API.

Example:
    >>> from pictify import Pictify
    >>> client = Pictify(api_key="your-api-key")
    >>> result = client.render(
    ...     template_id="your-template-id",
    ...     variables={"title": "Hello World"}
    ... )
    >>> print(result.image_url)
"""

from pictify.client import Pictify
from pictify.async_client import AsyncPictify
from pictify.types import (
    RenderOptions,
    RenderResult,
    BatchRenderOptions,
    BatchRenderResult,
    BatchItem,
    Template,
    TemplateVariable,
    ImageFormat,
)
from pictify.errors import (
    PictifyError,
    AuthenticationError,
    TemplateNotFoundError,
    RateLimitError,
    QuotaExceededError,
    RenderError,
    NetworkError,
    TimeoutError,
)

__version__ = "1.0.0"
__all__ = [
    # Clients
    "Pictify",
    "AsyncPictify",
    # Types
    "RenderOptions",
    "RenderResult",
    "BatchRenderOptions",
    "BatchRenderResult",
    "BatchItem",
    "Template",
    "TemplateVariable",
    "ImageFormat",
    # Errors
    "PictifyError",
    "AuthenticationError",
    "TemplateNotFoundError",
    "RateLimitError",
    "QuotaExceededError",
    "RenderError",
    "NetworkError",
    "TimeoutError",
]
