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
directory is git-ignored and weighs about 200 MB. Reinstall it with::

    ./venv/bin/pip install -e '.[screenshots]'
    PLAYWRIGHT_BROWSERS_PATH=.playwright ./venv/bin/playwright install --only-shell chromium

``--only-shell`` is deliberate: photographing and measuring are headless, and the
shell alone serves them. Only ``--browse`` opens a window, and it needs the full
browser, another 356 MB installed by dropping the flag. Both were kept until
September 2026, when the two were measured against each other and agreed to the
decimal on every contrast in ``ink_contrast.md`` — the headed half was disk spent
on a window that the machine's own browser already provides.

**It needs the network.** The browser fetches from Open-Meteo, exactly as a
visitor's would — that is the whole architecture. Which also means the future is
only served where the correction grid has nodes, so the searches below use Paris
for what must succeed and Pontarlier for the refusal.

**Unless ``--offline``, which invents the weather.** The rate limit is a daily
one, and a day spent waiting for it is a day the interface cannot be looked at.
In that mode Playwright answers the Open-Meteo calls itself, with figures this
script makes up. Everything downstream is the real thing — the same server, the
same assembly, the same correction, the same sky rules — only the source is not.

    **The numbers in an offline shot are fabricated.** They say nothing about
    any place or any day, and a picture taken this way must never be shown as
    though it came from data. That is why they land in ``shots/offline/`` rather
    than beside the real ones.

**``--browse`` opens a window instead of shooting one.** Photographing is the
middle step of a design loop, not the loop: this leaves a real browser open on a
chosen view, stub included, so a stylesheet can be edited and reloaded against
live pages. Close the window to give the shell back.

Usage::

    ./venv/bin/python scripts/screenshots.py
    ./venv/bin/python scripts/screenshots.py --only results results-dark
    ./venv/bin/python scripts/screenshots.py --offline
    ./venv/bin/python scripts/screenshots.py --offline --browse
    ./venv/bin/python scripts/screenshots.py --offline --browse results-forecast
