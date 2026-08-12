"""The seams: where three sources meet, and must read as one series."""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from conftest import fake_openmeteo

from weather_simulator.domain.records import Origin
from weather_simulator.sources import openmeteo
from weather_simulator.sources.errors import CoverageError, MissingVariableError
from weather_simulator.sources.parse import DailyColumns
from weather_simulator.sources.series import fetch_series, resume_after, split_range

TODAY = date(2026, 8, 2)
LAG = 6  # the reanalyses stop here, at 2026-07-27
HORIZON = TODAY + timedelta(days=openmeteo.FORECAST_DAYS)  # 2026-08-16
POINT = (43.30, 5.37)  # Marseille


def models_called(calls):
    return [params["models"][0] for _, params in calls]


def span(calls, model):
    params = next(p for _, p in calls if p["models"][0] == model)
    return date.fromisoformat(params["start_date"]), date.fromisoformat(params["end_date"])


class TestSplitRange:
    def test_a_range_entirely_behind_today_is_all_observed(self):
        observed, forecast, simulated = split_range(date(1978, 2, 12), date(1978, 4, 15), TODAY)
        assert observed == (date(1978, 2, 12), date(1978, 4, 15))
        assert forecast is None
        assert simulated is None

    def test_a_range_beyond_the_horizon_never_reaches_the_forecast(self):
        """The trap: 2047 clears ``end > today`` while starting after the fortnight.

        Read as three separate conditions rather than an intersection, this
        yields a forecast request ending twenty years before it starts.
        """
        observed, forecast, simulated = split_range(date(2047, 9, 1), date(2047, 11, 29), TODAY)
        assert observed is None
        assert forecast is None
        assert simulated == (date(2047, 9, 1), date(2047, 11, 29))

    def test_today_is_observed_and_the_forecast_starts_tomorrow(self):
        """IFS serves today with no latency, so observation runs to tonight."""
        observed, forecast, simulated = split_range(
            TODAY - timedelta(days=2), TODAY + timedelta(days=2), TODAY
        )
        assert observed == (TODAY - timedelta(days=2), TODAY)
        assert forecast == (TODAY + timedelta(days=1), TODAY + timedelta(days=2))
        assert simulated is None

    def test_a_range_inside_the_fortnight_is_forecast_alone(self):
        """No simulated day, and therefore no correction table required."""
        observed, forecast, simulated = split_range(TODAY + timedelta(days=1), HORIZON, TODAY)
        assert observed is None
        assert forecast == (TODAY + timedelta(days=1), HORIZON)
        assert simulated is None

    def test_the_model_takes_over_the_day_after_the_horizon(self):
        _, forecast, simulated = split_range(TODAY, date(2026, 9, 30), TODAY)
        assert forecast == (TODAY + timedelta(days=1), HORIZON)
        assert simulated == (HORIZON + timedelta(days=1), date(2026, 9, 30))

    def test_the_cuts_leave_neither_gap_nor_overlap(self):
        observed, forecast, simulated = split_range(date(2026, 6, 15), date(2026, 9, 14), TODAY)
        assert observed[1] + timedelta(days=1) == forecast[0]
        assert forecast[1] + timedelta(days=1) == simulated[0]

    @pytest.mark.parametrize(
        "start, end",
        [
            (date(1949, 12, 31), date(1950, 1, 5)),
            (date(2050, 12, 25), date(2051, 1, 1)),
            (date(2030, 1, 2), date(2030, 1, 1)),
        ],
    )
    def test_ranges_outside_the_coverage_are_refused(self, start, end):
        with pytest.raises(CoverageError):
            split_range(start, end, TODAY)


