"""Type definitions for the Pictify SDK.

Result models are Pydantic models that map the API's camelCase JSON onto
snake_case attributes via field aliases (``populate_by_name=True``), so callers
get idiomatic Python attributes while still validating the real wire format.
"""

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

# Formats the `/image` endpoint accepts (mapped to `fileExtension`).
# NOT `pdf`: the backend silently normalises unknown values to png, so a caller
# asking /image for a pdf would get a PNG with no error. PDF output exists only
# on template renders (`TemplateRenderFormat`).
ImageFormat = Literal["png", "jpg", "jpeg", "webp"]

# Formats template render accepts — images plus `pdf`.
TemplateRenderFormat = Literal["png", "jpg", "jpeg", "webp", "pdf"]

# Formats batch render accepts (the backend's actual enum: no `jpg` alias, no `pdf`).
BatchRenderFormat = Literal["png", "jpeg", "webp", "gif"]

# GIF quality presets accepted by the `/gif` endpoint.
GifQuality = Literal["low", "medium", "high"]

# Video output formats supported by video template renders.
# `gif` is a palette-optimised animated GIF capped at 15fps / 720px wide.
VideoFormat = Literal["mp4", "gif"]


class ImageResult(BaseModel):
    """Result of an ``/image`` render (``render_html`` / ``render_url``).

    Maps the API response ``{url, id, createdAt}``.
    """

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    url: str = Field(..., description="CDN URL of the rendered image")
    id: Optional[str] = Field(default=None, description="Unique image ID")
    created_at: Optional[str] = Field(
        default=None, alias="createdAt", description="When the image was created"
    )


class RenderResultItem(BaseModel):
    """A single rendered item in a template render response."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    layout: Optional[str] = Field(default=None, description="Layout variant name")
    url: Optional[str] = Field(default=None, description="CDN URL of the rendered image")
    width: Optional[int] = Field(default=None, description="Width of the rendered image")
    height: Optional[int] = Field(default=None, description="Height of the rendered image")
    format: Optional[str] = Field(default=None, description="Output format")
    name: Optional[str] = Field(default=None, description="Human-readable variant name")
    id: Optional[str] = Field(default=None, description="Unique render ID for this item")
    created_at: Optional[str] = Field(
        default=None, alias="createdAt", description="When this item was created"
    )


class RenderErrorEntry(BaseModel):
    """Error entry returned when a specific layout fails to render."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    layout: Optional[str] = Field(default=None, description="Layout variant that failed")
    error: Optional[str] = Field(default=None, description="Error message")


class RenderResult(BaseModel):
    """Result of a template render (``render`` / ``render_layouts``).

    The API returns a ``results[]`` envelope. The convenience property
    :pyattr:`url` returns the URL of the first result.
    """

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    results: List[RenderResultItem] = Field(
        default_factory=list, description="Successfully rendered items"
    )
    errors: List[RenderErrorEntry] = Field(
        default_factory=list, description="Errors for layouts that failed"
    )
    total_layouts: Optional[int] = Field(
        default=None, alias="totalLayouts", description="Total layouts requested"
    )
    total_rendered: Optional[int] = Field(
        default=None, alias="totalRendered", description="Total successfully rendered"
    )
    total_errors: Optional[int] = Field(
        default=None, alias="totalErrors", description="Total layout render errors"
    )
    template_uid: Optional[str] = Field(
        default=None, alias="templateUid", description="Template UID used"
    )

    @property
    def url(self) -> Optional[str]:
        """Convenience accessor — URL of the first rendered item (``results[0].url``)."""
        if self.results:
            return self.results[0].url
        return None


class GifRenderResult(BaseModel):
    """Result of a GIF render (``render_gif``).

    Flattened from the API's ``{gif: {...}}`` envelope.
    """

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    url: str = Field(..., description="CDN URL of the rendered GIF")
    uid: Optional[str] = Field(default=None, description="Unique GIF ID")
    width: Optional[int] = Field(default=None, description="Width of the rendered GIF")
    height: Optional[int] = Field(default=None, description="Height of the rendered GIF")
    animation_length: Optional[float] = Field(
        default=None, alias="animationLength", description="Animation length in ms"
    )


