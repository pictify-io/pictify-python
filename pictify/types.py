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


class RenderResult(BaseModel):
    """Result of a render operation."""

    image_url: Optional[str] = Field(
        default=None, description="URL of the generated image (if download was False)"
    )
    render_id: str = Field(..., description="Unique render ID")
    width: int = Field(..., description="Width of the generated image")
    height: int = Field(..., description="Height of the generated image")
    size: int = Field(..., description="File size in bytes")
    format: ImageFormat = Field(..., description="Format of the generated image")
    render_time: int = Field(..., description="Time taken to render in milliseconds")


class BatchRenderResult(BaseModel):
    """Result of a batch render operation."""

    results: List[RenderResult] = Field(..., description="Array of individual render results")
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
