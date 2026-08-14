"""The two pages and their files, served by the same application as the API.

``TestClient(app)`` without a context manager runs no lifespan, so the shipped
correction table is never read here — the same arrangement as ``test_api.py``.

The last test is the one worth having: docs/application.md plans for a static
frontend served by a CDN, so the API must start with no ``web/`` beside it. A
mount written outside that condition would only fail in the deployment nobody
runs locally.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from weather_simulator.api.app import app, mount_web

WEB = Path(__file__).resolve().parents[1] / "web"


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
        "/static/js/season.js",
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
    assert config.json()["max_days"] == 92


def test_every_season_the_page_can_name_has_a_palette() -> None:
    """The one join between `season.js` and the stylesheet, and it is by name.

    A season the script can write and the sheet cannot paint leaves the page
    with no gradient at all — `--sky` undefined, the sky layer blank. Nothing
    else would catch it: the two files never meet, they only agree.
    """
    sheet = (WEB / "static/css/style.css").read_text()
    # Every name the module can hand back, read off the one table it hands them
    # back from. It used to read the `return "winter"` literals; the table that
    # let the module also *build* a season took them away, and the join is the
    # same join — a name the script can write and the sheet cannot paint.
    written = set(re.findall(r'name: "(\w+)"', (WEB / "static/js/season.js").read_text()))
    painted = set(re.findall(r'body\.results\[data-season="(\w+)"\]', sheet))
    assert written == painted == {"winter", "spring", "summer", "autumn"}


def test_the_results_page_carries_a_season_of_its_own() -> None:
    """The fallback for a URL with no usable range, and the only one there is.

    `results.js` writes nothing when it cannot count days, on purpose: two
    fallbacks would be a second place to keep a season name.
    """
    assert 'data-season="summer"' in (WEB / "pages/results.html").read_text()


def test_nothing_is_mounted_without_the_web_directory(tmp_path) -> None:
    """No pages, no mount, and no exception either."""
    bare = FastAPI()
    assert mount_web(bare, tmp_path / "absent") is False
    assert TestClient(bare).get("/").status_code == 404