"""

from __future__ import annotations

import argparse
import json
import math
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

# The season bound is served, never copied: the refusal view builds its range
# from the same constant the API enforces.
from weather_simulator.api import validation  # noqa: E402

OUT = ROOT / "shots"

PARIS = {"lieu": "Paris", "lat": "48.8566", "lon": "2.3522"}
# Well outside the French box. It used to be the refusal case — the grid had no
# nodes there, so a far future was turned away — and it is now the opposite: the
# place that proves a search is answered anywhere in the world. What it shows is
# an uncorrected projection, which is why the shot is worth taking.
SANTIAGO = {"lieu": "Santiago", "lat": "-33.4489", "lon": "-70.6693"}
# The one place in the set where the humid-heat line has anything to say. Paris
# never reaches the first level and never will in this century, so every other
# view photographs the mark's absence — which is worth photographing, and is not
# a substitute for seeing it drawn.
DUBAI = {"lieu": "Dubaï", "lat": "25.2048", "lon": "55.2708"}

DESKTOP = {"width": 1440, "height": 960}
PHONE = {"width": 360, "height": 780}


# --- the invented weather, for --offline only ---------------------------------
#
# Plausible rather than realistic, and the distinction matters: the point is to
# exercise every branch of the display, not to resemble a place. So the year
# swings, the days wobble, and the wobble is seeded by the date — the same run
# twice gives the same picture, which is what makes two screenshots comparable.


def _invent(day: date, latitude: float, variable: str) -> float | None:
    season = math.cos((day.timetuple().tm_yday - 202) / 365.25 * 2 * math.pi)
    if latitude < 0:  # southern hemisphere: the same year, half a turn round
        season = -season
    # Deterministic wobble in [-1, 1], stable for a given day and variable.
    wobble = (math.sin(day.toordinal() * 12.9898 + len(variable) * 78.233) * 43758.5453) % 2 - 1

    # ``season`` peaks at +1 around 21 July, so it is *added*: subtracting it put
    # a Parisian August at -14 °C, under snow. Crude on purpose — a latitude
    # gradient this flat is wrong everywhere by a few degrees, which is enough to
    # fill a strip and not enough to mistake for data.
    warmth = 32 - abs(latitude) * 0.32 + season * 8 + wobble * 3.5
    if variable == "temperature_2m_max":
        return round(warmth + 5, 1)
    if variable == "temperature_2m_min":
        return round(warmth - 4, 1)
    if variable == "temperature_2m_mean":
        return round(warmth, 1)
    if variable == "cloud_cover_mean":
        # Spread across the whole range on purpose: all five sky classes have to
        # turn up in the strip, or the picture shows one card eighty times.
        return round(min(100.0, max(0.0, 50 + season * 18 + wobble * 45)), 0)
    if variable == "precipitation_sum":
        return round(max(0.0, wobble * 9 - 3), 1)
    if variable == "snowfall_sum":
        return round(max(0.0, wobble * 4 - 3), 1) if warmth < 2 else 0.0
    if variable == "dew_point_2m_mean":
        # Tied to the day's own mean temperature rather than wandering on a seed
        # of its own: a dew point free of the temperature beside it would put fog
        # on a hot afternoon and hand the wet bulb combinations no place on Earth
        # produces. What varies is the spread between the two, which is what
        # decides whether a day carries a humid-heat level at all.
        return round(_invent(day, latitude, "temperature_2m_mean") - (2 + abs(wobble) * 9), 1)
    if variable == "wind_speed_10m_max":
        return round(12 + abs(wobble) * 38, 1)
    if variable == "wind_speed_10m_mean":
        return round(5 + abs(wobble) * 16, 1)
    return None


def _payload(url: str, today: date, lag: int) -> dict:
    """What Open-Meteo would have answered — shape faithful, figures invented."""
    from urllib.parse import parse_qs, urlsplit

    query = parse_qs(urlsplit(url).query)
    first = date.fromisoformat(query["start_date"][0])
    last = date.fromisoformat(query["end_date"][0])
    latitude = float(query["latitude"][0])
    model = query["models"][0]

    # The reanalyses run days behind. Without that the first seam never appears,
    # and the strip would show a changeover the real series does not have there.
    served_until = today - timedelta(days=lag) if model in {"era5_land", "era5"} else None

    days = [first + timedelta(days=n) for n in range((last - first).days + 1)]
    daily: dict[str, list] = {"time": [day.isoformat() for day in days]}
    for variable in query["daily"]:
        daily[variable] = [
            None
            if served_until is not None and day > served_until
            else _invent(day, latitude, variable)
            for day in days
        ]
    return {
        "latitude": latitude,
        "longitude": float(query["longitude"][0]),
        "elevation": 42.0,
        "generationtime_ms": 0.1,
        "utc_offset_seconds": 7200,
        "daily": daily,
    }


def _geocoded(url: str) -> dict:
    """Enough of a geocoding answer for the candidate list to draw. Also invented."""
    from urllib.parse import parse_qs, urlsplit

    name = parse_qs(urlsplit(url).query).get("name", ["Lieu"])[0]
    return {
        "results": [
            {
                "id": index,
                "name": name,
                "latitude": 48.9 - index * 0.7,
                "longitude": 2.35 + index * 0.9,
                "country_code": "FR",
                "country": "France",
                "admin1": admin,
            }
            for index, admin in enumerate(
                ["Île-de-France", "La Réunion", "Seine-Saint-Denis", "Oise"]
            )
        ]
    }


def stub_openmeteo(page: Page, today: date, lag: int) -> None:
    """Answer every Open-Meteo call from this process instead of the network."""

    def handle(route) -> None:
        url = route.request.url
        body = _geocoded(url) if "geocoding-api" in url else _payload(url, today, lag)
        route.fulfill(body=json.dumps(body), content_type="application/json")

    page.route("**://*.open-meteo.com/**", handle)


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

    The cap was 3000 px, which was the height of the tallest page there was.
    The documentation page runs past that and came out beheaded at the foot;
    8000 clears it with room. Nothing else moves — every other view measures
    under 3000 and is capped by its own height, not by this number, which is
    only here so a runaway page cannot ask for a screenshot of a gigabyte.
    """
    height = page.evaluate("document.body.scrollHeight")
    page.set_viewport_size({"width": size["width"], "height": min(height, 8000)})


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


def documentation(page: Page, base: str) -> None:
    """The third page. Nothing to wait for that `goto` has not already waited on:
    it loads no module, fetches nothing, and is complete the moment it parses —
    which is the property being photographed as much as the layout is."""
    page.goto(f"{base}/documentation")


def home_candidates(page: Page, base: str) -> None:
    home(page, base)
    page.fill("#lieu", "Saint-Denis")  # eight of them in France — the reason to choose
    page.wait_for_selector(".candidate")


