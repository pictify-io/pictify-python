"""Fixtures and configuration for Pictify integration tests.

These tests hit the REAL Pictify API at https://api.pictify.io. They are
skipped automatically when ``PICTIFY_API_KEY`` is not set in the environment,
so a normal ``pytest`` run never touches the network.

Run them explicitly with::

    PICTIFY_API_KEY=xxx .venv/bin/python -m pytest tests/integration

Optional environment variables:

- ``PICTIFY_API_KEY``     (required) API key used for all requests.
- ``PICTIFY_BASE_URL``    (optional) override the API base URL.
- ``PICTIFY_TEMPLATE_ID`` (optional) a real template ID for template-based
                          render / get_template tests. Tests that need a
                          template skip when this is absent.
"""

import os

import pytest

API_KEY = os.environ.get("PICTIFY_API_KEY")
BASE_URL = os.environ.get("PICTIFY_BASE_URL")
TEMPLATE_ID = os.environ.get("PICTIFY_TEMPLATE_ID")


@pytest.fixture
def api_key() -> str:
    """Return the configured API key (tests are skipped if it is missing)."""
    return API_KEY or ""


@pytest.fixture
def base_url():
    """Return an optional custom base URL, or None to use the SDK default."""
    return BASE_URL


@pytest.fixture
def template_id():
    """Return an optional real template ID for template-based tests."""
    return TEMPLATE_ID


@pytest.fixture
def client(api_key, base_url):
    """Provide a live synchronous Pictify client, closed on teardown."""
    from pictify import Pictify

    kwargs = {"api_key": api_key}
    if base_url:
        kwargs["base_url"] = base_url
    c = Pictify(**kwargs)
    try:
        yield c
    finally:
        c.close()


@pytest.fixture
async def async_client(api_key, base_url):
    """Provide a live asynchronous Pictify client, closed on teardown."""
    from pictify import AsyncPictify

    kwargs = {"api_key": api_key}
    if base_url:
        kwargs["base_url"] = base_url
    c = AsyncPictify(**kwargs)
    try:
        yield c
    finally:
        await c.close()
