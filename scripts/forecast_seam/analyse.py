"""How far apart the two sides of the forecast seam are. Reads ``data/``; no network.

    ./venv/bin/python scripts/forecast_seam/analyse.py

Two questions, in this order, because the second is only readable once the first
is settled.

**1. What does the forecast endpoint return for a past day?** Either the run that
was current at the time — a genuine short-range forecast — or a re-analysis
pasted in after the fact. If it is the latter, every figure below understates the
real seam, because it compares an analysis with an analysis. The diagnostic is
blunt and sufficient: the share of days where the two sides agree *to the digit*.
Near 100 % means the same numbers on both sides and nothing measured.

**2. How large is the step?** Bias, mean absolute deviation and worst day, per
variable, per site, then pooled. Two yardsticks are printed alongside, because a
number of this kind means nothing on its own:

- **-1.8 to +0.9 °C** — the undocumented archive seam that forcing ``models``
  exists to prevent. A step of that size is already judged unacceptable.
- **8 to 11 points of cloud** — the climate model's deficit, which on its own
  justifies the entire correction grid of step 4.

What counts as a step is a judgement for the project owner. This prints, it does
not conclude.
"""

from __future__ import annotations

import json
import statistics as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import CACHE_DIR, FIELDS, SITES  # noqa: E402

from weather_simulator.sources import openmeteo  # noqa: E402
from weather_simulator.sources.parse import parse_daily  # noqa: E402

Pairs = dict[str, list[tuple[float, float]]]  # field -> [(analysis, forecast)]


def read(site: str) -> Pairs | None:
    """Both sides of one site, aligned on the date and reduced to paired values."""
    path = CACHE_DIR / f"{site}.json"
    if not path.exists():
        return None
    raw = json.loads(path.read_text(encoding="utf-8"))

    sides = {}
    for key, model in (
        ("analysis", openmeteo.RECENT_MODEL),
        ("forecast", openmeteo.FORECAST_MODEL),
    ):
        columns = parse_daily(
            raw[key],
            openmeteo.ALL_VARIABLES,
            source=model,
            model=model,
            optional=openmeteo.OPTIONAL_VARIABLES,
        )
        sides[key] = {
            day: {field: column[i] for field, column in columns.columns.items()}
            for i, day in enumerate(columns.dates)
        }

    common = sorted(set(sides["analysis"]) & set(sides["forecast"]))
    pairs: Pairs = {field: [] for field, _, _ in FIELDS}
    for day in common:
        for field, _, _ in FIELDS:
            left, right = sides["analysis"][day][field], sides["forecast"][day][field]
            if left is not None and right is not None:
                pairs[field].append((float(left), float(right)))
    return pairs


def stats(values: list[tuple[float, float]]) -> tuple[float, float, float, float]:
    """Bias, mean absolute deviation, worst day, and share of exact agreement."""
    deltas = [right - left for left, right in values]
    identical = sum(1 for d in deltas if d == 0.0) / len(deltas) * 100
    return (
        st.mean(deltas),
        st.mean(abs(d) for d in deltas),
        max(abs(d) for d in deltas),
        identical,
    )


def main() -> int:
    collected = {site: read(site) for site in SITES}
    missing = [site for site, pairs in collected.items() if pairs is None]
    present = {site: pairs for site, pairs in collected.items() if pairs}
    if not present:
        print("aucun site collecté — lancer collect.py d'abord")
        return 1
    if missing:
        print(f"absents : {', '.join(missing)}\n")

    print("(1) Ce que renvoie l'endpoint de prévision sur une journée passée\n")
    print(f"    {'site':<15}{'jours':>7}{'valeurs identiques':>22}")
    print("    " + "-" * 44)
    for site, pairs in present.items():
        flat = [pair for values in pairs.values() for pair in values]
        _, _, _, identical = stats(flat)
        print(f"    {site:<15}{len(pairs[FIELDS[0][0]]):>7}{identical:>21.1f}%")
    print(
        "\n    Proche de 100 % : les deux côtés servent les mêmes nombres, et rien"
        "\n    n'est mesuré ci-dessous. Nettement en dessous : ce sont bien deux"
        "\n    produits distincts, et la couture est réelle."
    )

    print("\n\n(2) L'écart, par variable — mise en commun des sites\n")
    print(f"    {'variable':<18}{'biais':>10}{'écart abs.':>13}{'pire jour':>12}{'n':>8}")
    print("    " + "-" * 61)
    for field, label, unit in FIELDS:
        flat = [pair for pairs in present.values() for pair in pairs[field]]
        if not flat:
            print(f"    {label:<18}{'donnée absente':>10}")
            continue
        bias, mad, worst, _ = stats(flat)
        named = f"{label} ({unit})"
        print(f"    {named:<18}{bias:>+10.2f}{mad:>13.2f}{worst:>12.2f}{len(flat):>8}")

    print("\n\n(3) L'écart par site — pour repérer un site qui décroche\n")
    lead = [field for field, _, _ in FIELDS][:3]
    print(f"    {'site':<15}" + "".join(f"{label:>18}" for _, label, _ in FIELDS[:3]))
    print("    " + "-" * 69)
    for site, pairs in present.items():
        row = f"    {site:<15}"
        for field in lead:
            if not pairs[field]:
                row += f"{'—':>18}"
                continue
            bias, mad, _, _ = stats(pairs[field])
            row += f"{bias:>+9.2f} ±{mad:<7.2f}"
        print(row)

    print(
        "\n    Repères — la couture d'archive que le forçage de `models` évite vaut"
        "\n    -1,8 à +0,9 °C, et le déficit de nébulosité du modèle climatique, qui"
        "\n    justifie à lui seul la grille de correction, 8 à 11 points."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
