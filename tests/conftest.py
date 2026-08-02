"""A stand-in for Open-Meteo, faithful to the shapes and the gaps it answers with."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from weather_simulator.sources import openmeteo

# What the reanalyses run behind. Not a constant in the code under test: the
# whole point is that the seam is read from the data rather than assumed, so the
# tests move this around.
DEFAULT_LAG = 6

LAGGING_MODELS = {openmeteo.TEMPERATURE_MODEL, openmeteo.SURFACE_MODEL}


def days(start: date, end: date) -> list[str]:
    span = (end - start).days + 1
    return [(start + timedelta(days=offset)).isoformat() for offset in range(span)]


def payload(
    params: dict[str, Any],
    *,
    suffixed: bool = False,
    null_variables: tuple[str, ...] = (),
    served_until: date | None = None,
    value: float = 1.0,
) -> dict[str, Any]:
    """Build the payload Open-Meteo would return for ``params``.

    ``suffixed`` reproduces the key spelling used when several models are asked
    for at once; ``null_variables`` reproduces a variable a source never serves;
    ``served_until`` reproduces the latency, days beyond it coming back null.
    """
    start = date.fromisoformat(params["start_date"])
    end = date.fromisoformat(params["end_date"])
    time = days(start, end)
    model = params["models"][0]

    daily: dict[str, Any] = {"time": time}
    for index, variable in enumerate(params["daily"]):
        key = f"{variable}_{model}" if suffixed else variable
        if variable in null_variables:
            daily[key] = [None] * len(time)
        else:
            daily[key] = [
                None if served_until and date.fromisoformat(day) > served_until else value + index
                for day in time
            ]
    return {"latitude": 46.9, "longitude": 6.35, "elevation": 831.0, "daily": daily}


def fake_openmeteo(
    *,
    today: date | None = None,
    lag: int = DEFAULT_LAG,
    null_variables: tuple[str, ...] = (),
) -> tuple[Any, list[tuple[str, dict[str, Any]]]]:
    """A fetcher recording every call, alongside the list of those calls.

    Only the reanalyses lag: IFS and the climate model answer in full.
    """
    calls: list[tuple[str, dict[str, Any]]] = []
    horizon = today - timedelta(days=lag) if today else None

    def fetch(url: str, params: dict[str, Any]) -> dict[str, Any]:
        calls.append((url, params))
        model = params["models"][0]
        return payload(
            params,
            null_variables=null_variables,
            served_until=horizon if model in LAGGING_MODELS else None,
        )

    return fetch, calls