class BatchRenderResult(BaseModel):
    """Result of submitting a batch render (``render_batch``).

    The job runs asynchronously (HTTP 202) — poll ``get_batch_results`` with the
    returned :pyattr:`batch_id` to track progress.
    """

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    batch_id: str = Field(..., alias="batchId", description="Unique batch job ID")
    status: Optional[str] = Field(default=None, description="Initial job status")
    total_items: Optional[int] = Field(
        default=None, alias="totalItems", description="Total number of items queued"
    )
    message: Optional[str] = Field(default=None, description="Human-readable status message")


class BatchItemStatus(BaseModel):
    """Status of a single item within a batch job.

    NOTE: batch results do NOT include rendered URLs — those are delivered via
    the ``render.completed`` webhook. Each item reports only its index, success,
    and the variable names it used (plus an ``error`` message on failure).
    """

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    index: Optional[int] = Field(default=None, description="Zero-based index in the batch")
    success: Optional[bool] = Field(default=None, description="Whether this item rendered")
    variables: Optional[List[str]] = Field(
        default=None, description="Variable names used for this item"
    )
    error: Optional[str] = Field(default=None, description="Error message (failed items)")


class BatchResults(BaseModel):
    """Full status + progress of a batch job (``get_batch_results``).

    ``GET /templates/batch/:batchId/results``.
    """

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    batch_id: str = Field(..., alias="batchId", description="Unique batch job ID")
    status: Optional[str] = Field(default=None, description="Current job status")
    progress: Optional[float] = Field(default=None, description="Completion percentage (0-100)")
    total_items: Optional[int] = Field(
        default=None, alias="totalItems", description="Total number of items"
    )
    completed_items: Optional[int] = Field(
        default=None, alias="completedItems", description="Number of items completed"
    )
    failed_items: Optional[int] = Field(
        default=None, alias="failedItems", description="Number of items that failed"
    )
    results: List[BatchItemStatus] = Field(
        default_factory=list, description="Per-item success records (no URLs)"
    )
    errors: List[BatchItemStatus] = Field(
        default_factory=list, description="Per-item failure records"
    )
    created_at: Optional[str] = Field(
        default=None, alias="createdAt", description="When the batch was created"
    )
    started_at: Optional[str] = Field(
        default=None, alias="startedAt", description="When processing started"
    )
    completed_at: Optional[str] = Field(
        default=None, alias="completedAt", description="When the batch completed"
    )


class TemplateVariableDefinition(BaseModel):
    """A variable definition declared on a template.

    Engine-specific fields are passed through.
    """

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    name: str = Field(..., description="Variable name (referenced as {{name}})")
    type: Optional[str] = Field(default=None, description="Variable type")
    default_value: Optional[Any] = Field(
        default=None, alias="defaultValue", description="Default value"
    )
    description: Optional[str] = Field(default=None, description="Human-readable description")
    validation: Optional[Dict[str, Any]] = Field(default=None, description="Validation rules")


class Template(BaseModel):
    """Template information returned by ``get_template`` / ``create_template`` / ``list_templates``.

    The API keys templates by ``uid`` (not ``id``) and declares variables in
    ``variable_definitions``. Additional engine fields are passed through.
    """

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    uid: str = Field(..., description="Unique template ID")
    name: Optional[str] = Field(default=None, description="Template name")
    html: Optional[str] = Field(default=None, description="Raw HTML body (html-engine)")
    width: Optional[int] = Field(default=None, description="Default width in pixels")
    height: Optional[int] = Field(default=None, description="Default height in pixels")
    engine: Optional[str] = Field(default=None, description="Rendering engine")
    output_format: Optional[str] = Field(
        default=None, alias="outputFormat", description="Output format (image | pdf)"
    )
    variables: Optional[List[str]] = Field(
        default=None, description="Legacy flat list of variable names"
    )
    variable_definitions: Optional[List[TemplateVariableDefinition]] = Field(
        default=None, alias="variableDefinitions", description="Structured variable definitions"
    )
    thumbnail: Optional[str] = Field(default=None, description="Thumbnail URL")
    created_at: Optional[str] = Field(
        default=None, alias="createdAt", description="Creation timestamp"
    )
    updated_at: Optional[str] = Field(
        default=None, alias="updatedAt", description="Last update timestamp"
    )


