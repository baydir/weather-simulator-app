"""Photograph the interface, so that a change to it can be looked at.

Nothing here is a test and nothing here asserts. It starts the application on a
free port, drives a real Chromium through the pages, and drops PNGs in ``shots/``.

**Why this exists rather than ``firefox --screenshot``.** That flag fires at the
load event, and at the load event the results page is empty: its days arrive
after four round trips to Open-Meteo. There is no way to tell it to wait. Here
the browser is driven over its debugging protocol, so the script can say *wait
until a card exists* and only then take the picture. The same limitation applies
to Chrome's own flag — it is the flag that is the problem, not the browser.

**The browser lives in the project**, under ``.playwright/``, not in the user
cache: ``PLAYWRIGHT_BROWSERS_PATH`` is set below before Playwright starts. That
directory is git-ignored and weighs about 560 MB. Reinstall it with::

    ./venv/bin/pip install -e '.[screenshots]'
    PLAYWRIGHT_BROWSERS_PATH=.playwright ./venv/bin/playwright install chromium

**It needs the network.** The browser fetches from Open-Meteo, exactly as a
visitor's would — that is the whole architecture. Which also means the future is
only served where the correction grid has nodes, so the searches below use Paris
for what must succeed and Pontarlier for the refusal.

Usage::

    ./venv/bin/python scripts/screenshots.py
    ./venv/bin/python scripts/screenshots.py --only results results-dark
"""

from __future__ import annotations

import argparse
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Before importing playwright: it reads this when it launches a browser, and
# the point is to keep Chromium inside the project rather than in ~/Library.
os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(ROOT / ".playwright"))

from playwright.sync_api import Page, sync_playwright  # noqa: E402

OUT = ROOT / "shots"

# Paris sits inside the three cells the collection has closed, so its future is
# served. Pontarlier does not, which is what makes it the refusal case.
PARIS = {"lieu": "Paris", "lat": "48.8566", "lon": "2.3522"}
PONTARLIER = {"lieu": "Pontarlier", "lat": "46.9036", "lon": "6.3547"}

DESKTOP = {"width": 1440, "height": 960}
PHONE = {"width": 360, "height": 780}


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def serve(port: int) -> subprocess.Popen:
    """Start the application and wait until it answers."""
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "weather_simulator.api.app:app", "--port", str(port)],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    for _ in range(60):
        if process.poll() is not None:
            raise SystemExit(f"the server stopped at start-up:\n{process.stderr.read().decode()}")
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/api/config", timeout=1).read()
            return process
        except (urllib.error.URLError, ConnectionError, TimeoutError):
            time.sleep(0.5)
    process.terminate()
    raise SystemExit("the server never answered")


def frame(page: Page, size: dict[str, int]) -> None:
    """Grow the viewport to the page's height, then shoot the viewport.

    Not ``full_page=True``, which measures ``documentElement.scrollWidth`` — and
    that reads 4769 px here, because it counts the strip's *internal* scroll.
    The page itself does not overflow: ``body.scrollWidth`` is the viewport's.
    Left alone, the screenshot came out five times too wide and everything in it
    was unreadably small.
    """
    height = page.evaluate("document.body.scrollHeight")
    page.set_viewport_size({"width": size["width"], "height": min(height, 3000)})


def results_url(base: str, place: dict[str, str], start: date, end: date) -> str:
    query = "&".join(
        f"{key}={value}"
        for key, value in {**place, "debut": start.isoformat(), "fin": end.isoformat()}.items()
    )
    return f"{base}/resultats?{query}"


# --- the views ----------------------------------------------------------------
#
# Each one says what it waits for. Waiting on a selector rather than on a delay
# is the difference between a picture of the page and a picture of a spinner.


def home(page: Page, base: str) -> None:
    page.goto(base)
    # The bounds arrive from /api/config; until they do, the form is half-built.
    page.wait_for_function("() => document.getElementById('debut').min !== ''")


def home_candidates(page: Page, base: str) -> None:
    home(page, base)
    page.fill("#lieu", "Saint-Denis")  # eight of them in France — the reason to choose
    page.wait_for_selector(".candidate")


def results(page: Page, base: str) -> None:
    # Straddling today, so the seam falls inside the strip.
    today = date.today()
    page.goto(results_url(base, PARIS, today - timedelta(days=10), today + timedelta(days=10)))
    page.wait_for_selector(".seam", timeout=90_000)


def results_seam(page: Page, base: str) -> None:
    """The strip scrolled to where the observed stops — otherwise it is off-screen."""
    results(page, base)
    page.eval_on_selector(".seam", "node => node.scrollIntoView({inline: 'center'})")
    page.wait_for_timeout(300)


def results_refused(page: Page, base: str) -> None:
    today = date.today()
    page.goto(results_url(base, PONTARLIER, today, today + timedelta(days=14)))
    page.wait_for_selector(".failure:not([hidden])", timeout=90_000)


VIEWS = {
    "home": (home, DESKTOP, "light"),
    "home-candidates": (home_candidates, DESKTOP, "light"),
    "home-dark": (home, DESKTOP, "dark"),
    "results": (results, DESKTOP, "light"),
    "results-dark": (results, DESKTOP, "dark"),
    "results-seam": (results_seam, DESKTOP, "light"),
    "results-narrow": (results, PHONE, "light"),
    "results-refused": (results_refused, DESKTOP, "light"),
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", nargs="+", choices=sorted(VIEWS), help="a subset of the views")
    parser.add_argument("--out", type=Path, default=OUT)
    chosen = parser.parse_args()

    wanted = chosen.only or list(VIEWS)
    chosen.out.mkdir(parents=True, exist_ok=True)

    port = free_port()
    server = serve(port)
    base = f"http://127.0.0.1:{port}"
    try:
        with sync_playwright() as playwright:
            # --lang, and not only the context locale: a date input renders its
            # format from the browser's *interface* language, so without this
            # the form showed 08/21/2026 to a French visitor.
            browser = playwright.chromium.launch(args=["--lang=fr-FR"])
            for name in wanted:
                shoot, size, scheme = VIEWS[name]
                # Two device pixels per CSS pixel, and the theme forced here
                # rather than on the machine — so both can be seen at once.
                # French locale, or the date fields render as 08/21/2026 and
                # the screenshot shows a page no French visitor would see.
                context = browser.new_context(
                    viewport=size,
                    device_scale_factor=2,
                    color_scheme=scheme,
                    locale="fr-FR",
                )
                page = context.new_page()
                shoot(page, base)
                path = chosen.out / f"{name}.png"
                frame(page, size)
                page.screenshot(path=path)
                print(f"{name:18} {path.relative_to(ROOT)}")
                context.close()
            browser.close()
    finally:
        server.terminate()
        server.wait()


if __name__ == "__main__":
    main()
