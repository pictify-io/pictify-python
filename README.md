# Pictify Python SDK

Official Python SDK for [Pictify](https://pictify.io) - Generate images from HTML templates.

## Installation

```bash
pip install pictify
```

For async support:

```bash
pip install pictify[async]
```

## Quick Start

```python
from pictify import Pictify

client = Pictify(api_key="your-api-key")

# Render an image
result = client.render(
    template_id="your-template-id",
    variables={
        "title": "Hello World",
        "subtitle": "Generated with Pictify"
    }
)

print(result.image_url)
```

## Async Usage

```python
import asyncio
from pictify import AsyncPictify

async def main():
    async with AsyncPictify(api_key="your-api-key") as client:
        result = await client.render(
            template_id="your-template-id",
            variables={"title": "Hello World"}
        )
        print(result.image_url)

asyncio.run(main())
```

## Features

### Render Options

```python
result = client.render(
    template_id="your-template-id",
    variables={"title": "Hello World"},
    format="png",           # png, jpg, jpeg, webp, gif, pdf
    width=1200,             # Output width
    height=630,             # Output height
    device_scale_factor=2,  # Retina images
    transparent=True,       # Transparent background (PNG only)
    quality=90,             # JPEG/WebP quality (1-100)
)
```

### Stream Response

```python
# Stream image bytes directly
with open("output.png", "wb") as f:
    for chunk in client.render_stream(
        template_id="your-template-id",
        variables={"title": "Hello World"}
    ):
        f.write(chunk)
```

### Layout Variants

Templates can have multiple layout variants (e.g. landscape, square, story) created via AI Resize in the Pictify editor. You can render a specific layout or multiple layouts in a single call.

```python
# Render a single layout variant
result = client.render(
    template_id="your-template-id",
    variables={"title": "Hello World"},
    layout="twitter-post"
)
print(result.results[0].url)  # URL for the twitter-post variant

# Render multiple layout variants at once
result = client.render(
    template_id="your-template-id",
    variables={"title": "Hello World"},
    layouts=["default", "twitter-post", "instagram-story"]
)
for item in result.results:
    print(f"{item.layout}: {item.url} ({item.width}x{item.height})")
```

The render response always includes a `results` list of `RenderResultItem` objects, each containing `layout`, `url`, `width`, `height`, and `format`. For backward compatibility, `result.url` returns the URL of the first result.

### Batch Rendering

```python
result = client.render_batch(
    template_id="your-template-id",
    items=[
        {"variables": {"title": "Image 1"}},
        {"variables": {"title": "Image 2"}},
        {"variables": {"title": "Image 3"}},
    ],
    format="png"
)

# Each item contains a nested results list (one entry per layout)
for item in result.results:
    print(f"Item {item.index}: success={item.success}")
    for r in item.results:
        print(f"  {r.layout} ({r.width}x{r.height}): {r.url}")
```

#### Batch with layouts

Pass `layout` for a single variant or `layouts` for multiple variants across all batch items:

```python
# Single layout for all batch items
result = client.render_batch(
    template_id="your-template-id",
    items=[
        {"variables": {"title": "Card 1"}},
        {"variables": {"title": "Card 2"}},
    ],
    layout="twitter-post"
)

# Multiple layouts for all batch items
result = client.render_batch(
    template_id="your-template-id",
    items=[
        {"variables": {"title": "Card 1"}},
        {"variables": {"title": "Card 2"}},
    ],
    layouts=["default", "twitter-post"]
)

# Access per-item, per-layout results
for item in result.results:
    for r in item.results:
        print(f"Item {item.index} / {r.layout}: {r.url}")
    for e in item.errors:
        print(f"Item {item.index} / {e.layout} failed: {e.error}")
```

### Template Management

```python
# Get template details
template = client.get_template("your-template-id")
print(f"Template: {template.name}")
print(f"Variables: {[v.name for v in template.variables]}")

# List all templates
templates = client.list_templates(limit=10)
for t in templates:
    print(f"{t.id}: {t.name}")
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
)

client = Pictify(api_key="your-api-key")

try:
    result = client.render(
        template_id="your-template-id",
        variables={"title": "Hello World"}
    )
except AuthenticationError:
    print("Invalid API key")
except TemplateNotFoundError as e:
    print(f"Template not found: {e.template_id}")
except RateLimitError as e:
    print(f"Rate limited. Retry after: {e.retry_after}s")
except QuotaExceededError:
    print("Account quota exceeded")
except RenderError as e:
    print(f"Render failed: {e.message}")
except PictifyError as e:
    print(f"Error: {e.message}")
```

## Framework Examples

### Flask

```python
from flask import Flask, Response
from pictify import Pictify

app = Flask(__name__)
client = Pictify(api_key="your-api-key")

@app.route("/og-image")
def og_image():
    def generate():
        for chunk in client.render_stream(
            template_id="your-template-id",
            variables={"title": "Dynamic OG Image"}
        ):
            yield chunk

    return Response(generate(), mimetype="image/png")
```

### FastAPI

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pictify import AsyncPictify

app = FastAPI()
client = AsyncPictify(api_key="your-api-key")

@app.get("/og-image")
async def og_image():
    async def generate():
        async for chunk in client.render_stream(
            template_id="your-template-id",
            variables={"title": "Dynamic OG Image"}
        ):
            yield chunk

    return StreamingResponse(generate(), media_type="image/png")
```

### Django

```python
from django.http import StreamingHttpResponse
from pictify import Pictify

client = Pictify(api_key="your-api-key")

def og_image(request):
    def generate():
        for chunk in client.render_stream(
            template_id="your-template-id",
            variables={"title": request.GET.get("title", "Hello")}
        ):
            yield chunk

    return StreamingHttpResponse(generate(), content_type="image/png")
```

## Configuration

```python
client = Pictify(
    api_key="your-api-key",
    base_url="https://api.pictify.io",  # Custom API URL
    timeout=30.0,                           # Request timeout in seconds
    max_retries=3,                          # Max retry attempts
)
```

## Type Hints

The SDK includes full type hints for all methods and classes:

```python
from pictify import (
    Pictify,
    RenderOptions,
    RenderResult,
    Template,
    TemplateVariable,
    ImageFormat,
)
```

## License

MIT