class VideoTemplate(BaseModel):
    """A video template returned by the video template endpoints.

    ``kind`` is ``timeline`` (built in the visual studio) or ``tsx`` (a
    single-file Remotion scene). Both render identically. Kept permissive:
    unknown engine fields pass through.
    """

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    uid: str = Field(..., description="Unique video template ID")
    name: Optional[str] = Field(default=None, description="Template name")
    kind: Optional[str] = Field(default=None, description="Template kind (timeline | tsx)")
    width: Optional[int] = Field(default=None, description="Canvas width in pixels")
    height: Optional[int] = Field(default=None, description="Canvas height in pixels")
    fps: Optional[int] = Field(default=None, description="Frames per second")
    duration_in_frames: Optional[int] = Field(
        default=None, alias="durationInFrames", description="Video length in frames"
    )
    poster_url: Optional[str] = Field(
        default=None, alias="posterUrl", description="Poster frame URL"
    )
    status: Optional[str] = Field(default=None, description="Template status (e.g. draft)")
    variable_definitions: Optional[List[TemplateVariableDefinition]] = Field(
        default=None, alias="variableDefinitions", description="Structured variable definitions"
    )
    created_at: Optional[str] = Field(
        default=None, alias="createdAt", description="Creation timestamp"
    )
    updated_at: Optional[str] = Field(
        default=None, alias="updatedAt", description="Last update timestamp"
    )


class VideoTemplateVariables(BaseModel):
    """Variable definitions of a video template (``get_video_template_variables``).

    ``GET /video/templates/:uid/variables``.
    """

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    template_uid: Optional[str] = Field(
        default=None, alias="templateUid", description="Video template UID"
    )
    template_name: Optional[str] = Field(
        default=None, alias="templateName", description="Video template name"
    )
    kind: Optional[str] = Field(default=None, description="Template kind (timeline | tsx)")
    variables: List[TemplateVariableDefinition] = Field(
        default_factory=list, description="Variable definitions you can set when rendering"
    )
    referenced: List[str] = Field(
        default_factory=list,
        description="Every variable name the document actually references",
    )


class RenderVideoResult(BaseModel):
    """Result of a video template render (``render_video``)."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    url: str = Field(..., description="Hosted URL of the finished file")
    duration_in_frames: Optional[int] = Field(
        default=None, alias="durationInFrames", description="Video length in frames"
    )
    format: Optional[str] = Field(
        default=None, description='What was actually produced: "mp4" or "gif"'
    )


class GenerateVideoTemplateResult(BaseModel):
    """Result of AI video template generation (``generate_video_template``)."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    template: VideoTemplate = Field(..., description="The generated draft template")
    preview_url: Optional[str] = Field(
        default=None, alias="previewUrl", description="A rendered preview frame of the scene"
    )


class Pagination(BaseModel):
    """Pagination metadata returned by ``list_templates``."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    page: Optional[int] = Field(default=None, description="Current page (1-based)")
    limit: Optional[int] = Field(default=None, description="Items per page")
    total: Optional[int] = Field(default=None, description="Total number of templates")
    total_pages: Optional[int] = Field(
        default=None, alias="totalPages", description="Total number of pages"
    )
    has_next: Optional[bool] = Field(
        default=None, alias="hasNext", description="Whether a next page exists"
    )
    has_prev: Optional[bool] = Field(
        default=None, alias="hasPrev", description="Whether a previous page exists"
    )


class ListTemplatesResult(BaseModel):
    """Result of listing templates (``list_templates``)."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    templates: List[Template] = Field(default_factory=list, description="Templates on this page")
    pagination: Optional[Pagination] = Field(default=None, description="Pagination metadata")
