"""Turning an Open-Meteo payload into columns, and catching silent absences.

Two traps live here.

The first is naming. Asked for a single model, both endpoints return the bare
variable name — the suffixed spelling (``temperature_2m_max_MRI_AGCM3_2_S``)
appears only when several models are requested at once, which this project never
does. The earlier prototype assumed the suffix was always there; it is not.
Both spellings are accepted rather than betting on either.

The second is the silent null. A variable a source does not serve comes back as
a full column of ``None`` under HTTP 200, with the unit reported as
``undefined``. Nothing in the status code says anything is wrong, so an
all-null column is treated as the error it is.
"""

from __future__ import annotations

from datetime import date
from typing import Any, NamedTuple

from weather_simulator.sources.errors import FetchError, MissingVariableError


class DailyColumns(NamedTuple):
    """Dates, and one column per requested variable, keyed by record field."""

    dates: list[date]
    columns: dict[str, list[float | None]]


def _resolve_key(daily: dict[str, Any], variable: str, model: str | None) -> str | None:
    if variable in daily:
        return variable
    if model is not None and f"{variable}_{model}" in daily:
        return f"{variable}_{model}"
    # Last resort: the model name is not always echoed exactly as it was sent.
    candidates = [k for k in daily if k.startswith(f"{variable}_")]
    return candidates[0] if len(candidates) == 1 else None


def parse_daily(
    payload: dict[str, Any],
    variables: dict[str, str],
    *,
    source: str,
    model: str | None = None,
    allow_trailing_gap: bool = False,
    optional: frozenset[str] = frozenset(),
) -> DailyColumns:
    """Extract the requested variables, or say precisely what is missing.

    ``variables`` maps Open-Meteo names to :class:`DailyRecord` field names.

    ``optional`` names the variables whose absence is tolerated — those nothing
    downstream depends on, kept for the record rather than relied upon. Every
    other variable missing entirely is an error.

    ``allow_trailing_gap`` distinguishes the two ways a null can arrive. A
    variable a source never serves is an error whatever the day. Days a source
    has not caught up with yet are not: the reanalyses run five to six days
    behind, and those trailing days are dropped here so another source can cover
    them. Only days where *every* variable is missing are dropped, so a variable
    absent throughout is still reported rather than quietly trimmed away.
    """
    daily = payload.get("daily")
    if not isinstance(daily, dict):
        raise FetchError(f"{source} returned no 'daily' block")

    times = daily.get("time")
    if not isinstance(times, list) or not times:
        raise FetchError(f"{source} returned an empty 'time' column")
    dates = [date.fromisoformat(t) for t in times]

    columns: dict[str, list[float | None]] = {}
    for variable, field in variables.items():
        key = _resolve_key(daily, variable, model)
        if key is None:
            if variable in optional:
                columns[field] = [None] * len(dates)
                continue
            raise MissingVariableError(variable, source)

        values = daily[key]
        if len(values) != len(dates):
            raise FetchError(
                f"{source} returned {len(values)} values for {variable!r} "
                f"against {len(dates)} dates"
            )
        columns[field] = list(values)

    if allow_trailing_gap:
        served = len(dates)
        while served and all(column[served - 1] is None for column in columns.values()):
            served -= 1
        dates = dates[:served]
        columns = {field: column[:served] for field, column in columns.items()}

    for variable, field in variables.items():
        if variable in optional:
            continue
        if columns[field] and all(v is None for v in columns[field]):
            raise MissingVariableError(variable, source)

    return DailyColumns(dates, columns)


def merge_columns(*parts: DailyColumns, source: str) -> DailyColumns:
    """Join several payloads of the same segment on the date.

    The past segment takes two requests differing only by ``models``, so their
    columns have to be brought back together. They are joined on the date alone
    — no reconciliation of any kind, both APIs reporting the same elevation for
    a point, derived from the same terrain model.
    """
    if not parts:
        raise ValueError("nothing to merge")

    # Trimming may have left one request shorter than the other, if the two
    # reanalyses do not run exactly the same number of days behind. The series
    # then stops where the slower one stops, and the following segment covers
    # the rest — a day half-served would be a day whose fields depend on which
    # source answered, which is precisely what must never happen.
    served = min(len(part.dates) for part in parts)
    dates = parts[0].dates[:served]
    for part in parts:
        if part.dates[:served] != dates:
            raise FetchError(f"{source} returned mismatched dates across requests")

    columns: dict[str, list[float | None]] = {}
    for part in parts:
        columns.update({field: column[:served] for field, column in part.columns.items()})
    return DailyColumns(dates, columns)
