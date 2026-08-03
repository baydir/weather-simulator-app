"""Which year to hold up against the future, and why it cannot be guessed.

Reads the cache filled by ``collect.py``; touches no network.

    python scripts/model_selection/reference_year.py

Section 4 of the design document envisages a button setting the requested dates
against the same dates of an older, climatically ordinary year. That year has to
be picked by measurement. The obvious candidates are not ordinary at all: 1980
was the coldest summer of its thirty at four of the five French sites, and using
it would show roughly twice the warming there actually is.

Each year is scored as its distance from the mean of its period, in standard
deviations, averaged over the French sites — a scale that lets a mild oceanic
site and a mountain one be added together. A year is ordinary when that distance
is near zero in summer, in winter and over the year at once: an annual mean can
sit dead centre while hiding a hot summer against a mild winter.

The measurement rests on the same reanalysis the application serves, ERA5-Land
for temperature, and on the sites of ``config.py``.
"""

from __future__ import annotations

import statistics as st
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import CACHE_DIR  # noqa: E402
from load import load_reference  # noqa: E402

# The five French sites. The grid of step 4 starts with France, so this is where
# a single hard-coded year would first be read — and a year ordinary in France
# is not ordinary elsewhere, which is the whole reason the document asks for one
# year per large region rather than one for the world.
FRENCH_SITES = ("brest", "marseille", "strasbourg", "pontarlier", "chamonix")

SEASONS: dict[str, set[int]] = {
    "ete": {6, 7, 8},
    "hiver": {12, 1, 2},
    "annee": set(range(1, 13)),
}

# The older the reference, the more change it shows — and the earliest years
# ERA5 serves reliably start in 1979, its preliminary back extension before that
# being of lesser quality. Thirty years is the conventional span of a normal.
EARLY = (1979, 1994)
FULL = (1979, 2008)


def _seasonal_means(
    dates: list[date],
    values: list[float | None],
    months: set[int],
    span: tuple[int, int],
) -> dict[int, float]:
    """Mean of one season per year, for the years the cache serves in full."""
    low, high = span
    gathered: dict[int, list[float]] = defaultdict(list)
    for day, value in zip(dates, values, strict=True):
        if value is not None and day.month in months and low <= day.year <= high:
            # December belongs to the winter that ends the following year. Not
            # done here: it would shift the year label by one for one season
            # only, and the button names a year the reader recognises.
            gathered[day.year].append(value)
    required = 80 if len(months) == 3 else 340
    return {year: st.mean(v) for year, v in gathered.items() if len(v) >= required}


def _scores(span: tuple[int, int]) -> dict[int, dict[str, float]]:
    """Distance from the period mean, in standard deviations, per year and season."""
    series = {site: load_reference(CACHE_DIR, site) for site in FRENCH_SITES}
    scores: dict[int, dict[str, float]] = defaultdict(dict)

    for season, months in SEASONS.items():
        standardised: dict[str, dict[int, float]] = {}
        for site, columns in series.items():
            yearly = _seasonal_means(
                columns.dates, columns.columns["temperature_max"], months, span
            )
            mean, spread = st.mean(yearly.values()), st.pstdev(yearly.values())
            standardised[site] = {
                year: (value - mean) / spread if spread else 0.0 for year, value in yearly.items()
            }
        shared = set.intersection(*(set(values) for values in standardised.values()))
        for year in shared:
            scores[year][season] = st.mean(standardised[site][year] for site in FRENCH_SITES)
    return scores


def _warming() -> float:
    """How much the French sites warmed between the first and last decade served."""
    decades = []
    for span in ((1979, 1988), (1999, 2008)):
        means = []
        for site in FRENCH_SITES:
            columns = load_reference(CACHE_DIR, site)
            yearly = _seasonal_means(
                columns.dates, columns.columns["temperature_max"], SEASONS["annee"], span
            )
            means.append(st.mean(yearly.values()))
        decades.append(st.mean(means))
    return decades[1] - decades[0]


def _report(span: tuple[int, int], label: str, highlight: tuple[int, ...] = ()) -> None:
    scores = _scores(span)
    if not scores:
        print(f"  {label}: nothing in the cache")
        return

    def worst(year: int) -> float:
        return max(abs(value) for value in scores[year].values())

    print(f"\n  {label}")
    print(f"    {'annee':<8}" + "".join(f"{season:>10}" for season in SEASONS) + f"{'ecart':>9}")
    for year in sorted(scores, key=worst)[:5]:
        row = "".join(f"{scores[year][season]:>+10.2f}" for season in SEASONS)
        print(f"    {year:<8}{row}{worst(year):>9.2f}")
    for year in highlight:
        if year in scores:
            row = "".join(f"{scores[year][season]:>+10.2f}" for season in SEASONS)
            print(f"    {year:<8}{row}{worst(year):>9.2f}   <-")


def main() -> int:
    if not CACHE_DIR.exists():
        print(f"no cache at {CACHE_DIR}; run collect.py first")
        return 1

    print("REFERENCE YEAR — distance from the period mean, in standard deviations,")
    print(f"averaged over {len(FRENCH_SITES)} French sites. Zero is a perfectly ordinary year.")

    _report(EARLY, f"periode ancienne {EARLY[0]}-{EARLY[1]}")
    _report(FULL, f"{FULL[0]}-{FULL[1]}", highlight=(1980, 2003))

    print(f"\n  Rechauffement entre 1979-1988 et 1999-2008 : {_warming():+.2f} C")
    print("  — ce qu'une annee de reference tardive depense avant de commencer.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
