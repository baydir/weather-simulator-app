"""Thirty years of French daily temperatures, for placing a colour scale on them.

    ./venv/bin/python scripts/temperature_scale/collect.py

One request per site, cached in ``data/temperature_scale/`` and never fetched
again; ``scale.py`` re-runs the analysis offline from there. Twelve sites,
1981-2010, ERA5-Land.

**Why cities rather than a grid.** An area-weighted grid would answer *what
France's climate is*; the question here is narrower — what temperatures a
visitor to this site actually reads. Visitors search places, so the sample is
places, spread over every French climate rather than over every square
kilometre: the ocean, the north, the continental east, the mountain, the
south-west, the Mediterranean and Corsica.

**Why ERA5-Land and not the record books.** The scale has to be placed on the
numbers the site *shows*, and the site shows a reanalysis. A grid cell smooths
extremes — no French cell reaches 40 °C over these thirty years, where station
records do — so a boundary set from published records would be a boundary the
page could not reach. That gap is the reason this measurement exists rather
than a table copied from an almanac.

**1981-2010** is the WMO normal period, and the one Météo-France still
publishes as *les normales*. It is a deliberately cold reference for a site that
shows the future: a scale placed here reddens as the century advances, and that
is the point of it.
"""

from __future__ import annotations

import json
import time
from datetime import date
from pathlib import Path

from weather_simulator.sources import openmeteo
from weather_simulator.sources.client import get_json
from weather_simulator.sources.errors import FetchError

CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / "temperature_scale"
START, END = date(1981, 1, 1), date(2010, 12, 31)

# Twelve places, one per French climate rather than one per region. Coordinates
# to two decimals, as everywhere else in the project.
SITES: dict[str, tuple[float, float]] = {
    "brest": (48.39, -4.49),
    "lille": (50.63, 3.06),
    "paris": (48.86, 2.35),
    "strasbourg": (48.58, 7.75),
    "lyon": (45.76, 4.84),
    "clermont": (45.78, 3.08),
    "bordeaux": (44.84, -0.58),
    "toulouse": (43.60, 1.44),
    "marseille": (43.30, 5.37),
    "nice": (43.70, 7.27),
    "ajaccio": (41.93, 8.74),
    "briancon": (44.90, 6.63),
}


def collect() -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    for name, (latitude, longitude) in SITES.items():
        path = CACHE_DIR / f"{name}.json"
        if path.exists():
            print(f"{name:12} déjà là")
            continue
        url, params = openmeteo.archive_temperature_request(latitude, longitude, START, END)
        try:
            payload = get_json(url, params)
        except FetchError as failure:
            # A daily quota is a wall, not a hiccup: stopping leaves what is
            # already cached intact, and the next run picks up where this one
            # left off.
            print(f"{name:12} échec — {failure}")
            print("\nRelancer plus tard : les sites déjà collectés ne seront pas redemandés.")
            return
        path.write_text(json.dumps(payload))
        days = len(payload["daily"]["time"])
        print(f"{name:12} {days} journées")
        time.sleep(2)


if __name__ == "__main__":
    collect()
