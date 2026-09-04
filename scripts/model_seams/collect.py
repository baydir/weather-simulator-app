"""Fetch one long daily series and put it on disk, once.

Separated from ``plot.py`` for the reason every collector in this tree is:
the network is rate-limited by the day and shares its quota with the site,
while a drawing gets redrawn twenty times before it looks right. Collect once,
replay from ``data/model_seams/`` forever after.

**It runs the plan the browser runs.** ``plan.fetch_series`` is the offline path
through the very same segments, models and seam arithmetic that ``/api/plan``
hands to a visitor — down to the query string, since it fetches the plan's own
URLs rather than requests rebuilt from the same arguments. So the picture this
produces is a picture of the application, not of a second pipeline that happens
to resemble it.

**A range this long is refused by the API and not by the sources.** The 92-day
bound is ``api/validation.py``'s, a policy about what a visitor may ask for in
one search; nothing under ``sources/`` has an opinion on length. Sixteen years
costs four requests: the two reanalyses, IFS, and the climate model.

    ./venv/bin/python scripts/model_seams/collect.py
    ./venv/bin/python scripts/model_seams/collect.py --place montpellier \\
        --lat 43.61 --lon 3.88 --from 2015-01-01 --to 2030-12-31
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from weather_simulator.api import plan  # noqa: E402
from weather_simulator.sources import openmeteo  # noqa: E402
from weather_simulator.sources.series import today_in_reference_zone  # noqa: E402

OUT = ROOT / "data" / "model_seams"

# The default point, and it is the one screenshots.py photographs. Nothing about
# the seams is particular to it — they fall on the same dates anywhere — but the
# curve above them is somebody's weather, and it may as well be a reader's.
PARIS = {"place": "paris", "latitude": 48.8566, "longitude": 2.3522}


def collect(place: str, latitude: float, longitude: float, start: date, end: date) -> Path:
    today = today_in_reference_zone()
    records = plan.fetch_series(latitude, longitude, start, end, today=today)

    path = OUT / f"{place}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                # What the series is of, so a file found later can be read
                # without its command line.
                "place": place,
                "latitude": latitude,
                "longitude": longitude,
                "collected": today.isoformat(),
                # The climate model is a parameter of the application, not a
                # constant of this script — recorded so a chart drawn from an
                # old file cannot claim to show the model now in use.
                "model": openmeteo.DEFAULT_MODEL,
                # Which dataset served which variable. `source` on a record says
                # "reanalysis" for the old past, and that stands for two
                # datasets: the temperatures come from one, everything else from
                # the other. A chart of the maximum temperature has to name the
                # right one, and it should not be told which by a string typed a
                # second time in the drawing.
                "reanalysis_temperature": openmeteo.TEMPERATURE_MODEL,
                "reanalysis_surface": openmeteo.SURFACE_MODEL,
                "days": [
                    {
                        key: value.isoformat() if isinstance(value, date) else value
                        for key, value in asdict(record).items()
                    }
                    for record in records
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--place", default=PARIS["place"], help="le nom du fichier de sortie")
    parser.add_argument("--lat", type=float, default=PARIS["latitude"])
    parser.add_argument("--lon", type=float, default=PARIS["longitude"])
    parser.add_argument("--from", dest="start", type=date.fromisoformat, default=date(2015, 1, 1))
    parser.add_argument("--to", dest="end", type=date.fromisoformat, default=date(2030, 12, 31))
    chosen = parser.parse_args()

    path = collect(chosen.place, chosen.lat, chosen.lon, chosen.start, chosen.end)
    days = json.loads(path.read_text(encoding="utf-8"))["days"]
    print(f"{len(days)} jours  {days[0]['date']} → {days[-1]['date']}  →  {path}")


if __name__ == "__main__":
    main()
