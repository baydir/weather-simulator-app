"""Fetch the hindcast of the five eligible models, and the reference, once.

Seventy requests over 36 years each: too slow and too rate-limited to repeat
every time a metric is reworked. Each payload is therefore written to disk as it
arrives and never fetched twice, so the run is resumable — if the rate limit
closes the door halfway through, the next run picks up where this one stopped.

The requests are built by ``weather_simulator.sources.openmeteo`` rather than
assembled here. That matters more than it looks: the models are forced
explicitly, the day boundary follows the location, and the eight variables are
the ones the application actually reads. A comparison run under any other
settings would rank the models on a series the application never shows.

``fetch_series`` is not used, and cannot be: it splits the range at today and
routes a past date to the archive. Here the past is deliberately asked *of the
climate models*, which is the whole point of a hindcast.

    python scripts/model_selection/collect.py

Run it twice if it stops early; it costs nothing to resume.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import CACHE_DIR, END, SITES, START  # noqa: E402

from weather_simulator.sources import openmeteo  # noqa: E402
from weather_simulator.sources.client import get_json  # noqa: E402
from weather_simulator.sources.errors import FetchError  # noqa: E402

# Open-Meteo weights a call by the span and the number of variables asked for,
# and 36 years of eight daily variables is a heavy one. The pause is deliberate
# and generous: the collection runs once.
PAUSE_SECONDS = 6

# The client's default backoff answers a transient failure — seconds, growing.
# It is the wrong scale here. Open-Meteo refuses bulk work with "try again in
# the next hour", and twenty-five seconds later the answer is still no: the
# first run burnt its four attempts inside two minutes and gave up on a site
# that a single longer wait would have caught. Five attempts spaced from five
# to twenty-five minutes span the hour the server actually asks for.
#
# This belongs to the collector, not to the client. On the request path a rate
# limit must fail fast and say so to the visitor, never sleep on their time.
BULK_RETRIES = 5
BULK_BACKOFF = 300


def _path(site: str, source: str) -> Path:
    return CACHE_DIR / f"{site}__{source}.json"


def _collect(site: str, source: str, request: tuple[str, dict[str, object]]) -> str:
    """Fetch one payload unless it is already on disk. Returns what happened."""
    target = _path(site, source)
    if target.exists():
        return "cached"

    url, params = request
    payload = get_json(url, params, retries=BULK_RETRIES, backoff=BULK_BACKOFF)
    # Written whole, response as received. The parsing — and the null detection
    # that goes with it — belongs to the analysis, not to the collection: a
    # payload rejected here would have to be re-fetched to be looked at.
    target.write_text(json.dumps(payload), encoding="utf-8")
    time.sleep(PAUSE_SECONDS)
    return "fetched"


def _requests(latitude: float, longitude: float) -> dict[str, tuple[str, dict[str, Any]]]:
    """The seven payloads one site needs: two for the reference, five hindcasts."""
    span = (latitude, longitude, START, END)
    requests: dict[str, tuple[str, dict[str, Any]]] = {
        openmeteo.TEMPERATURE_MODEL: openmeteo.archive_temperature_request(*span),
        openmeteo.SURFACE_MODEL: openmeteo.archive_surface_request(*span),
    }
    for model in openmeteo.ELIGIBLE_MODELS:
        requests[model] = openmeteo.climate_request(*span, model)
    return requests


def main() -> int:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    print(f"{START} -> {END}, {len(SITES)} sites, {len(openmeteo.ELIGIBLE_MODELS)} models")
    print(f"cache: {CACHE_DIR}\n")

    failures: list[str] = []
    for site, (latitude, longitude) in SITES.items():
        print(f"{site:<14}", end="", flush=True)
        for source, request in _requests(latitude, longitude).items():
            try:
                outcome = _collect(site, source, request)
            except FetchError as error:
                # One source failing is not a reason to lose the rest: the run
                # is resumable, so the gap is reported and picked up next time.
                failures.append(f"{site}/{source}: {error}")
                print(" !", end="", flush=True)
                continue
            print("." if outcome == "fetched" else "=", end="", flush=True)
        print()

    print("\n. fetched   = already cached   ! failed")
    if failures:
        print(f"\n{len(failures)} missing, run again to retry:")
        for failure in failures:
            print(f"  {failure}")
        return 1
    print("\ncomplete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
