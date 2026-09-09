"""Reading a payload: naming, and the absences that announce themselves as data."""

from __future__ import annotations

from datetime import date

import pytest
from conftest import payload

from weather_simulator.sources import openmeteo
from weather_simulator.sources.errors import FetchError, MissingVariableError
from weather_simulator.sources.parse import DailyColumns, merge_columns, parse_daily

PARAMS = {
    "start_date": "2020-01-01",
    "end_date": "2020-01-03",
    "daily": list(openmeteo.TEMPERATURE_VARIABLES),
    "models": ["era5_land"],
}


def test_bare_keys_are_read():
    columns = parse_daily(payload(PARAMS), openmeteo.TEMPERATURE_VARIABLES, source="era5_land")
    assert columns.dates == [date(2020, 1, 1), date(2020, 1, 2), date(2020, 1, 3)]
    assert set(columns.columns) == {"temperature_max", "temperature_min", "temperature_mean"}


def test_the_temperature_request_asks_for_the_dew_point_too() -> None:
    """What ERA5-Land is asked for is a superset of the three temperatures.

    The two names are not a tidying accident. The dew point joined the request at
    step 8; ``scripts/model_selection/`` is frozen and replays a 2026 cache that
    holds the three columns alone, through ``TEMPERATURE_VARIABLES``. Folding the
    fourth into that name turned the frozen replay into a MissingVariableError,
    which is a measurement stopping being reproducible.
    """
    params = {**PARAMS, "daily": list(openmeteo.TEMPERATURE_REQUEST_VARIABLES)}
    columns = parse_daily(
        payload(params), openmeteo.TEMPERATURE_REQUEST_VARIABLES, source="era5_land"
    )

    assert set(openmeteo.TEMPERATURE_VARIABLES) < set(openmeteo.TEMPERATURE_REQUEST_VARIABLES)
    assert "dew_point_mean" in columns.columns


def test_the_frozen_step_two_cache_still_parses() -> None:
    """A payload with the three columns and no dew point, read as step 2 reads it.

    The regression this pins is silent from the application's side: everything
    served today carries the dew point, so nothing fails until someone replays
    the model comparison from ``data/model_selection/`` and finds it will no
    longer load.
    """
    columns = parse_daily(payload(PARAMS), openmeteo.TEMPERATURE_VARIABLES, source="era5_land")

    assert "dew_point_mean" not in columns.columns
    assert len(columns.dates) == 3


def test_model_suffixed_keys_are_read():
    """The Climate API appends the model name to every key."""
    params = {**PARAMS, "models": ["MRI_AGCM3_2_S"]}
    columns = parse_daily(
        payload(params, suffixed=True),
        openmeteo.TEMPERATURE_VARIABLES,
        source="MRI_AGCM3_2_S",
        model="MRI_AGCM3_2_S",
    )
    assert columns.columns["temperature_max"] == [1.0, 1.0, 1.0]


def test_an_all_null_column_is_an_error_not_a_column():
    """HTTP 200 with nothing in it is the trap the design document warns about."""
    with pytest.raises(MissingVariableError) as raised:
        parse_daily(
            payload(PARAMS, null_variables=("temperature_2m_min",)),
            openmeteo.TEMPERATURE_VARIABLES,
            source="era5_land",
        )
    assert raised.value.variable == "temperature_2m_min"


def test_a_variable_absent_from_the_payload_is_reported():
    body = payload(PARAMS)
    del body["daily"]["temperature_2m_min"]
    with pytest.raises(MissingVariableError):
        parse_daily(body, openmeteo.TEMPERATURE_VARIABLES, source="era5_land")


def test_a_short_column_is_refused():
    body = payload(PARAMS)
    body["daily"]["temperature_2m_max"] = [1.0]
    with pytest.raises(FetchError):
        parse_daily(body, openmeteo.TEMPERATURE_VARIABLES, source="era5_land")


def test_a_payload_without_daily_block_is_refused():
    with pytest.raises(FetchError):
        parse_daily({"latitude": 46.9}, openmeteo.TEMPERATURE_VARIABLES, source="era5_land")


