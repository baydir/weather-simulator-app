"""Look at the seams: the days either side of each changeover, and the levels.

A window spanning today meets both — the reanalyses handing over to IFS five or
six days back, then IFS handing over to the climate model a fortnight ahead.
Their positions are not assumed here either: they are read off the assembled
series, wherever the source name changes from one day to the next.

Note what is *not* a seam: tonight. IFS runs straight through it, on the archive
side until today and on the forecast side after, so the changeover the reader
would most easily catch out is the one place the series does not break.

Section 3 asks for two checks — no step in level, no step in variance. This
prints both, on a real request, for a point given on the command line.

    python3 scripts/inspect_seam.py --site Pontarlier --window 60

It hits the live APIs (up to five requests), so it is slow and subject to the
rate limit. It is a reading tool, not a test: what counts as a step is a
judgement for the project owner to make.
"""

from __future__ import annotations

import argparse
import statistics as st
import sys
from datetime import timedelta

sys.path.insert(0, "src")

from weather_simulator.domain.records import Origin  # noqa: E402
from weather_simulator.sources import openmeteo  # noqa: E402
from weather_simulator.sources.series import fetch_series, today_in_reference_zone  # noqa: E402

SITES = {
    "Pontarlier": (46.90, 6.35),
    "Brest": (48.39, -4.49),
    "Marseille": (43.30, 5.37),
    "Reykjavik": (64.15, -21.94),
    "Bamako": (12.65, -8.00),
    "Singapour": (1.35, 103.82),
}

FIELDS = [
    ("temperature_min", "Tmin", "°C"),
    ("temperature_max", "Tmax", "°C"),
    ("precipitation", "précip", "mm"),
    ("snowfall", "neige", "cm"),
    ("cloud_cover", "nébul", "%"),
    ("wind_speed_max", "vent", "km/h"),
]


def summarise(records, field):
    values = [getattr(r, field) for r in records if getattr(r, field) is not None]
    if not values:
        return None, None, 0
    spread = st.pstdev(values) if len(values) > 1 else 0.0
    return st.mean(values), spread, len(values)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", default="Pontarlier", choices=sorted(SITES))
    parser.add_argument("--window", type=int, default=60, help="jours de part et d'autre")
    parser.add_argument("--show", type=int, default=5, help="jours affichés autour de la couture")
    parser.add_argument(
        "--model", default=openmeteo.DEFAULT_MODEL, choices=openmeteo.ELIGIBLE_MODELS
    )
    parser.add_argument("--timezone", default=openmeteo.DEFAULT_TIMEZONE)
    args = parser.parse_args()

    latitude, longitude = SITES[args.site]
    today = today_in_reference_zone()
    start = today - timedelta(days=args.window)
    end = today + timedelta(days=args.window - 1)

    print(f"{args.site}  ({latitude}, {longitude})  modèle {args.model}  tz {args.timezone}")
    print(f"fenêtre de {args.window} jours de part et d'autre du {today}\n")

    series = fetch_series(
        latitude, longitude, start, end, model=args.model, timezone=args.timezone, today=today
    )
    groups = {origin: [r for r in series if r.origin is origin] for origin in Origin}
    print(
        f"{len(series)} jours : "
        + ", ".join(
            f"{len(records)} {label}"
            for records, label in (
                (groups[Origin.OBSERVED], "observés"),
                (groups[Origin.FORECAST], "prévus"),
                (groups[Origin.SIMULATED], "simulés"),
            )
        )
    )

    # Wherever the source name changes from one day to the next, there is a seam.
    seams = [
        (b.date, a.source, b.source)
        for a, b in zip(series, series[1:], strict=False)
        if a.source != b.source
    ]
    for day, before, after in seams:
        print(f"    couture au {day} : {before} → {after}")

    print("\n(1) Jours autour de chaque couture\n")
    header = f"    {'date':<12}{'origine':<11}{'source':<15}" + "".join(
        f"{label:>9}" for _, label, _ in FIELDS
    )
    print(header)
    print("    " + "-" * (len(header) - 4))
    shown = set()
    for index, record in enumerate(series):
        near = any(abs((record.date - day).days) <= args.show for day, _, _ in seams)
        if not near:
            continue
        if shown and index - max(shown) > 1:
            print("    " + "·" * 12)
        shown.add(index)
        marker = "→ " if any(record.date == day for day, _, _ in seams) else "  "
        row = f"  {marker}{record.date.isoformat():<12}{record.origin.value:<11}{record.source:<15}"
        for field, _, _ in FIELDS:
            value = getattr(record, field)
            row += f"{'—':>9}" if value is None else f"{value:>9.1f}"
        print(row)

    print("\n(2) Niveaux et dispersions par origine\n")
    print(f"    {'variable':<16}{'observé':>20}{'prévu':>20}{'simulé':>20}")
    print("    " + "-" * 76)
    for field, label, unit in FIELDS:
        cells = ""
        for origin in (Origin.OBSERVED, Origin.FORECAST, Origin.SIMULATED):
            mean, spread, count = summarise(groups[origin], field)
            cells += f"{'—':>20}" if count == 0 else f"{mean:>13.2f} ±{spread:<6.2f}"
        print(f"    {label + ' (' + unit + ')':<16}{cells}")

    print(
        "\n    Un écart n'est pas en soi un défaut : les trois fenêtres ne couvrent"
        "\n    pas la même saison, ni la même durée, et la dernière est une"
        "\n    simulation. Ce qui se lit ici, c'est un saut brutal — pas une"
        "\n    différence. La colonne « prévu » est courte par construction : une"
        "\n    quinzaine contre deux fenêtres de la largeur demandée."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
