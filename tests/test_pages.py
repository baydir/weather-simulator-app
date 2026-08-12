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
        "/static/js/prompt.js",
        "/static/js/home.js",
        "/static/js/results.js",
        "/static/css/style.css",
        "/static/icon.svg",
    ],
)
def test_static_files_are_served(client: TestClient, path: str) -> None:
    assert client.get(path).status_code == 200


@pytest.mark.parametrize("path", ["/", "/resultats", "/static/js/i18n.js", "/static/css/style.css"])
def test_the_browser_is_told_to_ask_before_reusing(client: TestClient, path: str) -> None:
    """No ``Cache-Control`` and the browser invents one.

    Starlette sends an ETag and a Last-Modified but no instruction, so a browser
    falls back on a heuristic and may reuse a module without asking. Invisible in
    production, where nothing moves between two visits; maddening while the
    interface is being worked on, where an edited stylesheet does not arrive.

    ``no-cache`` is not ``no-store``: the copy is kept and an unchanged file
    comes back as a 304. It holds as long as the URLs carry no version.
    """
    assert client.get(path).headers["cache-control"] == "no-cache"


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
