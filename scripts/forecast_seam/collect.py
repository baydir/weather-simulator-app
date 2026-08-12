"""Fetch both sides of the forecast seam, at every site. **Only this touches the network.**

    ./venv/bin/python scripts/forecast_seam/collect.py

Two requests per site, over the same days: the archive's IFS analysis, and the
forecast endpoint's IFS run. The days overlap on purpose — the seam is not read
by looking at what lies either side of a boundary, but by asking both sources
about the *same* day and seeing whether they answer the same thing.

Requests are built by ``weather_simulator.sources.openmeteo``, never here.
Rebuilding them would open the door to two behaviours drifting apart, which is
the failure the whole project is arranged against.

Resumable: a site already on disk is skipped. The daily quota is shared with the
grid collection of step 4 and with the site itself, so this is written to be run
again rather than to succeed in one go.
"""

from __future__ import annotations

import json
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import CACHE_DIR, PAST_DAYS, SITES  # noqa: E402

from weather_simulator.sources import openmeteo  # noqa: E402
from weather_simulator.sources.client import get_json  # noqa: E402
from weather_simulator.sources.errors import FetchError  # noqa: E402


def window(today: date) -> tuple[date, date]:
    """The days both endpoints can answer for.

    Stops at yesterday. Today is still running, so its aggregate is partly a
    forecast on *both* sides — including the archive's — and comparing the two
    there would measure the hour of the day rather than the seam.
    """
    return today - timedelta(days=PAST_DAYS), today - timedelta(days=1)


def collect(site: str, latitude: float, longitude: float, first: date, last: date) -> str:
    target = CACHE_DIR / f"{site}.json"
    if target.exists():
        return "cached"

    url, params = openmeteo.archive_recent_request(latitude, longitude, first, last)
    analysis = get_json(url, params)

    url, params = openmeteo.forecast_request(latitude, longitude, first, last)
    forecast = get_json(url, params)

    target.write_text(
        json.dumps(
            {
                "site": site,
                "latitude": latitude,
                "longitude": longitude,
                "first": first.isoformat(),
                "last": last.isoformat(),
                "analysis": analysis,
                "forecast": forecast,
            }
        ),
        encoding="utf-8",
    )
    return "fetched"


def main() -> int:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    first, last = window(date.today())
    print(f"fenêtre : {first} → {last}  ({PAST_DAYS} jours)")
    print(f"cache : {CACHE_DIR}\n")

    failed = 0
    for site, (latitude, longitude) in SITES.items():
        try:
            outcome = collect(site, latitude, longitude, first, last)
        except FetchError as error:
            failed += 1
            print(f"  ! {site}: {error}", flush=True)
            continue
        print(f"  {site:<14} {outcome}", flush=True)

    if failed:
        print(f"\n{failed} site(s) en échec — relancer pour reprendre les manquants")
        return 1
    print("\ncollecte complète")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