def test_merging_the_two_past_requests_joins_on_the_date():
    # The request set and not the three temperatures: what the two old-past calls
    # actually bring back together is what ALL_VARIABLES names.
    temperature_params = {**PARAMS, "daily": list(openmeteo.TEMPERATURE_REQUEST_VARIABLES)}
    temperature = parse_daily(
        payload(temperature_params),
        openmeteo.TEMPERATURE_REQUEST_VARIABLES,
        source="era5_land",
    )
    surface_params = {**PARAMS, "daily": list(openmeteo.SURFACE_VARIABLES), "models": ["era5"]}
    surface = parse_daily(payload(surface_params), openmeteo.SURFACE_VARIABLES, source="era5")
    merged = merge_columns(temperature, surface, source="archive")
    assert merged.dates == temperature.dates
    assert set(merged.columns) == set(openmeteo.ALL_VARIABLES.values())


def test_merging_refuses_mismatched_dates():
    left = DailyColumns([date(2020, 1, 1)], {"temperature_max": [1.0]})
    right = DailyColumns([date(2020, 1, 2)], {"precipitation": [0.0]})
    with pytest.raises(FetchError):
        merge_columns(left, right, source="archive")


def test_merging_stops_where_the_slower_request_stops():
    """A day half-served would depend on which source answered."""
    long = DailyColumns([date(2020, 1, 1), date(2020, 1, 2)], {"temperature_max": [1.0, 2.0]})
    short = DailyColumns([date(2020, 1, 1)], {"precipitation": [0.0]})
    merged = merge_columns(long, short, source="archive")
    assert merged.dates == [date(2020, 1, 1)]
    assert merged.columns == {"temperature_max": [1.0], "precipitation": [0.0]}


LAGGING = {**PARAMS, "end_date": "2020-01-05"}


def test_days_the_source_has_not_caught_up_with_are_dropped():
    columns = parse_daily(
        payload(LAGGING, served_until=date(2020, 1, 3)),
        openmeteo.TEMPERATURE_VARIABLES,
        source="era5_land",
        allow_trailing_gap=True,
    )
    assert columns.dates[-1] == date(2020, 1, 3)
    assert all(value is not None for value in columns.columns["temperature_max"])


def test_the_gap_is_kept_when_trimming_is_not_asked_for():
    """Only the archive segment has another source to hand the tail to."""
    columns = parse_daily(
        payload(LAGGING, served_until=date(2020, 1, 3)),
        openmeteo.TEMPERATURE_VARIABLES,
        source="era5_land",
    )
    assert columns.dates[-1] == date(2020, 1, 5)
    assert columns.columns["temperature_max"][-1] is None


def test_a_fully_lagging_response_yields_nothing_rather_than_an_error():
    columns = parse_daily(
        payload(LAGGING, served_until=date(2019, 12, 31)),
        openmeteo.TEMPERATURE_VARIABLES,
        source="era5_land",
        allow_trailing_gap=True,
    )
    assert columns.dates == []


def test_an_optional_variable_may_be_absent_without_error():
    """Snowfall is kept as a yardstick; nothing downstream reads it."""
    surface = {**PARAMS, "daily": list(openmeteo.SURFACE_VARIABLES), "models": ["era5"]}
    columns = parse_daily(
        payload(surface, null_variables=("snowfall_sum",)),
        openmeteo.SURFACE_VARIABLES,
        source="era5",
        optional=openmeteo.OPTIONAL_VARIABLES,
    )
    assert columns.columns["snowfall"] == [None, None, None]
    assert all(v is not None for v in columns.columns["precipitation"])


def test_an_optional_variable_missing_from_the_payload_yields_a_null_column():
    surface = {**PARAMS, "daily": list(openmeteo.SURFACE_VARIABLES), "models": ["era5"]}
    body = payload(surface)
    del body["daily"]["snowfall_sum"]
    columns = parse_daily(
        body, openmeteo.SURFACE_VARIABLES, source="era5", optional=openmeteo.OPTIONAL_VARIABLES
    )
    assert columns.columns["snowfall"] == [None, None, None]


def test_trimming_does_not_mask_a_variable_that_is_never_served():
    """Latency drops whole days; an unserved variable leaves the others intact."""
    with pytest.raises(MissingVariableError):
        parse_daily(
            payload(LAGGING, null_variables=("temperature_2m_min",)),
            openmeteo.TEMPERATURE_VARIABLES,
            source="era5_land",
            allow_trailing_gap=True,
        )
