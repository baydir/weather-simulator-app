"""The JSON contract: one object per day, and what travels alongside them.

Stable and documented on purpose. docs/application.md asks for it so that a
chart, a running total or a map can branch onto this later without touching the
pipeline — which means the shape here is a commitment, not an implementation
detail.

Three things it carries and three it refuses to.

**It carries the class, never the pictogram.** ``sky`` is one of five words, and
the emoji lives on the display side alone, so that moving to a drawn icon set
touches nothing but the rendering.

**It carries ``origin`` on every day, and ``has_simulated`` on the response.**
The interface must warn on any future date, and it derives nothing — so the
question "is a warning due here" is answered on the server and shipped as a
boolean rather than left to be worked out from the days.

**It carries the grid's own metadata.** A corrected series read without knowing
which model was corrected, over which calibration period, and when the table was
generated is a silent source of error. It is null when nothing was corrected,
which is the honest answer for a range lying entirely in the past.

**It omits ``temperature_mean``.** Requested from all four sources, but only
because the snow criterion rests on it — docs/donnees.md is explicit that it is
not displayed, and shipping it would invite it onto a card.

**It omits ``snowfall``.** Kept in the record as a witness, but the climate model
serves it in patches, so it exists on one side of the seam and not the other.
Carrying it would be an invitation to read it.

**It omits the pictogram and any intensity grading.** Daily totals do not carry
what a grading would need; a drizzle and a forty-millimetre storm get the same
class, and docs/regles.md accepts that rather than inventing a difference.

Units follow Open-Meteo and are not normalised: degrees Celsius, millimetres,
percent, kilometres per hour. They are attached to each field below rather than
repeated in every response.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field

from weather_simulator.calibration.table import Metadata
from weather_simulator.domain.records import DailyRecord, Origin
from weather_simulator.domain.sky import SkyClass


class Day(BaseModel):
    """One day of the homogeneous series, ready to display.

    Every measured field is nullable. A source may legitimately return nothing
    for a day, and substituting a value would be a data-treatment decision made
    in passing — so the gap travels as ``null`` and the interface faces it.
    """

    date: date
    origin: Origin = Field(
        description="observed for a reanalysis day, simulated for a projected one"
    )
    source: str = Field(description="Which dataset served the day. For diagnosing the seams.")

    temperature_min: float | None = Field(default=None, description="degrees Celsius")
    temperature_max: float | None = Field(default=None, description="degrees Celsius")
    precipitation: float | None = Field(
        default=None, description="millimetres, all phases together"
    )
    cloud_cover: float | None = Field(
        default=None,
        description=(
            "percent, daily mean. Corrected on simulated days, raw on observed ones. "
            "Shipped because it is what the sky class turns on."
        ),
    )
    wind_speed_mean: float | None = Field(default=None, description="km/h")
    wind_speed_max: float | None = Field(
        default=None,
        description=(
            "km/h. The strongest *sustained* wind of the day, not a gust — a gust "
            "commonly runs to twice this. Never label it 'rafale'."
        ),
    )

    sky: SkyClass | None = Field(
        default=None,
        description=(
            "clear, cloudy, overcast, rain or snow — or null when a variable the "
            "rule needs is missing. The interface must have a card for that."
        ),
    )

    @classmethod
    def from_record(cls, record: DailyRecord, sky: SkyClass | None) -> Day:
        """Ship one day. ``sky`` is passed in, already decided on the full values.

        Cloud cover is rounded to a tenth on the way out, and on the way out
        only. Interpolating four nodes leaves a value like 20.12553949937517,
        which claims a precision the table does not have — it stores tenths.
        The rounding happens after the class has been decided, deliberately: a
        day at 29.97 % must not become cloudy because it was tidied up.
        """
        return cls(
            date=record.date,
            origin=record.origin,
            source=record.source or "",
            temperature_min=record.temperature_min,
            temperature_max=record.temperature_max,
            precipitation=record.precipitation,
            cloud_cover=None if record.cloud_cover is None else round(record.cloud_cover, 1),
            wind_speed_mean=record.wind_speed_mean,
            wind_speed_max=record.wind_speed_max,
            sky=sky,
        )


class Grid(BaseModel):
    """What corrected the simulated days, so the reader can judge the series."""

    model: str = Field(description="The climate model the table corrects")
    calibration_start: date
    calibration_end: date
    projection_start: date
    projection_end: date
    step: float = Field(description="Spacing of the lattice, in degrees")
    generated: date = Field(description="When the table was built")

    @classmethod
    def from_metadata(cls, metadata: Metadata) -> Grid:
        return cls(
            model=metadata.model,
            calibration_start=metadata.calibration_start,
            calibration_end=metadata.calibration_end,
            projection_start=metadata.projection_start,
            projection_end=metadata.projection_end,
            step=metadata.step,
            generated=metadata.generated,
        )


class Series(BaseModel):
    """The answer to one search."""

    latitude: float
    longitude: float
    start: date
    end: date
    has_simulated: bool = Field(
        description=(
            "True when at least one day is a projection. The interface must then "
            "show the warning of docs/projet.md. Shipped rather than derived."
        )
    )
    grid: Grid | None = Field(
        default=None,
        description="The correction applied to the simulated days. Null when there are none.",
    )
    days: list[Day]
