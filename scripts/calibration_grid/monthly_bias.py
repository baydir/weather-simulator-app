"""The cloud-cover bias month by month, for the two figures the site quotes.

    python scripts/calibration_grid/monthly_bias.py
    python scripts/calibration_grid/monthly_bias.py --sites Brest Perpignan

Reads ``data/calibration_grid/``; touches no network.

`docs/regles.md` gives the bias as eight to eleven points, and that is a yearly
mean per site. The documentation page says more than that — it says the gap is
seasonal and that it varies from place to place — and a claim of that shape
needs the month-by-month figures behind it, which nothing else in the pipeline
prints: `build.py` consumes the same series and emits quantile vectors, in which
a monthly mean is no longer legible.

**The gap here is not the correction.** This is a plain difference of means,
model minus reanalysis over the overlap; the correction is a quantile
transposition, and its size at a given quantile is not this number. What is
measured here is the thing the page describes to a reader — how much clearer the
model's sky is, on average, in that month at that place.

The sites are the ones the prose names, and their coordinates are the grid node
nearest the city, not the city: the table is a half-degree network, and a node
stands for the square around it.
"""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

CACHE = Path(__file__).resolve().parents[2] / "data" / "calibration_grid"

# The overlap the correction is calibrated on, and the window this measures.
# Beyond it the reanalysis stops and the difference would be model against
# nothing.
OVERLAP_END = "2014-12-31"

# The grid node nearest each city, which is what the site would interpolate
# from. Named for the city because that is how the page speaks of them.
SITES = {
    "Brest": (48.5, -4.5),
    "Lille": (50.5, 3.0),
    "Paris": (49.0, 2.5),
    "Nantes": (47.0, -1.5),
    "Bordeaux": (45.0, -0.5),
    "Lyon": (45.5, 5.0),
    "Toulouse": (43.5, 1.5),
    "Marseille": (43.5, 5.5),
    "Nice": (43.5, 7.0),
    "Perpignan": (42.5, 3.0),
    "Strasbourg": (48.5, 7.5),
    "Briançon": (45.0, 6.5),
}

MONTHS = ["janv", "févr", "mars", "avr", "mai", "juin",
          "juil", "août", "sept", "oct", "nov", "déc"]


def node_file(lat: float, lon: float) -> Path:
    """The cache file for a node, named as `collect.py` names it."""
    return CACHE / f"{lat:+06.1f}_{lon:+06.1f}.json"


def monthly_gap(path: Path) -> list[float | None]:
    """Model minus reanalysis, in points of cloud cover, for each month."""
    node = json.loads(path.read_text())
    months: dict[int, dict[str, list[float]]] = {
        month: {"reference": [], "model": []} for month in range(1, 13)
    }
    for side in ("reference", "model"):
        daily = node[side]["daily"]
        for day, cover in zip(daily["time"], daily["cloud_cover_mean"], strict=True):
            # The model runs to 2050; the reanalysis stops at the overlap, and
            # only the shared window can be differenced.
            if cover is None or day > OVERLAP_END:
                continue
            months[int(day[5:7])][side].append(cover)

    gaps: list[float | None] = []
    for month in range(1, 13):
        pair = months[month]
        if not pair["reference"] or not pair["model"]:
            gaps.append(None)
            continue
        gaps.append(statistics.fmean(pair["model"]) - statistics.fmean(pair["reference"]))
    return gaps


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sites", nargs="+", choices=sorted(SITES), default=sorted(SITES))
    chosen = parser.parse_args()

    print("Écart de nébulosité, modèle − réanalyse, en points, 1985-2014\n")
    print(f"{'':11s}" + "".join(f"{name:>6s}" for name in MONTHS) + f"{'année':>8s}")
    for site in chosen.sites:
        path = node_file(*SITES[site])
        if not path.exists():
            print(f"{site:11s} nœud non collecté ({path.name})")
            continue
        gaps = monthly_gap(path)
        measured = [gap for gap in gaps if gap is not None]
        cells = "".join(f"{gap:+6.1f}" if gap is not None else f"{'—':>6s}" for gap in gaps)
        print(f"{site:11s}{cells}{statistics.fmean(measured):+8.1f}")


if __name__ == "__main__":
    main()