def home_season(page: Page, base: str) -> None:
    """The other way of asking: a season and a year instead of two dates.

    Waiting on the panel and not on the click: the year list is built from
    `/api/config`, so a shot taken the instant the switch is pressed catches an
    empty select.
    """
    home(page, base)
    page.click("#mode-season")
    page.wait_for_selector("#panel-season:not([hidden])")
    page.wait_for_function("() => document.getElementById('annee').value !== ''")


def results(page: Page, base: str) -> None:
    # Wide enough to clear the forecast horizon, so the seam falls inside the
    # strip: ten days back plus a fortnight ahead would end on the last forecast
    # day and show no crossing at all.
    today = date.today()
    page.goto(results_url(base, PARIS, today - timedelta(days=10), today + timedelta(days=40)))
    page.wait_for_selector(".seam", timeout=90_000)


def results_forecast(page: Page, base: str) -> None:
    """The fortnight ahead, alone: a forecast, so no warning and no seam.

    The view worth looking at hardest. Nothing here may announce a simulation —
    these days are weather — and the page must therefore come up bare.
    """
    today = date.today()
    page.goto(results_url(base, PARIS, today + timedelta(days=1), today + timedelta(days=14)))
    page.wait_for_selector(".card", timeout=90_000)


def results_humid(page: Page, base: str) -> None:
    """A Gulf summer, where the humid-heat line is not empty.

    The view exists because every other one is Paris, and Paris never crosses
    the first level — so the whole set would photograph the mark's absence and
    nothing else. Here the strip reserves its line and fills some of it, which
    is the case the reserving was built for: the cards must keep one height and
    the calm days must read as calm rather than as unrendered.
    """
    page.goto(results_url(base, DUBAI, date(2046, 7, 15), date(2046, 8, 25)))
    page.wait_for_selector(".card-humid[data-humid]", timeout=90_000)


def results_seam(page: Page, base: str) -> None:
    """The strip scrolled to where the observed stops — otherwise it is off-screen."""
    results(page, base)
    page.eval_on_selector(".seam", "node => node.scrollIntoView({inline: 'center'})")
    page.wait_for_timeout(300)


def results_compare(page: Page, base: str) -> None:
    """A summer of 2046 with 1991 laid under it, in grey.

    A whole season rather than the crossing view: the comparison is about the
    shape of a period, and ninety-two days is where two curves either separate
    or do not. Waiting on the grey line and not on the click — the compared year
    is a second search, and a shot taken as the button goes down catches the
    chart before it is redrawn.
    """
    page.goto(results_url(base, PARIS, date(2046, 6, 21), date(2046, 9, 20)))
    page.wait_for_selector("#compare:not([hidden])", timeout=90_000)
    page.click("#compare-toggle")
    page.wait_for_selector(".chart-line.past", timeout=90_000)


def results_refused(page: Page, base: str) -> None:
    """What a refusal looks like, now that the out-of-grid one is gone.

    This view photographed a place the correction grid could not reach until the
    projection began being served there uncorrected. There is no longer any
    refusal that turns on *where* a search is made, so the subject had to move
    to one that turns on what it asks: a range longer than the season the API
    serves.

    The range is built from ``MAX_DAYS`` rather than from a number typed here,
    so the day that bound moves this view follows it instead of quietly
    photographing a page that loads fine — which is exactly how the previous
    subject decayed.
    """
    today = date.today()
    too_long = today + timedelta(days=validation.MAX_DAYS + 30)
    page.goto(results_url(base, PARIS, today, too_long))
    page.wait_for_selector(".failure:not([hidden])", timeout=90_000)


# The four grounds.
#
# Fixed dates in a year gone by, and both halves of that matter. **Past**, so the
# range is served everywhere in the world and asks the correction grid for
# nothing — these views work on the network as well as offline. **Fixed**, so a
# shot taken in February is comparable with one taken in August: a range counted
# from today would drift through the seasons and photograph a different ground
# every few weeks, which is the one thing a set of four must not do.
#
# They carry neither warning nor seam, every day in them being observed. That is
# not a gap: the ground is what they are for, and `results` goes on showing the
# crossing, on whatever season the day of the shot falls in.
SEASON_RANGES = {
    "winter": (date(2025, 1, 5), date(2025, 2, 20)),
    "spring": (date(2025, 4, 5), date(2025, 5, 20)),
    "summer": (date(2025, 7, 5), date(2025, 8, 20)),
    "autumn": (date(2025, 10, 5), date(2025, 11, 20)),
}


