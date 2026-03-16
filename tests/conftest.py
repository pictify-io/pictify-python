"""Pytest fixtures and configuration for Pictify SDK tests."""

import pytest
import respx
from httpx import Response


@pytest.fixture
def mock_render_result():
    """Mock render result data."""
    return {
        "image_url": "https://cdn.pictify.io/renders/abc123.png",
        "render_id": "render_abc123",
        "width": 1200,
        "height": 630,
        "size": 45678,
        "format": "png",
        "render_time": 234,
    }


@pytest.fixture
def mock_template():
    """Mock template data."""
    return {
        "id": "tmpl_abc123",
        "name": "OG Image Template",
        "description": "Template for Open Graph images",
        "width": 1200,
        "height": 630,
        "variables": [
            {"name": "title", "type": "string", "required": True},
            {"name": "description", "type": "string", "required": False},
        ],
        "preview_url": "https://cdn.pictify.io/previews/tmpl_abc123.png",
        "created_at": "2024-01-15T10:30:00Z",
        "updated_at": "2024-01-15T10:30:00Z",
    }


@pytest.fixture
def mock_batch_result():
    """Mock batch render result data."""
    return {
        "results": [
            {
                "index": 0,
                "success": True,
                "variables": ["title"],
                "results": [
                    {
                        "layout": "default",
                        "name": "Default",
                        "url": "https://cdn.pictify.io/renders/abc123.png",
                        "width": 1200,
                        "height": 630,
                        "format": "png",
                        "id": "img_abc123",
                    }
                ],
                "errors": [],
            }
        ],
        "total_time": 500,
        "success_count": 1,
        "failed_count": 0,
    }


@pytest.fixture
def mock_gif_result():
    """Mock GIF render result data."""
    return {
        "gif_url": "https://cdn.pictify.io/renders/abc123.gif",
        "render_id": "render_abc123",
        "width": 800,
        "height": 600,
        "size": 123456,
        "frame_count": 3,
        "duration": 300,
        "render_time": 1234,
    }


@pytest.fixture
def respx_mock():
    """Create a respx mock context."""
    with respx.mock:
        yield respx