class TestFourSegments:
    """Marseille, 15 June to 14 September 2026 — the range that meets them all."""

    LAST = date(2026, 9, 14)

    def setup_method(self):
        self.fetch, self.calls = fake_openmeteo(today=TODAY, lag=LAG)
        self.series = fetch_series(
            *POINT, date(2026, 6, 15), self.LAST, today=TODAY, fetch=self.fetch
        )

    def test_five_requests_in_order(self):
        assert models_called(self.calls) == [
            openmeteo.TEMPERATURE_MODEL,
            openmeteo.SURFACE_MODEL,
            openmeteo.RECENT_MODEL,
            openmeteo.FORECAST_MODEL,
            openmeteo.DEFAULT_MODEL,
        ]

    def test_ifs_resumes_the_day_the_reanalyses_stop(self):
        first, last = span(self.calls, openmeteo.RECENT_MODEL)
        assert first == TODAY - timedelta(days=LAG - 1)  # 2026-07-28
        assert last == TODAY  # the archive side carries through to tonight

    def test_the_forecast_runs_from_tomorrow_to_the_horizon(self):
        assert span(self.calls, openmeteo.FORECAST_MODEL) == (TODAY + timedelta(days=1), HORIZON)

    def test_the_model_is_asked_from_tomorrow_and_trimmed_on_return(self):
        """Asked in overlap, because where IFS stops is not knowable in advance."""
        assert span(self.calls, openmeteo.DEFAULT_MODEL) == (TODAY + timedelta(days=1), self.LAST)
        by_date = {record.date: record.source for record in self.series}
        assert by_date[HORIZON] == openmeteo.FORECAST_MODEL
        assert by_date[HORIZON + timedelta(days=1)] == openmeteo.DEFAULT_MODEL

    def test_the_series_is_contiguous_across_both_seams(self):
        dates = [record.date for record in self.series]
        assert dates == sorted(dates)
        assert len(dates) == len(set(dates)) == 92
        assert dates[0] == date(2026, 6, 15)
        assert dates[-1] == self.LAST
        assert dates[-1] - dates[0] == timedelta(days=91)

    def test_tonight_is_not_a_seam(self):
        """IFS runs straight through it — that is what the segment is for."""
        by_date = {record.date: record.origin for record in self.series}
        assert by_date[TODAY] is Origin.OBSERVED
        assert by_date[TODAY + timedelta(days=1)] is Origin.FORECAST
        assert by_date[HORIZON] is Origin.FORECAST
        assert by_date[HORIZON + timedelta(days=1)] is Origin.SIMULATED

    def test_each_day_records_which_dataset_served_it(self):
        by_date = {record.date: record.source for record in self.series}
        assert by_date[TODAY - timedelta(days=LAG)] == "reanalysis"
        assert by_date[TODAY - timedelta(days=LAG - 1)] == openmeteo.RECENT_MODEL
        assert by_date[TODAY] == openmeteo.RECENT_MODEL
        assert by_date[TODAY + timedelta(days=1)] == openmeteo.FORECAST_MODEL
        assert by_date[HORIZON + timedelta(days=1)] == openmeteo.DEFAULT_MODEL

    def test_every_day_carries_the_same_fields_whichever_source_served_it(self):
        expected = set(openmeteo.ALL_VARIABLES.values())
        for record in self.series:
            carried = {
                field
                for field in record.__slots__
                if field not in {"date", "origin", "source"} and getattr(record, field) is not None
            }
            assert carried == expected, f"{record.date} is short of {expected - carried}"

    def test_the_snow_criterion_never_reads_snowfall(self):
        """The model holes it irregularly, so nothing may depend on it."""
        assert "snowfall_sum" in openmeteo.OPTIONAL_VARIABLES
        for field in ("temperature_mean", "precipitation"):
            assert field in openmeteo.ALL_VARIABLES.values()


class TestSeamPlacement:
    @pytest.mark.parametrize("lag", [3, 6, 9])
    def test_the_seam_follows_the_data_rather_than_a_constant(self, lag):
        fetch, calls = fake_openmeteo(today=TODAY, lag=lag)
        fetch_series(*POINT, TODAY - timedelta(days=30), TODAY, today=TODAY, fetch=fetch)
        assert span(calls, openmeteo.RECENT_MODEL)[0] == TODAY - timedelta(days=lag - 1)

    @pytest.mark.parametrize("served", [5, 10, 14])
    def test_the_model_takes_over_where_the_forecast_actually_stopped(self, served):
        """A forecast cut short moves the seam; it must not leave a hole.

        This is what asking the climate model from tomorrow buys: the request is
        planned before IFS has answered, so the handover cannot be computed then.
        """
        fetch, _ = fake_openmeteo(today=TODAY, lag=LAG, forecast_days=served)
        series = fetch_series(*POINT, TODAY, date(2026, 9, 30), today=TODAY, fetch=fetch)

        by_date = {record.date: record.origin for record in series}
        last_forecast = TODAY + timedelta(days=served)
        assert by_date[last_forecast] is Origin.FORECAST
        assert by_date[last_forecast + timedelta(days=1)] is Origin.SIMULATED

        dates = [record.date for record in series]
        assert len(dates) == len(set(dates))  # the overlap left no duplicate
        assert dates == sorted(dates)
        assert dates[-1] - dates[0] == timedelta(days=len(dates) - 1)  # nor any hole

    def test_a_range_within_the_latency_falls_entirely_to_ifs(self):
        fetch, calls = fake_openmeteo(today=TODAY, lag=LAG)
        series = fetch_series(*POINT, TODAY - timedelta(days=3), TODAY, today=TODAY, fetch=fetch)
        assert span(calls, openmeteo.RECENT_MODEL) == (TODAY - timedelta(days=3), TODAY)
        assert len(series) == 4
        assert {record.origin for record in series} == {Origin.OBSERVED}


