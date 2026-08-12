"""The two halves of a search, over HTTP.

No network anywhere: the browser's part is played by ``tests/conftest.py``,
which answers with the shapes and the gaps Open-Meteo really returns, and the
correction table is injected rather than read from disk.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import pytest
from conftest import DEFAULT_LAG, payload
from fastapi.testclient import TestClient

from weather_simulator.api import plan as planning
from weather_simulator.api.app import app, get_grid, load_grid
from weather_simulator.calibration.grid import CorrectionGrid
from weather_simulator.calibration.table import CorrectionTable, Metadata
from weather_simulator.domain.correction import CloudCorrection, MonthlyCorrection, quantiles
from weather_simulator.sources import openmeteo

STEP = 0.5
SAMPLE = [float(v) for v in range(0, 101, 2)] * 3
SHIFT = 10.0

# One covered cell, and Paris inside it — the same corner of the real table that
# the collection has actually reached.
COVERED = [(48.5, 2.0), (48.5, 2.5), (49.0, 2.0), (49.0, 2.5)]
PARIS = (48.8566, 2.3522)
SANTIAGO = (-33.4489, -70.6693)

TODAY = date(2026, 8, 7)


def _correction() -> CloudCorrection:
    """A node whose model runs ``SHIFT`` points short, and projects no change."""
    biased = quantiles([max(0.0, v - SHIFT) for v in SAMPLE])
    reference = quantiles(SAMPLE)
    return CloudCorrection(
        {
            month: MonthlyCorrection(reference=reference, model_past=biased, model_future=biased)
            for month in range(1, 13)
        }
    )


def _grid(placeholder: bool = False) -> CorrectionGrid:
    metadata = Metadata(
        model=openmeteo.DEFAULT_MODEL,
        calibration_start=date(1985, 1, 1),
        calibration_end=date(2014, 12, 31),
        projection_start=date(2021, 1, 1),
        projection_end=date(2050, 12, 31),
        step=STEP,
        generated=date(2026, 8, 4),
        node_count=len(COVERED),
        placeholder=placeholder,
    )
    return CorrectionGrid(CorrectionTable(metadata, {node: _correction() for node in COVERED}))


@pytest.fixture
def client() -> TestClient:
    """A client whose grid covers Paris and nothing else.

    ``TestClient(app)`` without a context manager runs no lifespan, so the
    shipped table is never read here.
    """
    app.dependency_overrides[get_grid] = _grid
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def frozen_today(monkeypatch) -> date:
    """Pin the day, so the seam sits where the test says it does."""
    monkeypatch.setattr("weather_simulator.api.app.today_in_reference_zone", lambda: TODAY)
    return TODAY


def _search(start: date, end: date, point: tuple[float, float] = PARIS) -> dict[str, Any]:
    latitude, longitude = point
    return {
        "latitude": latitude,
        "longitude": longitude,
        "start": start.isoformat(),
        "end": end.isoformat(),
    }


def _fetch(url: str, *, lag: int = DEFAULT_LAG, forecast_days: int | None = None) -> dict[str, Any]:
    """Play the browser: answer a planned URL the way Open-Meteo would.

    ``forecast_days`` cuts IFS short of the fortnight it was asked for, which is
    the case the climate model's overlap exists to absorb.
    """
    from urllib.parse import parse_qs, urlsplit

    query = parse_qs(urlsplit(url).query)
    params = {
        "start_date": query["start_date"][0],
        "end_date": query["end_date"][0],
        "daily": query["daily"],
        "models": query["models"],
    }
    model = params["models"][0]
    served_until = None
    if model in {openmeteo.TEMPERATURE_MODEL, openmeteo.SURFACE_MODEL}:
        served_until = TODAY - timedelta(days=lag)
    elif model == openmeteo.FORECAST_MODEL and forecast_days is not None:
        served_until = TODAY + timedelta(days=forecast_days)
    return payload(params, served_until=served_until)


def _run(client: TestClient, search: dict[str, Any], **answers: Any) -> Any:
    """A whole search: plan, fetch, days."""
    planned = client.post("/api/plan", json=search)
    assert planned.status_code == 200, planned.json()
    body = planned.json()
    return client.post(
        "/api/days",
        json={
            **search,
            "today": body["today"],
            "payloads": {r["id"]: _fetch(r["url"], **answers) for r in body["requests"]},
        },
    )


# --- the plan tells the browser exactly what to fetch ------------------------


def test_a_past_range_needs_no_climate_request(client, frozen_today) -> None:
    body = client.post("/api/plan", json=_search(date(2020, 6, 1), date(2020, 6, 30))).json()
    assert [r["id"] for r in body["requests"]] == [
        planning.TEMPERATURE,
        planning.SURFACE,
        planning.RECENT,
    ]


def test_a_range_before_2017_gets_no_ifs_request(client, frozen_today) -> None:
    """IFS covers 2017 onwards. Asking it for 1960 would be asking for nothing."""
    body = client.post("/api/plan", json=_search(date(1960, 6, 1), date(1960, 6, 30))).json()
    assert [r["id"] for r in body["requests"]] == [planning.TEMPERATURE, planning.SURFACE]


def test_a_future_range_gets_the_climate_request_alone(client, frozen_today) -> None:
    body = client.post("/api/plan", json=_search(date(2046, 7, 1), date(2046, 7, 31))).json()
    assert [r["id"] for r in body["requests"]] == [planning.PROJECTION]


def test_a_range_straddling_today_meets_every_segment(client, frozen_today) -> None:
    body = client.post(
        "/api/plan", json=_search(TODAY - timedelta(days=30), TODAY + timedelta(days=30))
    ).json()
    assert [r["id"] for r in body["requests"]] == [
        planning.TEMPERATURE,
        planning.SURFACE,
        planning.RECENT,
        planning.FORECAST,
        planning.PROJECTION,
    ]
    assert body["today"] == TODAY.isoformat()


def test_a_range_inside_the_fortnight_needs_no_climate_request(client, frozen_today) -> None:
    """And therefore no correction table — the near future works everywhere."""
    body = client.post(
        "/api/plan",
        json=_search(TODAY + timedelta(days=1), TODAY + timedelta(days=openmeteo.FORECAST_DAYS)),
    ).json()
    assert [r["id"] for r in body["requests"]] == [planning.FORECAST]


def test_the_planned_urls_carry_the_forced_model_and_the_timezone(client, frozen_today) -> None:
    """Left to itself the archive endpoint plants a second seam in 2017."""
    body = client.post("/api/plan", json=_search(date(2020, 6, 1), date(2020, 6, 30))).json()
    urls = {r["id"]: r["url"] for r in body["requests"]}

    assert f"models={openmeteo.TEMPERATURE_MODEL}" in urls[planning.TEMPERATURE]
    assert f"models={openmeteo.SURFACE_MODEL}" in urls[planning.SURFACE]
    assert all("timezone=auto" in url for url in urls.values())


# --- the refusals ------------------------------------------------------------


@pytest.mark.parametrize(
    ("start", "end", "fragment"),
    [
        (date(2020, 6, 30), date(2020, 6, 1), "précède"),
        (date(1949, 12, 31), date(1950, 1, 10), "1950"),
        (date(2050, 12, 25), date(2051, 1, 5), "1950"),
        (date(2020, 1, 1), date(2020, 6, 1), "90 jours"),
    ],
)
def test_an_impossible_range_is_refused_in_french(
    client, frozen_today, start: date, end: date, fragment: str
) -> None:
    response = client.post("/api/plan", json=_search(start, end))
    assert response.status_code == 400
    assert fragment in response.json()["message"]


def test_the_ninety_day_bound_counts_both_ends(client, frozen_today) -> None:
    start = date(2020, 1, 1)

    def status(span: int) -> int:
        search = _search(start, start + timedelta(days=span))
        return client.post("/api/plan", json=search).status_code

    assert status(89) == 200  # ninety days inclusive
    assert status(90) == 400


@pytest.mark.parametrize(
    "body",
    [
        {"latitude": 200.0, "longitude": 2.0, "start": "2020-06-01", "end": "2020-06-10"},
        {"latitude": 48.8, "longitude": 2.3, "start": "pas-une-date", "end": "2020-06-10"},
        {"latitude": 48.8},
    ],
)
def test_a_malformed_body_is_refused_in_french_too(client, frozen_today, body: dict) -> None:
    """One shape of refusal for the interface to read, whatever went wrong."""
    response = client.post("/api/plan", json=body)
    assert response.status_code == 422
    assert "mal formées" in response.json()["message"]


def test_a_place_outside_the_grid_is_refused_for_the_future(client, frozen_today) -> None:
    """An uncorrected future would be an artificially sunny one. Not shown."""
    response = client.post("/api/plan", json=_search(date(2046, 7, 1), date(2046, 7, 31), SANTIAGO))
    assert response.status_code == 400
    assert "pas encore couvert" in response.json()["message"]


def test_the_same_place_is_served_for_the_past(client, frozen_today) -> None:
    """A past range calls for no coefficient. Refusing it would be gratuitous."""
    response = client.post("/api/plan", json=_search(date(2020, 6, 1), date(2020, 6, 30), SANTIAGO))
    assert response.status_code == 200


def test_payloads_that_do_not_match_the_plan_are_refused(client, frozen_today) -> None:
    search = _search(date(2020, 6, 1), date(2020, 6, 30))
    response = client.post(
        "/api/days", json={**search, "today": TODAY.isoformat(), "payloads": {"invented": {}}}
    )
    assert response.status_code == 400
    assert "ne correspondent pas" in response.json()["message"]


def test_a_plan_from_another_day_is_refused(client, frozen_today) -> None:
    """At midnight the cut between what happened and what might have moves."""
    search = _search(date(2020, 6, 1), date(2020, 6, 30))
    response = client.post(
        "/api/days",
        json={**search, "today": (TODAY - timedelta(days=5)).isoformat(), "payloads": {}},
    )
    assert response.status_code == 409


# --- the whole exchange ------------------------------------------------------


def test_a_past_search_comes_back_as_observed_days(client, frozen_today) -> None:
    response = _run(client, _search(date(2020, 6, 1), date(2020, 6, 30)))
    assert response.status_code == 200, response.json()
    body = response.json()

    assert body["has_simulated"] is False
    assert body["grid"] is None
    assert len(body["days"]) == 30
    assert {day["origin"] for day in body["days"]} == {"observed"}


def test_a_future_search_is_corrected_and_flagged(client, frozen_today) -> None:
    response = _run(client, _search(date(2046, 7, 1), date(2046, 7, 31)))
    assert response.status_code == 200, response.json()
    body = response.json()

    assert body["has_simulated"] is True
    assert body["grid"]["model"] == openmeteo.DEFAULT_MODEL
    assert {day["origin"] for day in body["days"]} == {"simulated"}
    # conftest serves cloud_cover as the 6th requested variable, so 6.0 raw.
    assert body["days"][0]["cloud_cover"] == pytest.approx(6.0 + SHIFT)


def test_a_straddling_search_has_no_hole_and_no_duplicate(client, frozen_today) -> None:
    """The seam is the point of the whole exchange. It must not show."""
    start, end = TODAY - timedelta(days=30), TODAY + timedelta(days=30)
    response = _run(client, _search(start, end))
    assert response.status_code == 200, response.json()
    days = response.json()["days"]

    dates = [date.fromisoformat(day["date"]) for day in days]
    assert dates == sorted(dates)
    assert len(dates) == len(set(dates)) == 61
    assert dates[0] == start and dates[-1] == end


def test_the_reanalyses_keep_the_days_they_served(client, frozen_today) -> None:
    """IFS is asked for in overlap; it must only cover what they did not reach."""
    start, end = TODAY - timedelta(days=30), TODAY
    response = _run(client, _search(start, end))
    sources = {date.fromisoformat(d["date"]): d["source"] for d in response.json()["days"]}

    handover = TODAY - timedelta(days=DEFAULT_LAG)
    assert sources[handover] == "reanalysis"
    assert sources[handover + timedelta(days=1)] == openmeteo.RECENT_MODEL
    assert sources[TODAY] == openmeteo.RECENT_MODEL


def test_the_forecast_keeps_the_days_it_served(client, frozen_today) -> None:
    """The second seam, settled the same way as the first: IFS wins where it served."""
    response = _run(client, _search(TODAY, TODAY + timedelta(days=40)), forecast_days=9)
    days = response.json()["days"]
    origins = {date.fromisoformat(day["date"]): day["origin"] for day in days}

    handover = TODAY + timedelta(days=9)
    assert origins[handover] == "forecast"
    assert origins[handover + timedelta(days=1)] == "simulated"

    dates = [date.fromisoformat(day["date"]) for day in days]
    assert len(dates) == len(set(dates)) == 41  # the overlap left no duplicate, no hole


def test_a_near_future_search_needs_no_correction_table(client, frozen_today) -> None:
    """The fortnight ahead is IFS, which needs no debiasing — so it works anywhere.

    ``has_simulated`` is false, so no warning is raised and no grid is reported:
    the answer carries a forecast, not a trajectory.
    """
    response = _run(
        client,
        _search(TODAY + timedelta(days=1), TODAY + timedelta(days=openmeteo.FORECAST_DAYS)),
    )
    assert response.status_code == 200, response.json()
    body = response.json()

    assert body["has_simulated"] is False
    assert body["grid"] is None
    assert {day["origin"] for day in body["days"]} == {"forecast"}


def test_a_forecast_day_is_never_corrected(client, frozen_today) -> None:
    """Only the climate model is short of cloud; correcting IFS would invent a bias."""
    response = _run(client, _search(TODAY + timedelta(days=1), TODAY + timedelta(days=40)))
    days = {d["origin"]: d for d in reversed(response.json()["days"])}
    # conftest serves cloud_cover as the 6th requested variable, so 6.0 raw.
    assert days["forecast"]["cloud_cover"] == pytest.approx(6.0)
    assert days["simulated"]["cloud_cover"] == pytest.approx(6.0 + SHIFT)


def test_today_belongs_to_the_observed_half(client, frozen_today) -> None:
    response = _run(client, _search(TODAY - timedelta(days=2), TODAY))
    days = response.json()["days"]

    assert days[-1]["date"] == TODAY.isoformat()
    assert days[-1]["origin"] == "observed"


def test_the_contract_never_carries_a_pictogram(client, frozen_today) -> None:
    response = _run(client, _search(date(2020, 6, 1), date(2020, 6, 30)))
    day = response.json()["days"][0]

    assert day["sky"] in {"clear", "cloudy", "overcast", "rain", "snow", None}
    assert set(day) == {
        "date",
        "origin",
        "source",
        "temperature_min",
        "temperature_max",
        "precipitation",
        "cloud_cover",
        "wind_speed_mean",
        "wind_speed_max",
        "sky",
    }


# --- the fifth lock ----------------------------------------------------------


def test_a_placeholder_table_stops_the_boot(tmp_path) -> None:
    """The one lock no oversight can walk past."""
    path = tmp_path / "cloud_correction_placeholder.json"
    CorrectionTable(_grid(placeholder=True).table.metadata, _grid().table.nodes).write(path)

    with pytest.raises(RuntimeError, match="placeholder"):
        load_grid(path)


def test_the_real_table_loads(tmp_path) -> None:
    path = tmp_path / "cloud_correction.json"
    _grid().table.write(path)
    assert load_grid(path).is_placeholder is False


# --- what the interface is told before it asks anything ----------------------


def test_the_config_carries_the_bounds_the_api_enforces(client) -> None:
    body = client.get("/api/config").json()

    assert body["max_days"] == 90
    assert body["coverage_start"] == "1950-01-01"
    assert body["coverage_end"] == "2050-12-31"
    assert body["geocoding_url"] == openmeteo.GEOCODING_URL