def season_view(start: date, end: date):
    """One of the four, waiting on a card as the others do."""

    def shoot(page: Page, base: str) -> None:
        page.goto(results_url(base, PARIS, start, end))
        page.wait_for_selector(".card", timeout=90_000)

    return shoot


VIEWS = {
    "home": (home, DESKTOP, "light"),
    "home-candidates": (home_candidates, DESKTOP, "light"),
    "home-season": (home_season, DESKTOP, "light"),
    "home-dark": (home, DESKTOP, "dark"),
    "documentation": (documentation, DESKTOP, "light"),
    "documentation-narrow": (documentation, PHONE, "light"),
    "results": (results, DESKTOP, "light"),
    "results-dark": (results, DESKTOP, "dark"),
    "results-seam": (results_seam, DESKTOP, "light"),
    "results-forecast": (results_forecast, DESKTOP, "light"),
    "results-compare": (results_compare, DESKTOP, "light"),
    "results-narrow": (results, PHONE, "light"),
    "results-refused": (results_refused, DESKTOP, "light"),
    "results-humid": (results_humid, DESKTOP, "light"),
    "results-humid-dark": (results_humid, DESKTOP, "dark"),
    **{
        f"results-{name}": (season_view(start, end), DESKTOP, "light")
        for name, (start, end) in SEASON_RANGES.items()
    },
}


def browse(playwright, base: str, view: str, offline: bool, lag: int) -> None:
    """Open a real window on the site and hand it over, until it is closed.

    The design loop is edit, look, edit again, and a screenshot is only the
    middle step. Here the browser stays open: change a stylesheet, reload, the
    change is there. The stub survives reloads — the route is registered on the
    page, not on a navigation — so the strip keeps its days without the network.

    Headed and nothing else. No dev switch on the server, no rewritten URLs: the
    invented data exists inside this browser and cannot reach anything else. A
    flag that made the application itself serve made-up weather would be one
    misconfiguration away from publishing it.
    """
    shoot, size, scheme = VIEWS[view]
    browser = playwright.chromium.launch(headless=False, args=["--lang=fr-FR"])
    context = browser.new_context(viewport=size, color_scheme=scheme, locale="fr-FR")
    page = context.new_page()
    if offline:
        stub_openmeteo(page, date.today(), lag)
    shoot(page, base)

    print(
        f"\n{view} ouvert. Modifiez le CSS, rechargez (⌘R). Fermez la fenêtre pour rendre la main."
    )
    closed = False

    def note_closure() -> None:
        nonlocal closed
        closed = True

    page.on("close", lambda _: note_closure())
    while not closed:
        try:
            page.wait_for_timeout(500)
        except Exception:  # the window went away mid-wait
            break
    browser.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", nargs="+", choices=sorted(VIEWS), help="a subset of the views")
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument(
        "--offline",
        action="store_true",
        help="inventer les données au lieu d'appeler Open-Meteo — chiffres faux",
    )
    parser.add_argument("--lag", type=int, default=6, help="retard des réanalyses, avec --offline")
    parser.add_argument(
        "--browse",
        nargs="?",
        const="results",
        choices=sorted(VIEWS),
        help="ouvrir une fenêtre sur cette vue au lieu de photographier",
    )
    chosen = parser.parse_args()

    wanted = chosen.only or list(VIEWS)
    # Fabricated shots never land beside real ones: a picture nobody can tell
    # apart from data is the one thing this mode must not produce.
    out = chosen.out or (OUT / "offline" if chosen.offline else OUT)
    out.mkdir(parents=True, exist_ok=True)
    if chosen.offline:
        print("!! mode hors réseau : les valeurs affichées sont inventées\n")

    port = free_port()
    server = serve(port)
    base = f"http://127.0.0.1:{port}"
    try:
        with sync_playwright() as playwright:
            if chosen.browse:
                browse(playwright, base, chosen.browse, chosen.offline, chosen.lag)
                return
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
                #
                # Reduced motion, so the banner question stops turning and two
                # runs are comparable. An accessibility setting rather than a
                # test hook: the still page is one real readers get, so a
                # screenshot of it is a screenshot of the site.
                context = browser.new_context(
                    viewport=size,
                    device_scale_factor=2,
                    color_scheme=scheme,
                    locale="fr-FR",
                    reduced_motion="reduce",
                )
                page = context.new_page()
                if chosen.offline:
                    stub_openmeteo(page, date.today(), chosen.lag)
                shoot(page, base)
                path = out / f"{name}.png"
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