class TestSingleSegment:
    def test_an_old_range_never_reaches_ifs_or_the_model(self):
        """Langres, 12 February to 15 April 1978 — the reanalyses alone."""
        fetch, calls = fake_openmeteo(today=TODAY, lag=LAG)
        series = fetch_series(
            *POINT, date(1978, 2, 12), date(1978, 4, 15), today=TODAY, fetch=fetch
        )
        assert models_called(calls) == [openmeteo.TEMPERATURE_MODEL, openmeteo.SURFACE_MODEL]
        assert len(series) == 63
        assert {record.origin for record in series} == {Origin.OBSERVED}

    def test_a_far_future_range_takes_one_request(self):
        """Tokyo, September to November 2047 — the model alone, no forecast."""
        fetch, calls = fake_openmeteo(today=TODAY, lag=LAG)
        series = fetch_series(
            *POINT, date(2047, 9, 1), date(2047, 11, 29), today=TODAY, fetch=fetch
        )
        assert models_called(calls) == [openmeteo.DEFAULT_MODEL]
        assert {record.origin for record in series} == {Origin.SIMULATED}

    def test_a_range_inside_the_fortnight_takes_the_forecast_alone(self):
        """No simulated day, so no climate request and no correction needed."""
        fetch, calls = fake_openmeteo(today=TODAY, lag=LAG)
        series = fetch_series(*POINT, TODAY + timedelta(days=1), HORIZON, today=TODAY, fetch=fetch)
        assert models_called(calls) == [openmeteo.FORECAST_MODEL]
        assert {record.origin for record in series} == {Origin.FORECAST}
        assert len(series) == openmeteo.FORECAST_DAYS


class TestRequestShape:
    def test_the_source_is_always_forced(self):
        """Left to itself the archive endpoint switches reanalysis in 2017."""
        fetch, calls = fake_openmeteo(today=TODAY, lag=LAG)
        fetch_series(*POINT, date(2015, 1, 1), date(2015, 3, 31), today=TODAY, fetch=fetch)
        assert all("models" in params for _, params in calls)

    def test_days_are_local_days(self):
        """A daily maximum spanning 09:00 to 09:00 would mean nothing in Tokyo."""
        fetch, calls = fake_openmeteo(today=TODAY, lag=LAG)
        fetch_series(*POINT, date(2047, 9, 1), date(2047, 9, 30), today=TODAY, fetch=fetch)
        assert all(params["timezone"] == "auto" for _, params in calls)

    def test_the_model_is_a_parameter_never_a_hard_coded_value(self):
        fetch, calls = fake_openmeteo(today=TODAY, lag=LAG)
        fetch_series(
            *POINT,
            date(2047, 9, 1),
            date(2047, 9, 30),
            model="NICAM16_8S",
            today=TODAY,
            fetch=fetch,
        )
        assert models_called(calls) == ["NICAM16_8S"]

    def test_a_silently_unserved_variable_stops_the_assembly(self):
        """Cloud cover is what the sky class rests on; a null column is fatal."""
        fetch, _ = fake_openmeteo(today=TODAY, lag=LAG, null_variables=("cloud_cover_mean",))
        with pytest.raises(MissingVariableError):
            fetch_series(*POINT, date(2047, 9, 1), date(2047, 9, 30), today=TODAY, fetch=fetch)

    def test_a_missing_snowfall_no_longer_stops_anything(self):
        """The gap the climate model leaves must not take the request down."""
        fetch, _ = fake_openmeteo(today=TODAY, lag=LAG, null_variables=("snowfall_sum",))
        series = fetch_series(*POINT, date(2047, 9, 1), date(2047, 9, 30), today=TODAY, fetch=fetch)
        assert len(series) == 30
        assert all(record.snowfall is None for record in series)
        assert all(record.precipitation is not None for record in series)


class TestResumeAfter:
    """Settling the overlap when IFS was fetched without waiting for the reanalyses.

    The browser executes a plan built in one go, so IFS is asked for the whole
    stretch the reanalyses might not reach. The reanalyses win wherever they
    served, and the boundary is read from the days they actually returned.
    """

    @staticmethod
    def columns(first: date, last: date) -> DailyColumns:
        span = (last - first).days + 1
        dates = [first + timedelta(days=offset) for offset in range(span)]
        return DailyColumns(dates, {"cloud_cover": [float(i) for i in range(span)]})

    def test_the_days_the_reanalyses_served_are_given_up(self):
        recent = self.columns(date(2026, 7, 1), date(2026, 8, 2))
        trimmed = resume_after(recent, date(2026, 7, 27))

        assert trimmed.dates[0] == date(2026, 7, 28)
        assert trimmed.dates[-1] == date(2026, 8, 2)
        assert len(trimmed.columns["cloud_cover"]) == len(trimmed.dates)

    def test_the_values_follow_their_dates(self):
        """A column trimmed out of step with its dates would misdate every day."""
        recent = self.columns(date(2026, 7, 1), date(2026, 7, 5))
        trimmed = resume_after(recent, date(2026, 7, 2))

        assert trimmed.dates == [date(2026, 7, 3), date(2026, 7, 4), date(2026, 7, 5)]
        assert trimmed.columns["cloud_cover"] == [2.0, 3.0, 4.0]

    def test_without_a_boundary_nothing_is_given_up(self):
        """No reanalysis at all — a range wholly after they stopped, say."""
        recent = self.columns(date(2026, 7, 1), date(2026, 7, 5))
        assert resume_after(recent, None) is recent

    def test_a_boundary_before_the_segment_gives_up_nothing(self):
        recent = self.columns(date(2026, 7, 1), date(2026, 7, 5))
        assert resume_after(recent, date(2026, 6, 30)).dates[0] == date(2026, 7, 1)
