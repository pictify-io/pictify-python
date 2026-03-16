"""Type definitions for the Pictify SDK."""

from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field
from datetime import datetime

# Image format type
ImageFormat = Literal["png", "jpg", "jpeg", "webp", "gif", "pdf"]


class RenderOptions(BaseModel):
    """Options for rendering an image."""

    template_id: str = Field(..., description="The ID of the template to use")
    variables: Dict[str, Any] = Field(
        default_factory=dict, description="Variables to inject into the template"
    )
    format: ImageFormat = Field(default="png", description="Output format")
    width: Optional[int] = Field(default=None, description="Output width in pixels")
    height: Optional[int] = Field(default=None, description="Output height in pixels")
    download: bool = Field(
        default=False, description="Whether to return the image as bytes instead of a URL"
    )
    device_scale_factor: float = Field(
        default=1.0, description="Device scale factor for retina images"
    )
    transparent: bool = Field(default=False, description="Transparent background (PNG only)")
    quality: int = Field(default=90, ge=1, le=100, description="Quality for JPEG/WebP")
    layout: Optional[str] = Field(
        default=None, description="Single layout variant to render"
    )
    layouts: Optional[List[str]] = Field(
        default=None, description="Multiple layout variants to render"
    )


class BatchItem(BaseModel):
    """Individual item in a batch render request."""

    variables: Dict[str, Any] = Field(..., description="Variables for this specific render")
    filename: Optional[str] = Field(default=None, description="Optional filename for this render")


class BatchRenderOptions(BaseModel):
    """Options for batch rendering."""

    template_id: str = Field(..., description="The ID of the template to use")
    items: List[BatchItem] = Field(..., description="Array of items to render")
    format: ImageFormat = Field(default="png", description="Output format for all items")
    width: Optional[int] = Field(default=None, description="Output width for all items")
    height: Optional[int] = Field(default=None, description="Output height for all items")
    layout: Optional[str] = Field(
        default=None, description="Layout variant to use for all batch items"
    )
    layouts: Optional[List[str]] = Field(
        default=None, description="Array of layout variant names to render for all batch items"
    )


class RenderResultItem(BaseModel):
    """Individual result item when rendering with layout variants."""

    layout: Optional[str] = Field(default=None, description="Layout variant name")
    name: Optional[str] = Field(default=None, description="Display name for this variant")
    url: Optional[str] = Field(default=None, description="URL of the rendered image")
    width: Optional[int] = Field(default=None, description="Width of the rendered image")
    height: Optional[int] = Field(default=None, description="Height of the rendered image")
    format: Optional[ImageFormat] = Field(default=None, description="Format of the rendered image")
    id: Optional[str] = Field(default=None, description="Unique ID for this render")


class RenderResult(BaseModel):
    """Result of a render operation.

    For single renders (no layouts), use `image_url` for backward compatibility.
    For layout renders, iterate over `results` or use the `url` property for the first result.
    """

    # Legacy single-render fields
    image_url: Optional[str] = Field(
        default=None, description="URL of the generated image (if download was False)"
    )
    render_id: Optional[str] = Field(default=None, description="Unique render ID")
    width: Optional[int] = Field(default=None, description="Width of the generated image")
    height: Optional[int] = Field(default=None, description="Height of the generated image")
    size: Optional[int] = Field(default=None, description="File size in bytes")
    format: Optional[ImageFormat] = Field(default=None, description="Format of the generated image")
    render_time: Optional[int] = Field(
        default=None, description="Time taken to render in milliseconds"
    )

    # Layout render fields
    results: List[RenderResultItem] = Field(
        default_factory=list, description="Array of rendered layout results"
    )
    errors: List[Dict[str, Any]] = Field(
        default_factory=list, description="Array of errors from layout rendering"
    )
    total_layouts: Optional[int] = Field(
        default=None, description="Total number of layout variants requested"
    )
    total_rendered: Optional[int] = Field(
        default=None, description="Total number of successfully rendered layouts"
    )
    total_errors: Optional[int] = Field(
        default=None, description="Total number of layout rendering errors"
    )
    template_uid: Optional[str] = Field(
        default=None, description="Template UID used for the render"
    )

    @property
    def url(self) -> Optional[str]:
        """Return the URL of the first result for backward compatibility.

        Falls back to image_url for non-layout renders.
        """
        if self.results:
            return self.results[0].url
        return self.image_url


class BatchItemError(BaseModel):
    """Error for a specific layout within a batch item."""

    layout: Optional[str] = Field(default=None, description="Layout variant name that failed")
    error: Optional[str] = Field(default=None, description="Error message")


