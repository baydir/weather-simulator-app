"""Turn the collected series into the shipped correction table.

    python scripts/calibration_grid/build.py              # depuis le cache
    python scripts/calibration_grid/build.py --neutral    # table provisoire

Reads ``data/calibration_grid/``; touches no network.

The neutral mode exists because the collection is measured in hours of quota
and the rest of the pipeline should not wait for it. It emits a table covering
the whole French box whose corrections return their input untouched — the three
quantile vectors being identical, quantile delta mapping is the identity.

**That table must never be served.** An uncorrected future is an artificially
sunny future, which is precisely the failure docs/regles.md exists to prevent: the
model is short of the reanalysis by eight to eleven points of cloud, and three
of the five sky classes turn on that variable. So the flag rides along in the
metadata, the file carries a different name, and the loader is expected to check
``is_placeholder`` before letting anything through to a visitor.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from collect import (  # noqa: E402
    CACHE_DIR,
    CALIBRATION_END,
    CALIBRATION_START,
    PROBE_FILE,
    VARIABLE,
)
from nodes import Node, bounding_nodes, worth_collecting  # noqa: E402

from weather_simulator.calibration.table import CorrectionTable, Metadata  # noqa: E402
from weather_simulator.domain.correction import (  # noqa: E402
    LEVELS,
    CloudCorrection,
    MonthlyCorrection,
    build,
)
from weather_simulator.sources import openmeteo  # noqa: E402

OUTPUT_DIR = (
    Path(__file__).resolve().parents[2] / "src" / "weather_simulator" / "calibration" / "data"
)
PROJECTION_START, PROJECTION_END = date(2021, 1, 1), date(2050, 12, 31)


def _by_month(payload: dict, first: date, last: date) -> dict[int, list[float]]:
    """Daily values grouped by calendar month, over a period."""
    daily = payload["daily"]
    key = next((k for k in daily if k != "time" and k.startswith(VARIABLE)), VARIABLE)
    grouped: dict[int, list[float]] = defaultdict(list)
    for stamp, value in zip(daily["time"], daily[key], strict=True):
        if value is None:
            continue
        day = date.fromisoformat(stamp)
        if first <= day <= last:
            grouped[day.month].append(float(value))
    return grouped


def from_cache() -> CorrectionTable:
    """Build the table from whatever nodes have been collected so far."""
    nodes: dict[tuple[float, float], CloudCorrection] = {}
    thin: list[str] = []

    for path in sorted(CACHE_DIR.glob("*.json")):
        if path.name == "elevations.json":
            continue
        raw = json.loads(path.read_text(encoding="utf-8"))
        latitude = float(raw["reference"]["latitude"])
        longitude = float(raw["reference"]["longitude"])

        reference = _by_month(raw["reference"], CALIBRATION_START, CALIBRATION_END)
        past = _by_month(raw["model"], CALIBRATION_START, CALIBRATION_END)
        future = _by_month(raw["model"], PROJECTION_START, PROJECTION_END)

        correction = build(reference, past, future)
        if len(correction.months) < 12:
            thin.append(f"{latitude:.1f},{longitude:.1f} ({len(correction.months)} mois)")
        # Snapped to the lattice: Open-Meteo answers with the cell centre, which
        # is not the coordinate that was asked for.
        key = (round(latitude * 2) / 2, round(longitude * 2) / 2)
        nodes[key] = correction

    if thin:
        print(f"  {len(thin)} noeuds incomplets : {', '.join(thin[:5])}")

    return CorrectionTable(
        metadata=Metadata(
            model=openmeteo.DEFAULT_MODEL,
            calibration_start=CALIBRATION_START,
            calibration_end=CALIBRATION_END,
            projection_start=PROJECTION_START,
            projection_end=PROJECTION_END,
            step=0.5,
            generated=date.today(),
            node_count=len(nodes),
        ),
        nodes=nodes,
    )


def neutral() -> CorrectionTable:
    """A table over the whole box whose correction changes nothing.

    The three vectors are identical, so the mapping is the identity at every
    quantile. Built from the elevation probe alone, which is already complete,
    so it covers every node the real table will ever hold.
    """
    identity = [round(100 * level, 1) for level in LEVELS]
    months = {
        month: MonthlyCorrection(
            reference=list(identity),
            model_past=list(identity),
            model_future=list(identity),
        )
        for month in range(1, 13)
    }

    known = json.loads(PROBE_FILE.read_text(encoding="utf-8"))
    elevations = {node: known[node.key] for node in bounding_nodes() if node.key in known}
    wanted: list[Node] = worth_collecting(elevations) if elevations else bounding_nodes()

    return CorrectionTable(
        metadata=Metadata(
            model=openmeteo.DEFAULT_MODEL,
            calibration_start=CALIBRATION_START,
            calibration_end=CALIBRATION_END,
            projection_start=PROJECTION_START,
            projection_end=PROJECTION_END,
            step=0.5,
            generated=date.today(),
            node_count=len(wanted),
            placeholder=True,
            note=(
                "Table provisoire : correction identite. Sert a faire tourner la "
                "chaine pendant la collecte. Ne jamais servir a un visiteur — le "
                "futur y serait artificiellement ensoleille de 8 a 11 points de "
                "nebulosite."
            ),
        ),
        nodes={(node.latitude, node.longitude): CloudCorrection(dict(months)) for node in wanted},
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--neutral", action="store_true", help="table identite, provisoire")
    args = parser.parse_args(argv)

    table = neutral() if args.neutral else from_cache()
    name = "cloud_correction_placeholder.json" if args.neutral else "cloud_correction.json"
    target = OUTPUT_DIR / name
    table.write(target)

    size = target.stat().st_size / 1024
    print(f"\n{len(table.nodes)} noeuds ecrits dans {target.relative_to(Path.cwd())}")
    print(
        f"{size:.0f} Ko, modele {table.metadata.model}, "
        f"calibration {table.metadata.calibration_start}..{table.metadata.calibration_end}"
    )
    if table.metadata.placeholder:
        print("\n  ATTENTION — table provisoire, correction identite.")
        print("  " + table.metadata.note)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
