"""The two pages and their files, served by the same application as the API.

``TestClient(app)`` without a context manager runs no lifespan, so the shipped
correction table is never read here — the same arrangement as ``test_api.py``.

The last test is the one worth having: docs/application.md plans for a static
frontend served by a CDN, so the API must start with no ``web/`` beside it. A
mount written outside that condition would only fail in the deployment nobody
runs locally.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from weather_simulator.api.app import app, mount_web


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.mark.parametrize("path", ["/", "/resultats"])
def test_pages_are_served_as_html(client: TestClient, path: str) -> None:
    response = client.get(path)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")


@pytest.mark.parametrize(
    "path",
    [
        "/static/js/fetch.js",
        "/static/js/i18n.js",
        "/static/js/present.js",
        "/static/js/dom.js",
        "/static/js/band.js",
        "/static/js/bounds.js",
        "/static/js/home.js",
        "/static/js/results.js",
        "/static/css/style.css",
        "/static/icon.svg",
    ],
)
def test_static_files_are_served(client: TestClient, path: str) -> None:
    assert client.get(path).status_code == 200


def test_api_still_answers(client: TestClient) -> None:
    """The pages are mounted alongside the API, not in front of it."""
    config = client.get("/api/config")
    assert config.status_code == 200
    assert config.json()["max_days"] == 90


def test_nothing_is_mounted_without_the_web_directory(tmp_path) -> None:
    """No pages, no mount, and no exception either."""
    bare = FastAPI()
    assert mount_web(bare, tmp_path / "absent") is False
    assert TestClient(bare).get("/").status_code == 404