class BatchItemResult(BaseModel):
    """Individual batch item result containing per-layout renders."""

    index: int = Field(..., description="Zero-based index of this item in the batch")
    success: bool = Field(..., description="Whether this batch item rendered successfully")
    variables: List[str] = Field(
        default_factory=list, description="Variable names used for this item"
    )
    results: List[RenderResultItem] = Field(
        default_factory=list, description="Rendered images, one per requested layout"
    )
    errors: List[BatchItemError] = Field(
        default_factory=list, description="Errors for layouts that failed to render for this item"
    )


class BatchRenderResult(BaseModel):
    """Result of a batch render operation."""

    results: List[BatchItemResult] = Field(..., description="Array of individual batch item results")
    total_time: int = Field(..., description="Total time taken for the batch")
    success_count: int = Field(..., description="Number of successful renders")
    failed_count: int = Field(..., description="Number of failed renders")


class TemplateVariable(BaseModel):
    """Template variable definition."""

    name: str = Field(..., description="Variable name")
    type: Literal["string", "number", "boolean", "image", "color"] = Field(
        ..., description="Variable type"
    )
    default_value: Optional[Any] = Field(default=None, description="Default value")
    required: bool = Field(..., description="Whether the variable is required")
    description: Optional[str] = Field(default=None, description="Description of the variable")


class Template(BaseModel):
    """Template information."""

    id: str = Field(..., description="Unique template ID")
    name: str = Field(..., description="Template name")
    description: Optional[str] = Field(default=None, description="Template description")
    width: int = Field(..., description="Default width")
    height: int = Field(..., description="Default height")
    variables: List[TemplateVariable] = Field(
        default_factory=list, description="Variables defined in the template"
    )
    preview_url: Optional[str] = Field(default=None, description="Preview URL")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class HTMLRenderOptions(BaseModel):
    """Options for rendering HTML directly (without a template)."""

    html: str = Field(..., description="Raw HTML content to render")
    css: Optional[str] = Field(default=None, description="Optional CSS to apply")
    format: ImageFormat = Field(default="png", description="Output format")
    width: int = Field(default=1200, description="Output width in pixels")
    height: int = Field(default=630, description="Output height in pixels")
    device_scale_factor: float = Field(
        default=1.0, description="Device scale factor for retina images"
    )
    transparent: bool = Field(default=False, description="Transparent background (PNG only)")
    quality: int = Field(default=90, ge=1, le=100, description="Quality for JPEG/WebP")
    download: bool = Field(
        default=False, description="Whether to return the image as bytes instead of a URL"
    )


class GIFFrame(BaseModel):
    """Individual frame in a GIF animation."""

    variables: Optional[Dict[str, Any]] = Field(
        default=None, description="Variables for this frame (when using template)"
    )
    html: Optional[str] = Field(
        default=None, description="HTML content for this frame (when using raw HTML)"
    )
    delay: Optional[int] = Field(
        default=None, description="Delay for this specific frame in ms (overrides global delay)"
    )


class GIFRenderOptions(BaseModel):
    """Options for rendering a GIF animation."""

    template_id: Optional[str] = Field(
        default=None, description="The ID of the template to use (if using template)"
    )
    html: Optional[str] = Field(
        default=None, description="Raw HTML content to render (if not using template)"
    )
    css: Optional[str] = Field(default=None, description="Optional CSS to apply (when using html)")
    frames: List[GIFFrame] = Field(..., description="Array of frame configurations")
    width: Optional[int] = Field(default=None, description="Output width in pixels")
    height: Optional[int] = Field(default=None, description="Output height in pixels")
    delay: int = Field(default=100, description="Delay between frames in milliseconds")
    loop: int = Field(default=0, description="Number of times to loop (0 = infinite)")
    quality: int = Field(default=80, ge=1, le=100, description="Quality (1-100)")


class GIFRenderResult(BaseModel):
    """Result of a GIF render operation."""

    gif_url: Optional[str] = Field(default=None, description="URL of the generated GIF")
    render_id: str = Field(..., description="Unique render ID")
    width: int = Field(..., description="Width of the generated GIF")
    height: int = Field(..., description="Height of the generated GIF")
    size: int = Field(..., description="File size in bytes")
    frame_count: int = Field(..., description="Number of frames")
    duration: int = Field(..., description="Total duration in milliseconds")
    render_time: int = Field(..., description="Time taken to render in milliseconds")
