"""Fetch the cloud-cover series the correction grid is built from.

    python scripts/calibration_grid/collect.py

Two passes. The first probes one day at every node in the French box to read its
elevation, which separates land from open sea for the price of a negligible
request. The second fetches the full series only for the nodes that survived —
land, plus the ring of sea touching it.

Resumable, and it has to be: the rate limit closes the door well before the
collection ends, and a run is measured in hours of quota rather than minutes of
network. Everything already on disk is skipped, so the command is simply run
again until it says it is done.

Two requests per node. The reanalysis over the calibration period, and the model
over 1985-2050 in one go — that single request carries both the model's past,
which makes it comparable to the reference, and its future, which carries the
trend the correction must not flatten.

Thirty calibration years, not ten: script 16 of the verification set found that
ten produce an error of the same order as the correction itself.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import date
from functools import partial
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from nodes import Node, bounding_nodes, worth_collecting  # noqa: E402
from priority import in_priority_order  # noqa: E402

from weather_simulator.sources import openmeteo  # noqa: E402
from weather_simulator.sources.client import get_json  # noqa: E402
from weather_simulator.sources.errors import FetchError  # noqa: E402

CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / "calibration_grid"
PROBE_FILE = CACHE_DIR / "elevations.json"

CALIBRATION_START, CALIBRATION_END = date(1985, 1, 1), date(2014, 12, 31)
MODEL_START, MODEL_END = date(1985, 1, 1), date(2050, 12, 31)

VARIABLE = "cloud_cover_mean"

# The archive answers in about six seconds for thirty years, the climate API in
# under one. The pause is what keeps a long run from tripping the per-minute
# limit; the client handles the hourly one by waiting it out.
PAUSE = 2

# How long to wait after a refusal, in seconds. Not a constant, because the
# right value is not deducible: Open-Meteo publishes limits that would imply
# four nodes a day, two hundred times below what the collection actually
# achieves, and exposes no quota header. Nodes arrive in bursts separated by
# exactly this delay, which suggests the budget refills continuously and that
# waiting less would catch it sooner. Measured rather than assumed —
# ``--backoff`` exists so the measurement can be repeated.
DEFAULT_BACKOFF = 300


def _fetcher(backoff: int):
    # Ten attempts, not five. The client grows its wait linearly, so this gives
    # a node up to three quarters of an hour to get through before it is given
    # up on — which suits an unattended run better than failing fast. A refused
    # request comes back in under a second and does not appear to be charged,
    # so asking often costs nothing.
    return partial(get_json, retries=10, backoff=backoff)


fetch = _fetcher(DEFAULT_BACKOFF)


def _probe(node: Node) -> float:
    """One day, one variable, for the elevation the payload carries anyway."""
    url, params = openmeteo.archive_surface_request(
        node.latitude, node.longitude, date(2020, 1, 1), date(2020, 1, 1)
    )
    params["daily"] = [VARIABLE]
    return float(fetch(url, params).get("elevation", 0.0))


def probe_elevations() -> dict[Node, float]:
    """Read every node's elevation, cached as a whole."""
    known: dict[str, float] = {}
    if PROBE_FILE.exists():
        known = json.loads(PROBE_FILE.read_text(encoding="utf-8"))

    nodes = bounding_nodes()
    pending = [n for n in nodes if n.key not in known]
    if pending:
        print(f"sonde d'altitude : {len(pending)} noeuds restants sur {len(nodes)}")
        for index, node in enumerate(pending, start=1):
            try:
                known[node.key] = _probe(node)
            except FetchError as error:
                print(f"  ! {node.key}: {error}")
                break
            if index % 25 == 0:
                PROBE_FILE.write_text(json.dumps(known), encoding="utf-8")
                print(f"  {index}/{len(pending)}", flush=True)
            time.sleep(1)
        PROBE_FILE.write_text(json.dumps(known), encoding="utf-8")

    return {node: known[node.key] for node in nodes if node.key in known}


def _collect(node: Node) -> str:
    target = CACHE_DIR / f"{node.key}.json"
    if target.exists():
        return "cached"

    url, params = openmeteo.archive_surface_request(
        node.latitude, node.longitude, CALIBRATION_START, CALIBRATION_END
    )
    params["daily"] = [VARIABLE]
    reference = fetch(url, params)
    time.sleep(PAUSE)

    url, params = openmeteo.climate_request(node.latitude, node.longitude, MODEL_START, MODEL_END)
    params["daily"] = [VARIABLE]
    model = fetch(url, params)
    time.sleep(PAUSE)

    target.write_text(json.dumps({"reference": reference, "model": model}), encoding="utf-8")
    return "fetched"


def main(argv: list[str] | None = None) -> int:
    global fetch
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--backoff",
        type=int,
        default=DEFAULT_BACKOFF,
        help="secondes d'attente apres un refus (defaut 300)",
    )
    parser.add_argument(
        "--limit", type=int, default=None, help="s'arreter apres N noeuds, pour mesurer un debit"
    )
    args = parser.parse_args(argv)
    fetch = _fetcher(args.backoff)

    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    elevations = probe_elevations()
    total = len(bounding_nodes())
    if len(elevations) < total:
        print(f"\nsonde incomplete ({len(elevations)}/{total}) — relancer")
        return 1

    # Ordered by the population each node serves, not by latitude. The rate
    # limit makes the collection a matter of days, so what is fetched first
    # decides what the application can answer meanwhile.
    wanted = in_priority_order(worth_collecting(elevations))
    land = sum(1 for value in elevations.values() if value > 0)
    print(f"\n{total} noeuds dans la boite, {land} terrestres, {len(wanted)} a collecter")
    print(f"cache : {CACHE_DIR}\n")

    print(f"palier de reprise : {args.backoff} s\n")
    done = failed = 0
    for index, node in enumerate(wanted, start=1):
        if args.limit and done >= args.limit:
            break
        try:
            outcome = _collect(node)
        except FetchError as error:
            failed += 1
            print(f"  ! {node.key}: {error}", flush=True)
            continue
        if outcome == "fetched":
            done += 1
        if index % 20 == 0:
            served = sum(1 for n in wanted if (CACHE_DIR / f"{n.key}.json").exists())
            print(f"  {served}/{len(wanted)} noeuds servis", flush=True)

    served = sum(1 for n in wanted if (CACHE_DIR / f"{n.key}.json").exists())
    print(f"\n{served}/{len(wanted)} noeuds servis ({done} cette fois, {failed} echecs)")
    if served < len(wanted):
        print("relancer pour reprendre les manquants")
        return 1
    print("collecte complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
