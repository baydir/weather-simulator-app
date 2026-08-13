"""The HTTP layer: three endpoints, no state, no database.

A search takes two calls. ``/api/plan`` turns a place and a range into the list
of Open-Meteo requests that cover it, already spelled out as URLs; the browser
runs them; ``/api/days`` takes the answers back and returns the classified
series. ``/api/config`` serves, once per page, the handful of constants the
interface needs to refuse an impossible search before asking anything.

Two endpoints rather than the single one docs/application.md describes. The
browser has to fetch, because Open-Meteo limits per IP; but choosing *what* to
fetch stays here, and for two reasons. The server holds a live version of that
choice — ``/api/days`` replays the plan to check the payloads against the search
— so building it in the browser too would be the one duplication CLAUDE.md rule 3
is about. And the range is cut at today taken from this machine's clock, where a
browser's is the visitor's own. Both endpoints are stateless, so the property the
single one stood for — scaling by multiplying instances — is untouched.

**The correction table is read once, at start-up, and a placeholder stops the
boot.** The four locks docs/application.md lists are all things a caller has to
remember to check; this is the fifth, and the only one no oversight can walk
past. An uncorrected future is sunny by 8 to 11 points of cloud cover and three
of the five sky classes hang off that, so the failure has to be the loud kind.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.responses import Response

from weather_simulator.api import errors, pipeline, validation
from weather_simulator.api import plan as planning
from weather_simulator.api.contract import Series
from weather_simulator.calibration.grid import CorrectionGrid
from weather_simulator.calibration.table import CorrectionTable, OutsideCoverage
from weather_simulator.domain import thresholds
from weather_simulator.sources import openmeteo
from weather_simulator.sources.errors import SourceError
from weather_simulator.sources.series import today_in_reference_zone

TABLE_PATH = (
    Path(__file__).resolve().parent.parent / "calibration" / "data" / "cloud_correction.json"
)

WEB = Path(__file__).resolve().parents[3] / "web"


def load_grid(path: Path = TABLE_PATH) -> CorrectionGrid:
    """Read the shipped table, and refuse the placeholder outright."""
    grid = CorrectionGrid(CorrectionTable.read(path))
    if grid.is_placeholder:
        raise RuntimeError(
            f"{path} is the placeholder table: its corrections are the identity. "
            "Serving it would show a future artificially sunny by 8 to 11 points of "
            "cloud cover, on which three of the five sky classes depend. Run "
            "scripts/calibration_grid/build.py to produce the real table."
        )
    return grid


@lru_cache(maxsize=1)
def get_grid() -> CorrectionGrid:
    """The table, resident. A few megabytes is what buys a stateless server."""
    return load_grid()


# Named so that a test can substitute its own table through
# ``app.dependency_overrides[get_grid]`` without ever reading the shipped file.
Grid = Annotated[CorrectionGrid, Depends(get_grid)]


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_grid()  # fail at boot rather than on the first visitor
    yield


app = FastAPI(
    title="Weather Simulator",
    summary="Météo journalière plausible de 1950 à 2050, à partir de réanalyses "
    "et d'une projection climatique. Ce n'est pas une prévision.",
    lifespan=lifespan,
)


# --- what the interface needs to know before asking anything -----------------


class Config(BaseModel):
    """Constants the interface shares with the API, served rather than copied."""

    geocoding_url: str
    coverage_start: str
    coverage_end: str
    max_days: int
    temperature_band_edges: list[float]
    temperature_band_step: float


@app.get("/api/config", response_model=Config)
def config() -> Config:
    """The bounds and the geocoding address, so the browser holds no Open-Meteo
    knowledge of its own and applies the same limits the API does.

    The band boundaries are here for the same reason the ninety-day limit is: a
    chart drawn in the browser has to graduate its temperature axis on them, and
    a ladder written out a second time in JavaScript is the duplication rule 3 is
    about. What travels is the scale, not the colours — those stay in the
    stylesheet, exactly as the pictogram does, so repainting the ramp still
    touches one file.
    """
    return Config(
        geocoding_url=openmeteo.GEOCODING_URL,
        coverage_start=openmeteo.COVERAGE_START.isoformat(),
        coverage_end=openmeteo.COVERAGE_END.isoformat(),
        max_days=validation.MAX_DAYS,
        temperature_band_edges=list(thresholds.TEMPERATURE_BAND_EDGES),
        temperature_band_step=thresholds.TEMPERATURE_BAND_STEP_C,
    )


# --- the two halves of a search ----------------------------------------------


class PlannedRequest(BaseModel):
    """One call for the browser to make. It reads neither field, it just fetches."""

    id: str
    url: str


class PlanOut(BaseModel):
    today: str
    requests: list[PlannedRequest]


@app.post("/api/plan", response_model=PlanOut)
def plan(search: validation.Search, grid: Grid) -> PlanOut:
    """Validate a search, then say exactly what to fetch for it.

    The refusal for an uncovered place happens here rather than after the fact,
    so a visitor does not spend their own Open-Meteo quota on a search that was
    never going to be answered.
    """
    today = today_in_reference_zone()
    validation.refuse_uncovered(search, today, grid)

    built = planning.build(search.latitude, search.longitude, search.start, search.end, today)
    return PlanOut(
        today=today.isoformat(),
        requests=[PlannedRequest(id=s.id, url=s.url) for s in built.segments],
    )


@app.post("/api/days", response_model=Series)
def days(fetched: validation.Fetched, grid: Grid) -> Series:
    """Turn the fetched payloads into the daily series the interface displays.

    The plan is rebuilt here rather than remembered — the server keeps no state
    between the two calls — and the payloads are checked against it, so a body
    that does not match the search is refused instead of being read for whatever
    it happens to contain.
    """
    if abs((today_in_reference_zone() - fetched.today).days) > 1:
        raise errors.StalePlan(fetched.today, today_in_reference_zone())

    validation.refuse_uncovered(fetched, fetched.today, grid)
    built = planning.build(
        fetched.latitude, fetched.longitude, fetched.start, fetched.end, fetched.today
    )
    if set(fetched.payloads) != built.ids:
        raise errors.PayloadMismatch(built.ids, set(fetched.payloads))

    records = planning.assemble(built, fetched.payloads)
    simulated = any(segment.id == planning.PROJECTION for segment in built.segments)
    correction = grid.correction_at(fetched.latitude, fetched.longitude) if simulated else None

    return pipeline.run(
        records,
        latitude=fetched.latitude,
        longitude=fetched.longitude,
        correction=correction,
        metadata=grid.table.metadata if simulated else None,
    )


# --- the two pages, and the files they load ----------------------------------
#
# Mounted only when ``web/`` sits next to the package. docs/application.md plans
# for a static frontend served by a CDN, so the API has to start without it —
# and an installed wheel carries the package alone. Nothing here is dynamic: the
# two pages are files, and everything they show is fetched by the browser.


# Ask before reusing. Not "do not store" — the copy is kept, and a file that has
# not moved comes back as a 304 of a few bytes.
#
# It is the right setting as long as the URLs carry no version: without it
# Starlette sends an ETag and a Last-Modified but no instruction, so the browser
# falls back on a heuristic of its own and may reuse a module without ever
# asking. That is invisible in production, where nothing changes between two
# visits, and maddening while working on the interface — an edited stylesheet
# that simply does not arrive.
#
# The day docs/application.md puts these files behind a CDN, the answer changes
# shape rather than value: fingerprinted URLs get a year of immutable caching,
# and the two pages pointing at them keep this.
REVALIDATE = {"cache-control": "no-cache"}


class RevalidatedStatic(StaticFiles):
    """``StaticFiles``, minus the guessing.

    ``file_response`` is overridden through ``*args`` rather than by repeating
    its parameters: it is Starlette's internal seam, its signature has moved
    between versions, and this needs none of it.
    """

    def file_response(self, *args: object, **kwargs: object) -> Response:
        response = super().file_response(*args, **kwargs)
        response.headers.update(REVALIDATE)
        return response


def mount_web(target: FastAPI, directory: Path = WEB) -> bool:
    """Serve the two pages and their files, when there are any to serve.

    Says whether it mounted anything, so the absent case is a thing a test can
    assert rather than a silent branch.
    """
    if not directory.is_dir():
        return False

    target.mount("/static", RevalidatedStatic(directory=directory / "static"), name="static")

    @target.get("/", include_in_schema=False)
    def home() -> FileResponse:
        """The form: a place, two dates."""
        return FileResponse(directory / "pages" / "home.html", headers=REVALIDATE)

    @target.get("/resultats", include_in_schema=False)
    def results() -> FileResponse:
        """The band of days. The search travels in the query string, so the URL
        can be shared and the back button works without a line of script."""
        return FileResponse(directory / "pages" / "results.html", headers=REVALIDATE)

    return True


mount_web(app)


# --- how a refusal reaches the visitor ---------------------------------------


def _refusal(error: errors.ApiError) -> JSONResponse:
    return JSONResponse(status_code=error.status_code, content={"message": error.message})


@app.exception_handler(errors.ApiError)
def _api_error(request: Request, error: errors.ApiError) -> JSONResponse:
    return _refusal(error)


@app.exception_handler(RequestValidationError)
def _malformed(request: Request, error: RequestValidationError) -> JSONResponse:
    """A body that is not the right shape at all — a bad latitude, a missing field.

    Distinct from the refusals above, which are searches that make sense and
    cannot be served. This one only happens if the interface sends something it
    should not have, so the visitor gets one sentence and the technical detail
    travels alongside for the log.
    """
    return JSONResponse(
        status_code=422,
        content={
            "message": "Recherche invalide : la localisation ou les dates sont mal formées.",
            "detail": jsonable_encoder(error.errors()),
        },
    )


@app.exception_handler(OutsideCoverage)
def _outside_coverage(request: Request, error: OutsideCoverage) -> JSONResponse:
    """The grid refusing a point that got past the check — belt and braces."""
    return _refusal(errors.OutOfGrid(error.latitude, error.longitude))


@app.exception_handler(SourceError)
def _source_error(request: Request, error: SourceError) -> JSONResponse:
    """A payload that is not what it claims to be. The status code said nothing."""
    return JSONResponse(
        status_code=502,
        content={
            "message": "Les données reçues d'Open-Meteo sont incomplètes. "
            "Aucun résultat n'est affiché plutôt qu'un résultat partiel."
        },
    )
