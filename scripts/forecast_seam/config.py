"""What the forecast seam is measured on, and over which days.

**The junction under test.** The recent past comes from ECMWF IFS on the archive
endpoint (``ecmwf_ifs``, ~9 km, an analysis); the fortnight ahead comes from IFS
on the forecast endpoint (``ecmwf_ifs025``, 0.25°, an integration forward). Same
centre, same system, two different products. If they disagree at the changeover,
the series gains a step where it claims to have none.

**Sites — the ten of step 2, deliberately.** Reused rather than redefined so a
figure here can be set beside a figure there without wondering whether the points
moved. They are imported, not copied: one fact, one file.

**Period — the last ninety-two days.** Not a choice, a ceiling: the forecast
endpoint serves no further back than that. One run therefore measures one season,
and a spread over the year needs runs spaced over the year. Saying so is part of
the result — the alternative is a figure that looks annual and is not.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path


def _sites() -> dict[str, tuple[float, float]]:
    """The ten sites of step 2, loaded from where they are defined.

    By path rather than by ``sys.path``: both folders name their settings file
    ``config.py``, so an import would resolve to whichever came first — most
    likely this one, importing itself.
    """
    source = Path(__file__).resolve().parents[1] / "model_selection" / "config.py"
    spec = importlib.util.spec_from_file_location("model_selection_config", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.SITES


SITES = _sites()

CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / "forecast_seam"

# The furthest back the forecast endpoint reaches. Beyond it the archive is the
# only source, and there is no junction left to measure.
PAST_DAYS = 92

# What the seam is read on. Cloud cover leads: three of the five sky classes turn
# on it, and it is the variable the whole correction grid exists to repair.
FIELDS = (
    ("cloud_cover", "nébulosité", "%"),
    ("temperature_max", "Tmax", "°C"),
    ("temperature_min", "Tmin", "°C"),
    ("temperature_mean", "Tmoy", "°C"),
    ("precipitation", "précipitations", "mm"),
    ("wind_speed_max", "vent max", "km/h"),
    ("wind_speed_mean", "vent moyen", "km/h"),
)
