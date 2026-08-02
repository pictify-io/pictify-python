"""Pytest fixtures and configuration for Pictify SDK unit tests.

Mock payloads mirror the REAL Pictify API wire format (camelCase keys), so the
SDK's snake_case aliasing is exercised through the mocks.
"""

import pytest
import respx


@pytest.fixture
def mock_image_result():
    """Mock `/image` response (render_html / render_url)."""
    return {
        "url": "https://cdn.pictify.io/renders/abc123.png",
        "id": "img_abc123",
        "createdAt": "2026-06-08T10:30:00Z",
    }


@pytest.fixture
def mock_render_result():
    """Mock template render response (`/templates/:uid/render`)."""
    return {
        "results": [
            {
                "layout": "default",
                "url": "https://cdn.pictify.io/renders/default.png",
                "width": 600,
                "height": 200,
                "format": "png",
                "name": "Default",
                "id": "img_default",
                "createdAt": "2026-06-08T10:30:00Z",
            }
        ],
        "errors": [],
        "totalLayouts": 1,
        "totalRendered": 1,
        "totalErrors": 0,
        "templateUid": "tmpl_abc123",
    }


@pytest.fixture
def mock_layout_render_result():
    """Mock template render response with multiple layouts + an error."""
    return {
        "results": [
            {
                "layout": "default",
                "url": "https://cdn.pictify.io/renders/default.png",
                "width": 600,
                "height": 200,
                "format": "png",
                "name": "Default",
                "id": "img_default",
                "createdAt": "2026-06-08T10:30:00Z",
            },
            {
                "layout": "square",
                "url": "https://cdn.pictify.io/renders/square.png",
                "width": 1080,
                "height": 1080,
                "format": "png",
                "name": "Square",
                "id": "img_square",
                "createdAt": "2026-06-08T10:30:00Z",
            },
        ],
        "errors": [{"layout": "bogus", "error": "Layout not found"}],
        "totalLayouts": 3,
        "totalRendered": 2,
        "totalErrors": 1,
        "templateUid": "tmpl_abc123",
    }


@pytest.fixture
def mock_gif_result():
    """Mock `/gif` response — note the nested `gif` envelope."""
    return {
        "gif": {
            "url": "https://cdn.pictify.io/renders/abc123.gif",
            "uid": "gif_abc123",
            "width": 400,
            "height": 200,
            "animationLength": 2000,
        },
        "_meta": {"processingTime": 1234},
    }


@pytest.fixture
def mock_batch_submit_result():
    """Mock `/templates/:uid/batch-render` 202 response."""
    return {
        "batchId": "batch_abc123",
        "status": "pending",
        "totalItems": 2,
    }


@pytest.fixture
def mock_batch_results():
    """Mock `/templates/batch/:batchId/results` response (no URLs)."""
    return {
        "batchId": "batch_abc123",
        "status": "processing",
        "progress": 50,
        "totalItems": 2,
        "completedItems": 1,
        "failedItems": 0,
        "results": [{"index": 0, "success": True, "variables": ["name", "company"]}],
        "errors": [],
        "createdAt": "2026-06-08T10:30:00Z",
        "startedAt": "2026-06-08T10:30:01Z",
    }


@pytest.fixture
def mock_template():
    """Mock template object (as nested under the `template` envelope)."""
    return {
        "uid": "tmpl_abc123",
        "name": "OG Image Template",
        "html": "<div>Hi {{name}} from {{company}}</div>",
        "width": 600,
        "height": 200,
        "engine": "html",
        "outputFormat": "image",
        "variables": ["name", "company"],
        "variableDefinitions": [
            {"name": "name", "type": "string"},
            {"name": "company", "type": "string"},
        ],
        "createdAt": "2026-06-08T10:30:00Z",
        "updatedAt": "2026-06-08T10:30:00Z",
    }


@pytest.fixture
def mock_template_envelope(mock_template):
    """Mock `GET /templates/:uid` and `POST /templates` response."""
    return {"template": mock_template}


@pytest.fixture
def mock_list_templates_result(mock_template):
    """Mock `GET /templates` response."""
    return {
        "templates": [mock_template],
        "pagination": {
            "page": 1,
            "limit": 12,
            "total": 1,
            "totalPages": 1,
            "hasNext": False,
            "hasPrev": False,
        },
    }


@pytest.fixture
def mock_video_template():
    """Mock video template object (as nested under the `template` envelope)."""
    return {
        "uid": "vid_abc123",
        "name": "Promo",
        "kind": "tsx",
        "width": 1080,
        "height": 1080,
        "fps": 30,
        "durationInFrames": 240,
        "posterUrl": "https://media.pictify.io/posters/vid_abc123.png",
        "status": "draft",
        "variableDefinitions": [
            {"name": "title", "type": "string", "defaultValue": "Hello"},
        ],
        "createdAt": "2026-08-02T10:30:00Z",
        "updatedAt": "2026-08-02T10:30:00Z",
    }


@pytest.fixture
def mock_video_template_envelope(mock_video_template):
    """Mock `POST /video/templates` response."""
    return {"template": mock_video_template}


@pytest.fixture
def mock_list_video_templates_result(mock_video_template):
    """Mock `GET /video/templates` response."""
    return {"templates": [mock_video_template]}


@pytest.fixture
def mock_video_variables_result():
    """Mock `GET /video/templates/:uid/variables` response."""
    return {
        "templateUid": "vid_abc123",
        "templateName": "Promo",
        "kind": "tsx",
        "variables": [
            {"name": "title", "type": "string", "defaultValue": "Hello"},
            {"name": "accent", "type": "color", "defaultValue": "#ff5500"},
        ],
        "referenced": ["title", "accent"],
    }


@pytest.fixture
def mock_render_video_result():
    """Mock `POST /video/templates/:uid/render` response."""
    return {
        "url": "https://media.pictify.io/videos/abc123.mp4",
        "durationInFrames": 240,
        "format": "mp4",
    }


@pytest.fixture
def mock_generate_video_result(mock_video_template):
    """Mock `POST /video/templates/generate` response."""
    return {
        "template": mock_video_template,
        "previewUrl": "https://media.pictify.io/previews/vid_abc123.png",
    }


@pytest.fixture
def respx_mock():
    """Create a respx mock context."""
    with respx.mock:
        yield respx
