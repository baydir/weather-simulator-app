"""Look at the seams: the days either side of each changeover, and the levels.

A window spanning today meets both — the reanalyses handing over to IFS five or
six days back, then IFS handing over to the climate model tonight. Their
positions are not assumed here either: they are read off the assembled series,
wherever the source name changes from one day to the next.

Section 3 asks for two checks — no step in level, no step in variance. This
prints both, on a real request, for a point given on the command line.

    python3 scripts/inspect_seam.py --site Pontarlier --window 60

It hits the live APIs (up to four requests), so it is slow and subject to the
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
    observed = [r for r in series if r.origin is Origin.OBSERVED]
    simulated = [r for r in series if r.origin is Origin.SIMULATED]
    print(f"{len(series)} jours : {len(observed)} observés, {len(simulated)} simulés")

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

    print("\n(2) Niveaux et dispersions de part et d'autre\n")
    print(f"    {'variable':<16}{'observé':>20}{'simulé':>20}{'écart moy.':>13}")
    print("    " + "-" * 65)
    for field, label, unit in FIELDS:
        before_mean, before_sd, n_before = summarise(observed, field)
        after_mean, after_sd, n_after = summarise(simulated, field)
        if n_before == 0 or n_after == 0:
            print(f"    {label:<16}{'donnée absente':>20}")
            continue
        print(
            f"    {label + ' (' + unit + ')':<16}"
            f"{before_mean:>13.2f} ±{before_sd:<6.2f}"
            f"{after_mean:>13.2f} ±{after_sd:<6.2f}"
            f"{after_mean - before_mean:>+13.2f}"
        )

    print(
        "\n    Un écart n'est pas en soi un défaut : les deux fenêtres ne couvrent"
        "\n    pas la même saison et la seconde est une simulation. Ce qui se lit"
        "\n    ici, c'est un saut brutal — pas une différence."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
