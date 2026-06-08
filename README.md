# Pictify Python SDK

Official Python SDK for [Pictify](https://pictify.io) — generate images, PDFs, and GIFs from raw HTML, live URLs, and reusable templates.

## Installation

```bash
pip install pictify
```

## Quick Start

```python
from pictify import Pictify

client = Pictify(api_key="your-api-key")

# Render raw HTML to a PNG
image = client.render_html(html="<div style='font-size:48px;padding:40px'>Hello World</div>")
print(image.url)

# Render a reusable template
result = client.render("your-template-uid", variables={"name": "Ada", "company": "Pictify"})
print(result.url)  # results[0].url
```

## Async Usage

```python
import asyncio
from pictify import AsyncPictify

async def main():
    async with AsyncPictify(api_key="your-api-key") as client:
        image = await client.render_html(html="<div>Hello World</div>")
        print(image.url)

asyncio.run(main())
```

## Features

- **Sync + async clients** — `Pictify` and `AsyncPictify`, identical surface
- **Full type hints** — Pydantic result models with snake_case attributes
- **Automatic retries** — exponential backoff on 5xx and network errors
- **Typed errors** — `AuthenticationError`, `RateLimitError`, `QuotaExceededError`, and more
- **Templates, HTML, URLs & GIFs** — one client for every render type
- **Async batch rendering** — submit large jobs and poll for progress

## Configuration

```python
client = Pictify(
    api_key="your-api-key",
    base_url="https://api.pictify.io",  # optional: API base URL
    timeout=30.0,                       # optional: request timeout in seconds (default: 30)
    max_retries=3,                      # optional: retries on 5xx/network errors (default: 3)
)
```

Both clients are context managers and expose `close()`:

```python
with Pictify(api_key="your-api-key") as client:
    ...

async with AsyncPictify(api_key="your-api-key") as client:
    ...
```

## API Reference

### `render_html(html, *, css=None, width=None, height=None, selector=None, format=None)`

Render an image (or PDF) directly from HTML. `POST /image`.

```python
image = client.render_html(
    html="<div style='padding:40px'>Hello</div>",
    css="div { color: blue; }",   # optional — inlined into a <style> tag
    width=1200,                    # optional (default: 1280)
    height=630,                    # optional (default: 720)
    selector="#card",             # optional — crop to a specific element
    format="png",                 # optional: 'png' | 'jpg' | 'jpeg' | 'webp' | 'pdf' (default: png)
)
print(image.url, image.id, image.created_at)
```

### `render_url(url, *, width=None, height=None, selector=None, format=None)`

Screenshot a live URL. `POST /image` with `url`.

```python
image = client.render_url(url="https://example.com", width=1280, height=720)
print(image.url)
```

### `render(template_id, *, variables=None, format=None, quality=None, width=None, height=None, layout=None, layouts=None)`

Render a single image (or PDF) from a template. `POST /templates/:uid/render`.

The response is a `results` envelope; `result.url` is a convenience accessor for `results[0].url`.

```python
result = client.render(
    "template-uid",
    variables={"title": "My Post", "author": "Ada"},
    format="png",   # optional: 'png' | 'jpg' | 'jpeg' | 'webp' | 'pdf' (default: png)
    quality=0.9,    # optional render quality, 0.1-1.0 (default: 0.9)
    width=1200,     # optional
    height=630,     # optional
)
print(result.url)
print(result.results[0])  # RenderResultItem: layout, url, width, height, format, name, id, created_at
```

### `render_layouts(template_id, layouts, *, variables=None, format=None, quality=None, width=None, height=None)`

Render multiple layout variants of a template in one call (max 20). `POST /templates/:uid/render` with `layouts`.

Each successful layout appears in `results`; missing/invalid layouts appear in `errors`.

```python
result = client.render_layouts(
    "template-uid",
    layouts=["default", "square", "story"],
    variables={"title": "Hello"},
)
for item in result.results:
    print(item.layout, item.url, f"{item.width}x{item.height}")
for err in result.errors:
    print("failed:", err.layout, err.error)
```

### `render_gif(*, html=None, url=None, template_id=None, variables=None, width=None, height=None, quality=None)`

Render an animated GIF from raw HTML, a live URL, or a template. `POST /gif`.

Provide exactly one source: `html`, `url`, or `template_id`. The `{gif: {...}}` envelope is flattened.

```python
gif = client.render_gif(
    html="<style>@keyframes p{...}</style><div class='anim'>Hi</div>",
    width=400,     # optional (default: 800)
    height=200,    # optional (default: 600)
    quality="medium",  # optional: 'low' | 'medium' | 'high' (default: medium)
)
print(gif.url, gif.uid, gif.animation_length)
```

### `render_batch(template_id, variable_sets, *, format=None, quality=None, concurrency=None, layout=None, layouts=None)`

Submit an **async** batch render of a template across many variable sets (max 100). `POST /templates/:uid/batch-render`.

Returns immediately (HTTP 202) with a `batch_id`. Poll `get_batch_results` for progress. Rendered URLs are delivered via the `render.completed` webhook — they are **not** returned by the poll endpoint.

```python
job = client.render_batch(
    "template-uid",
    variable_sets=[{"name": p["name"], "price": p["price"]} for p in products],
)
print(job.batch_id, job.status, job.total_items)
```

### `get_batch_results(batch_id)`

Get the status, progress, and per-item results of a batch job. `GET /templates/batch/:batchId/results`.

```python
status = client.get_batch_results(job.batch_id)
print(status.status, status.completed_items, "/", status.total_items)
for item in status.results:
    print(item.index, item.success, item.variables)  # no URLs (see webhook)
```

### `get_template(template_id)`

Get a single template by its UID. `GET /templates/:uid`.

```python
template = client.get_template("template-uid")
print(template.uid, template.name)
print([v.name for v in (template.variable_definitions or [])])
```

### `list_templates(*, page=None, limit=None, sort=None)`

List templates in your account. `GET /templates`.

```python
result = client.list_templates(page=1, limit=20, sort="newest")
for t in result.templates:
    print(t.uid, t.name)
print(result.pagination.total, result.pagination.has_next)
```

### `create_template(html, *, name=None, width=None, height=None, variable_definitions=None, output_format=None)`

Create a template from HTML. Variables are auto-discovered from `{{variableName}}` tokens. `POST /templates`.

```python
template = client.create_template(
    html="<div>Hi {{first_name}}</div>",
    name="Welcome Card",
    width=600,
    height=200,
)
print(template.uid)
```

## Error Handling

```python
from pictify import (
    Pictify,
    PictifyError,
    AuthenticationError,
    TemplateNotFoundError,
    RateLimitError,
    QuotaExceededError,
    RenderError,
    ServerError,
)

client = Pictify(api_key="your-api-key")

try:
    result = client.render("template-uid", variables={"title": "Hello World"})
except AuthenticationError:
    print("Invalid API key")
except TemplateNotFoundError:
    print("Template not found")
except RateLimitError as e:
    print(f"Rate limited. Retry after: {e.retry_after}s")
except QuotaExceededError:
    print("Render quota exceeded")
except RenderError as e:
    print(f"Render/validation failed: {e.message}; field errors: {e.errors}")
except ServerError as e:
    print(f"Server error: {e.message}")
except PictifyError as e:
    print(f"Error: {e.message}")
```

Status → error mapping: `401 → AuthenticationError`, `402 → QuotaExceededError`, `404 → TemplateNotFoundError`, `422 → RenderError` (with field-level `errors`), `429 → QuotaExceededError` when `code == "quota_exceeded"` else `RateLimitError`, other 4xx → `RenderError`, `5xx → ServerError`. Only 5xx and network errors are retried.

## Type Hints

The SDK ships full type hints and Pydantic result models:

```python
from pictify import (
    Pictify,
    AsyncPictify,
    ImageResult,
    RenderResult,
    RenderResultItem,
    GifRenderResult,
    BatchRenderResult,
    BatchResults,
    Template,
    ListTemplatesResult,
    ImageFormat,
    GifQuality,
)
```

## License

MIT
