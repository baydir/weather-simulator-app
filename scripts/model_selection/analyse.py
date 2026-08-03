"""Set the five hindcasts against the reference, and lay out what separates them.

Reads the cache filled by ``collect.py``; touches no network.

    python scripts/model_selection/analyse.py

The script ranks, it does not choose. Averaging ranks compresses fifteen
measures at ten sites into one number, and that compression hides as much as it
shows — a model may lead on average while failing outright somewhere the
application will actually be used. The tables are printed in full for that
reason, and the choice of model belongs to the scientific-validation regime of
section 1 of the design document.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import CACHE_DIR, END, SITES, START  # noqa: E402
from load import coverage, load_model, load_reference  # noqa: E402
from measures import DISPERSION, MEASURES, SHAPE, Measure  # noqa: E402

from weather_simulator.sources import openmeteo  # noqa: E402
from weather_simulator.sources.errors import FetchError, MissingVariableError  # noqa: E402

MODELS = openmeteo.ELIGIBLE_MODELS
Table = dict[tuple[str, str, str], float | None]  # (site, source, measure) -> value
Coverage = dict[tuple[str, str, str], float]  # (site, source, field) -> percent served


def gather() -> tuple[Table, Coverage, list[str]]:
    """Compute every measure for the reference and the five models, at every site."""
    values: Table = {}
    served: Coverage = {}
    missing: list[str] = []

    for site in SITES:
        series = {}
        try:
            series["reference"] = load_reference(CACHE_DIR, site)
        except (FileNotFoundError, FetchError, MissingVariableError) as error:
            missing.append(f"{site}/reference: {error}")
            continue
        for model in MODELS:
            try:
                series[model] = load_model(CACHE_DIR, site, model)
            except (FileNotFoundError, FetchError, MissingVariableError) as error:
                missing.append(f"{site}/{model}: {error}")

        for source, columns in series.items():
            for measure in MEASURES:
                values[(site, source, measure.key)] = measure.compute(columns.dates, columns)
            for field, share in coverage(columns).items():
                served[(site, source, field)] = share

    return values, served, missing


def print_coverage(served: Coverage, sites: list[str]) -> None:
    """Which variables each model actually serves, worst site first.

    Reported before anything else, because a variable a model never serves is
    not a shade of quality: it decides on its own whether the model can carry
    the application at all.
    """
    fields = sorted({field for (_, _, field) in served})
    print(
        f"\n  {'model':<16}" + "".join(f"{f.replace('temperature_', 'T')[:11]:>13}" for f in fields)
    )
    for model in MODELS:
        row = f"  {model:<16}"
        for field in fields:
            shares = [served[(s, model, field)] for s in sites if (s, model, field) in served]
            row += f"{min(shares):>12.0f}%" if shares else f"{'--':>13}"
        print(row)
    print("\n  Lowest share across sites. 0% is a variable the model never serves.")


def print_measure(values: Table, measure: Measure, sites: list[str]) -> None:
    """One table per measure: the reference, then what each model makes of it."""
    print(f"\n  {measure.label}" + (f" ({measure.unit})" if measure.unit else ""))
    print(f"    {'site':<14}{'reference':>11}" + "".join(f"{m[:11]:>13}" for m in MODELS))

    for site in sites:
        reference = values.get((site, "reference", measure.key))
        row = f"    {site:<14}" + (
            f"{reference:>11.2f}" if reference is not None else f"{'--':>11}"
        )
        for model in MODELS:
            value = values.get((site, model, measure.key))
            if value is None or reference is None:
                row += f"{'--':>13}"
            elif measure.kind == "ratio":
                # Shown as the ratio to the reference: 1.00 is agreement, and
                # the eye catches a 0.61 or a 1.41 faster than two columns of
                # absolute values.
                row += f"{value / reference if reference else float('nan'):>13.2f}"
            else:
                row += f"{value - reference:>+13.2f}"
        print(row)


def rank(values: Table, sites: list[str]) -> dict[str, dict[str, float]]:
    """Average rank of each model, per family of measures and overall.

    Ranked site by site and measure by measure, then averaged: a rank cannot be
    dragged by one site where every model is far out, which an average of raw
    deviations would be. Ties share the mean of the ranks they span.
    """
    scores: dict[str, dict[str, list[float]]] = {
        model: {DISPERSION: [], SHAPE: []} for model in MODELS
    }

    for site in sites:
        for measure in MEASURES:
            reference = values.get((site, "reference", measure.key))
            deviations = {
                model: measure.deviation(values.get((site, model, measure.key)), reference)
                for model in MODELS
            }
            scored = {m: d for m, d in deviations.items() if d is not None}
            if len(scored) < 2:
                continue
            ordered = sorted(scored.items(), key=lambda item: item[1])
            for model, deviation in ordered:
                tied = [p for p, (_, d) in enumerate(ordered, start=1) if d == deviation]
                scores[model][measure.family].append(sum(tied) / len(tied))

    summary: dict[str, dict[str, float]] = {}
    for model, families in scores.items():
        pooled = families[DISPERSION] + families[SHAPE]
        summary[model] = {
            DISPERSION: sum(families[DISPERSION]) / len(families[DISPERSION])
            if families[DISPERSION]
            else float("nan"),
            SHAPE: sum(families[SHAPE]) / len(families[SHAPE]) if families[SHAPE] else float("nan"),
            "total": sum(pooled) / len(pooled) if pooled else float("nan"),
            "n": float(len(pooled)),
        }
    return summary


def main() -> int:
    if not CACHE_DIR.exists():
        print(f"no cache at {CACHE_DIR}; run collect.py first")
        return 1

    values, served, missing = gather()
    sites = [site for site in SITES if (site, "reference", MEASURES[0].key) in values]

    # Ranked only where all five answered. A site where two models are absent
    # would hand the three present a rank of 1, 2 and 3 whatever they are
    # worth, and a collection stopped by the rate limit would quietly decide
    # the comparison.
    ranked = [
        site for site in sites if all((site, model, MEASURES[0].key) in values for model in MODELS)
    ]

    print(f"MODEL SELECTION — hindcast vs reanalysis, {START}..{END}")
    print(f"{len(sites)} sites, {len(MODELS)} models, {len(MEASURES)} measures")
    print("\nRatios are model/reference (1.00 = agreement); differences are model-reference.")
    print("Means are not compared: Open-Meteo's monthly linear correction sets them.")

    print(f"\n\n{'=' * 78}\nCOUVERTURE\n{'=' * 78}")
    print_coverage(served, sites)

    for family in (DISPERSION, SHAPE):
        print(f"\n\n{'=' * 78}\n{family.upper()}\n{'=' * 78}")
        for measure in MEASURES:
            if measure.family == family:
                print_measure(values, measure, sites)

    title = "AVERAGE RANK — 1 is closest to the reference, 5 the furthest"
    print(f"\n\n{'=' * 78}\n{title}\n{'=' * 78}")
    print(f"\n  Over the {len(ranked)} sites where all five models answered:")
    print(f"  {', '.join(ranked)}\n")
    summary = rank(values, ranked)
    print(f"  {'model':<16}{'dispersion':>13}{'forme':>10}{'ensemble':>11}{'n':>7}")
    for model, row in sorted(summary.items(), key=lambda item: item[1]["total"]):
        print(
            f"  {model:<16}{row[DISPERSION]:>13.2f}{row[SHAPE]:>10.2f}"
            f"{row['total']:>11.2f}{int(row['n']):>7}"
        )

    if missing:
        print(f"\n{len(missing)} series unavailable:")
        for entry in missing:
            print(f"  {entry}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
