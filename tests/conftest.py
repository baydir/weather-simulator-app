"""A stand-in for Open-Meteo, faithful to the shapes and the gaps it answers with."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any
from urllib.parse import parse_qs, urlsplit

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
    models = params["models"]
    model = models[0] if models else ""

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


def asked(url: str) -> dict[str, Any]:
    """Read a planned URL back into the parameters it carries.

    The plan spells its requests out as finished URLs, because that is what the
    browser is handed and all it can do anything with. A stand-in therefore
    parses one, exactly as Open-Meteo would — and a test that wants to know what
    was asked for reads it here rather than being passed a dictionary the real
    exchange never contains.
    """
    query = parse_qs(urlsplit(url).query)
    return {
        "start_date": query["start_date"][0],
        "end_date": query["end_date"][0],
        "daily": query["daily"],
        # Read leniently, alone among these: a request that forces no model is
        # the one failure worth asserting on rather than crashing on — left to
        # itself the archive endpoint switches reanalysis in 2017.
        "models": query.get("models", []),
        "timezone": query["timezone"][0],
    }


def fake_openmeteo(
    *,
    today: date | None = None,
    lag: int = DEFAULT_LAG,
    null_variables: tuple[str, ...] = (),
    forecast_days: int | None = None,
) -> tuple[Any, list[dict[str, Any]]]:
    """A fetcher recording every call, alongside what each one asked for.

    The reanalyses lag behind today; the forecast stops short of it. Both are
    parameters rather than constants, because the point of both seams is that
    their position is read from the answer rather than assumed.

    ``forecast_days`` cuts the forecast short of the fortnight it was asked for,
    counting from tomorrow. Left unset, IFS answers in full.
    """
    calls: list[dict[str, Any]] = []
    lagging_until = today - timedelta(days=lag) if today else None
    forecast_until = (
        today + timedelta(days=forecast_days) if today and forecast_days is not None else None
    )

    def fetch(url: str) -> dict[str, Any]:
        params = asked(url)
        calls.append(params)
        model = params["models"][0] if params["models"] else ""
        if model in LAGGING_MODELS:
            served_until = lagging_until
        elif model == openmeteo.FORECAST_MODEL:
            served_until = forecast_until
        else:
            served_until = None
        return payload(params, null_variables=null_variables, served_until=served_until)

    return fetch, calls
