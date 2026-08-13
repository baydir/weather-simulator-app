"""Where the six colours should cut, read off what France actually recorded.

    ./venv/bin/python scripts/temperature_scale/scale.py

No network: it reads what ``collect.py`` cached. Twelve sites, 1981-2010,
ERA5-Land — 131 484 site-days of daily maximum and minimum.

The scale is absolute: one colour per temperature, the same all year, as the
public weather maps do. So the only question a measurement can answer is
**what each candidate boundary set captures** — how much of the French record
falls in each colour, and whether any colour goes unused. Where "very cold"
ends and "cold" begins stays a convention of language, exactly as it does for
the sky classes; measurement says what falls either side of the line, not where
to draw it.

Two things this reports that are easy to get wrong by intuition:

**The minimum and the maximum are not on the same part of the scale.** A shared
scale is what makes the two numbers on a card comparable, and it is also what
sends the minimum permanently into the cold half — a French night above 20 °C is
rare. That is a fact about nights, not a fault in the scale, but it has to be
seen before it is chosen.

**Nothing here reaches 40 °C.** A reanalysis grid cell smooths extremes, and
this is the source the site shows. A top boundary taken from station records
would be a colour the page could not display.
"""

from __future__ import annotations

import json
from pathlib import Path

CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / "temperature_scale"

# The colours, from cold to hot. Five boundaries make six bands; a value equal
# to a boundary falls in the warmer of the two, as the sky thresholds do.
COLOURS = ["bleu", "vert", "jaune", "orange", "rouge", "violet"]

CANDIDATES: dict[str, list[float]] = {
    "ronds larges": [0, 10, 20, 30, 35],
    "ronds décalés": [-5, 5, 15, 25, 35],
    "cinq degrés": [0, 5, 15, 25, 32],
    "resserré chaud": [0, 10, 20, 28, 34],
}


def read() -> dict[str, dict[str, list[float]]]:
    series: dict[str, dict[str, list[float]]] = {}
    for path in sorted(CACHE_DIR.glob("*.json")):
        daily = json.load(path.open())["daily"]
        series[path.stem] = {
            "max": [v for v in daily["temperature_2m_max"] if v is not None],
            "min": [v for v in daily["temperature_2m_min"] if v is not None],
        }
    return series


def quantile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(fraction * len(ordered)))]


def band(value: float, cuts: list[float]) -> int:
    for index, cut in enumerate(cuts):
        if value < cut:
            return index
    return len(cuts)


def shares(values: list[float], cuts: list[float]) -> list[float]:
    counts = [0] * (len(cuts) + 1)
    for value in values:
        counts[band(value, cuts)] += 1
    return [100 * count / len(values) for count in counts]


def main() -> None:
    series = read()
    if not series:
        raise SystemExit("rien dans data/temperature_scale/ — lancer collect.py d'abord")

    highs = [v for site in series.values() for v in site["max"]]
    lows = [v for site in series.values() for v in site["min"]]

    print(f"\n{len(series)} sites, {len(highs)} journées\n")
    print("Par site — maximale et minimale, degrés")
    print(f"{'':12} {'min':>7} {'p1':>7} {'p25':>7} {'p50':>7} {'p75':>7} {'p99':>7} {'max':>7}")
    for name, site in series.items():
        for field, label in (("max", "maximale"), ("min", "minimale")):
            values = site[field]
            row = [
                min(values),
                quantile(values, 0.01),
                quantile(values, 0.25),
                quantile(values, 0.50),
                quantile(values, 0.75),
                quantile(values, 0.99),
                max(values),
            ]
            head = f"{name:12}" if field == "max" else " " * 12
            print(head + "".join(f"{v:7.1f}" for v in row) + f"  {label}")

    print("\nToute la France ensemble")
    for values, label in ((highs, "maximale"), (lows, "minimale"), (highs + lows, "les deux")):
        row = [
            min(values),
            quantile(values, 0.01),
            quantile(values, 0.25),
            quantile(values, 0.50),
            quantile(values, 0.75),
            quantile(values, 0.99),
            max(values),
        ]
        print(f"{label:12}" + "".join(f"{v:7.1f}" for v in row))

    print("\nCe que chaque découpage capture — % des journées")
    for name, cuts in CANDIDATES.items():
        print(f"\n  {name} : {cuts}")
        print(f"{'':14}" + "".join(f"{colour:>9}" for colour in COLOURS))
        for values, label in ((highs, "maximale"), (lows, "minimale")):
            print(f"    {label:10}" + "".join(f"{part:8.1f} " for part in shares(values, cuts)))

    print("\nLes journées les plus chaudes de la période, toutes villes")
    hottest = sorted(highs)[-5:]
    print("  " + "  ".join(f"{v:.1f}" for v in hottest))


if __name__ == "__main__":
    main()
