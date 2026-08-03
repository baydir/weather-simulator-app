"""What the sky classes actually deliver, and why the obvious yardsticks fail.

    python scripts/sky_thresholds/calibrate.py

Establishes the figures of the *Classe de ciel* section of CLAUDE.md. Fetches
once into ``data/sky_thresholds/`` and never again; the analysis re-runs offline.

The question this answers is narrow, because it is the only one measurement can
answer. Where "nuageux" ends and "couvert" begins is a convention of language
over a continuum — no measurement settles it. What measurement can say is what
each class *delivers*: how much daylight reaches the ground on the days a given
threshold captures. That is the anchor the thresholds were missing.

Two candidate yardsticks were tried first and both are traps, which is why this
script reports them rather than merely avoiding them.

``sunshine_duration`` overstates real sunshine by a third to a factor of two,
and the error grows with cloudiness — the signature of a threshold applied to
hourly means, where an hour counts whole as soon as its average crosses the bar.
A heliograph counts the minutes.

``weather_code`` is the daily *maximum* of 24 hourly codes, so one hour at 80 %
cloud makes the whole day overcast. It calls half of Marseille's dry days
overcast. It is also circular: a deterministic function of the very variable
whose thresholds are sought.

What is left is ``shortwave_radiation_sum`` — a primary ERA5 field, not a
derivation, whose annual totals match published values, and which every one of
the three sources serves. Divided by a clear-sky estimate it gives the fraction
of available light a day received, comparable between Brest and Bamako.
"""

from __future__ import annotations

import json
import math
import statistics as st
import time
from datetime import date
from pathlib import Path

from weather_simulator.domain import thresholds as T
from weather_simulator.sources import openmeteo
from weather_simulator.sources.client import get_json
from weather_simulator.sources.errors import FetchError

CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / "sky_thresholds"
START, END = date(2005, 1, 1), date(2014, 12, 31)

VARIABLES = [
    "cloud_cover_mean",
    "precipitation_sum",
    "shortwave_radiation_sum",
    "temperature_2m_max",
    "temperature_2m_min",
    "sunshine_duration",
    "daylight_duration",
]

# The sites of the step 2 comparison, so that the two rest on the same ground.
SITES: dict[str, tuple[float, float]] = {
    "brest": (48.39, -4.49),
    "marseille": (43.30, 5.37),
    "strasbourg": (48.58, 7.75),
    "pontarlier": (46.90, 6.35),
    "chamonix": (45.92, 6.87),
    "reykjavik": (64.15, -21.94),
    "bamako": (12.65, -8.00),
    "singapore": (1.35, 103.82),
    "christchurch": (-43.53, 172.63),
    "ushuaia": (-54.80, -68.30),
}

# Published sunshine normals, hours per year — the yardstick's yardstick. Orders
# of magnitude from national services, quoted to show a factor, not a decimal.
NORMALS = {"brest": 1700, "marseille": 2860, "strasbourg": 1690, "pontarlier": 1900}

CANDIDATES = ((30.0, 70.0), (30.0, 80.0), (25.0, 85.0))


def fetch(site: str, latitude: float, longitude: float) -> dict:
    """One request per site, cached. ERA5 forced, never the default endpoint."""
    target = CACHE_DIR / f"{site}.json"
    if target.exists():
        return json.loads(target.read_text(encoding="utf-8"))

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": START.isoformat(),
        "end_date": END.isoformat(),
        "daily": VARIABLES,
        "models": [openmeteo.SURFACE_MODEL],
        "timezone": openmeteo.DEFAULT_TIMEZONE,
    }
    payload = get_json(openmeteo.ARCHIVE_URL, params, retries=5, backoff=300)
    target.write_text(json.dumps(payload), encoding="utf-8")
    time.sleep(6)
    return payload


def clear_sky(latitude: float, elevation: float, day: date) -> float:
    """Daily clear-sky radiation, MJ/m2 — astronomy plus one altitude term.

    Extraterrestrial radiation is pure geometry (FAO-56), so it is identical in
    1950 and in 2050 and introduces no data dependency. The 0.75 is the share of
    it that a clear atmosphere passes at sea level; the altitude term raises that
    where there is less air to cross. Both APIs report the same elevation for a
    point, from the same terrain model.
    """
    phi = math.radians(latitude)
    j = day.timetuple().tm_yday
    distance = 1 + 0.033 * math.cos(2 * math.pi * j / 365)
    declination = 0.409 * math.sin(2 * math.pi * j / 365 - 1.39)
    # Clamped for the polar day and night, where the sun never sets or rises.
    sunset = math.acos(max(-1.0, min(1.0, -math.tan(phi) * math.tan(declination))))
    extraterrestrial = (
        (24 * 60 / math.pi)
        * 0.0820
        * distance
        * (
            sunset * math.sin(phi) * math.sin(declination)
            + math.cos(phi) * math.cos(declination) * math.sin(sunset)
        )
    )
    return (0.75 + 2e-5 * elevation) * extraterrestrial


def dry_days(payload: dict, latitude: float) -> list[dict]:
    """Days below the wet gate, with the light they received.

    Only dry days: the wet ones are already taken by the snow and rain classes,
    so the cloud thresholds partition these and nothing else.
    """
    daily = payload["daily"]
    elevation = payload["elevation"]
    rows = []
    for index, stamp in enumerate(daily["time"]):
        cloud = daily["cloud_cover_mean"][index]
        rain = daily["precipitation_sum"][index]
        radiation = daily["shortwave_radiation_sum"][index]
        if None in (cloud, rain, radiation) or rain >= T.PRECIPITATION_MM:
            continue
        day = date.fromisoformat(stamp)
        available = clear_sky(latitude, elevation, day)
        # Near the poles in winter there is no light to receive and the ratio is
        # meaningless. Reported rather than silently dropped: it is where the
        # sky class rests on nothing.
        if available < 1.0:
            continue
        high, low = daily["temperature_2m_max"][index], daily["temperature_2m_min"][index]
        rows.append(
            {
                "cloud": cloud,
                "light": 100 * radiation / available,
                "range": None if None in (high, low) else high - low,
            }
        )
    return rows


def _share_without_light(payload: dict, latitude: float) -> float:
    daily = payload["daily"]
    total = dark = 0
    for index, stamp in enumerate(daily["time"]):
        if daily["precipitation_sum"][index] is None:
            continue
        total += 1
        if clear_sky(latitude, payload["elevation"], date.fromisoformat(stamp)) < 1.0:
            dark += 1
    return 100 * dark / total if total else 0.0


def report_classes(data: dict[str, list[dict]]) -> None:
    print(f"\n{'=' * 78}\nCE QUE CHAQUE CLASSE RECOIT\n{'=' * 78}")
    print("\nPart des jours secs, et lumiere mediane recue en % du ciel clair.\n")
    for low, high in CANDIDATES:
        print(f"  seuils {low:.0f} / {high:.0f}")
        print(f"    {'site':<14}{'degage':>16}{'nuageux':>16}{'couvert':>16}")
        for site, rows in data.items():
            total = len(rows)
            cells = ""
            for floor, ceiling in ((0.0, low), (low, high), (high, 101.0)):
                picked = [r["light"] for r in rows if floor <= r["cloud"] < ceiling]
                cells += (
                    f"{100 * len(picked) / total:>8.0f}%{st.median(picked):>7.0f}%"
                    if len(picked) > 20
                    else f"{'--':>16}"
                )
            print(f"    {site:<14}{cells}")
        print()


def report_ambiguity(data: dict[str, list[dict]]) -> None:
    print(f"\n{'=' * 78}\nCE QUE LA MOYENNE JOURNALIERE NE PEUT PAS DIRE\n{'=' * 78}")
    print("\nA nebulosite egale, la lumiere recue s'etale : une matinee bouchee suivie")
    print("d'un apres-midi radieux porte la meme moyenne qu'une journee grise de bout en bout.\n")
    print(f"  {'site':<14}{'nebulosite':<12}{'n':>6}{'d1':>7}{'median':>8}{'d9':>7}{'etendue':>10}")

    def quantile(values: list[float], q: float) -> float:
        ordered = sorted(values)
        return ordered[min(int(q * len(ordered)), len(ordered) - 1)]

    for site, rows in data.items():
        for low, high in ((25, 35), (45, 55), (65, 75), (85, 95)):
            picked = [r["light"] for r in rows if low <= r["cloud"] < high]
            if len(picked) < 30:
                continue
            first, last = quantile(picked, 0.1), quantile(picked, 0.9)
            print(
                f"  {site:<14}{f'{low}-{high}%':<12}{len(picked):>6}{first:>7.0f}"
                f"{st.median(picked):>8.0f}{last:>7.0f}{last - first:>9.0f}pt"
            )
        print()


def report_traps(payloads: dict[str, dict]) -> None:
    print(f"\n{'=' * 78}\nLES DEUX ETALONS PIEGEUX\n{'=' * 78}")
    print("\nsunshine_duration contre les normales publiees, heures par an :\n")
    print(f"  {'site':<14}{'ERA5':>10}{'normale':>10}{'rapport':>10}")
    for site, normal in NORMALS.items():
        daily = payloads[site]["daily"]
        per_year: dict[int, float] = {}
        for stamp, seconds in zip(daily["time"], daily["sunshine_duration"], strict=True):
            if seconds is not None:
                year = date.fromisoformat(stamp).year
                per_year[year] = per_year.get(year, 0.0) + seconds / 3600
        measured = st.median(per_year.values())
        print(f"  {site:<14}{measured:>10.0f}{normal:>10}{measured / normal:>10.2f}")
    print("\n  L'erreur suit la nebulosite du site — signature d'un seuil applique")
    print("  a des moyennes horaires, ou l'heure compte entiere des que sa moyenne passe.")
    print("\n  weather_code : maximum des 24 codes horaires, donc une heure a 80 % de")
    print("  nebulosite suffit a couvrir la journee. Circulaire de surcroit — une")
    print("  fonction deterministe de la variable meme qu'on cherche a seuiller.")


def report_extra_variables(data: dict[str, list[dict]]) -> None:
    """How much of the ambiguity the other daily variables recover."""

    def r_squared(columns: list[list[float]], target: list[float]) -> float:
        design = [[1.0] * len(target)] + columns
        size = len(design)
        matrix = [
            [sum(design[i][r] * design[j][r] for r in range(len(target))) for j in range(size)]
            for i in range(size)
        ]
        vector = [sum(design[i][r] * target[r] for r in range(len(target))) for i in range(size)]
        for i in range(size):
            pivot = max(range(i, size), key=lambda r: abs(matrix[r][i]))
            matrix[i], matrix[pivot] = matrix[pivot], matrix[i]
            vector[i], vector[pivot] = vector[pivot], vector[i]
            if abs(matrix[i][i]) < 1e-12:
                return float("nan")
            for r in range(i + 1, size):
                factor = matrix[r][i] / matrix[i][i]
                for c in range(i, size):
                    matrix[r][c] -= factor * matrix[i][c]
                vector[r] -= factor * vector[i]
        beta = [0.0] * size
        for i in reversed(range(size)):
            beta[i] = (
                vector[i] - sum(matrix[i][j] * beta[j] for j in range(i + 1, size))
            ) / matrix[i][i]
        predicted = [sum(beta[j] * design[j][r] for j in range(size)) for r in range(len(target))]
        mean = st.mean(target)
        spread = sum((v - mean) ** 2 for v in target)
        return 1 - sum((target[r] - predicted[r]) ** 2 for r in range(len(target))) / spread

    print(f"\n{'=' * 78}\nCE QUE LES AUTRES VARIABLES RECUPERENT\n{'=' * 78}")
    print("\nVariance de la lumiere recue expliquee, jours secs.")
    print("L'amplitude thermique signe le ciel clair : le sol chauffe le jour et")
    print("rayonne la nuit sans couverture. Elle est servie sur les trois segments.\n")
    print(f"  {'site':<14}{'nebulosite':>13}{'+ amplitude':>14}{'gain':>9}")
    for site, rows in data.items():
        usable = [r for r in rows if r["range"] is not None]
        if len(usable) < 200:
            continue
        cloud = [r["cloud"] for r in usable]
        spread = [r["range"] for r in usable]
        light = [r["light"] for r in usable]
        alone, both = r_squared([cloud], light), r_squared([cloud, spread], light)
        print(f"  {site:<14}{alone:>13.3f}{both:>14.3f}{both - alone:>+9.3f}")


def main() -> int:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    payloads: dict[str, dict] = {}
    data: dict[str, list[dict]] = {}

    for site, (latitude, longitude) in SITES.items():
        try:
            payload = fetch(site, latitude, longitude)
        except FetchError as error:
            print(f"  {site}: {error}")
            continue
        payloads[site] = payload
        data[site] = dry_days(payload, latitude)

    if not data:
        return 1

    print(f"SEUILS DE CIEL — ERA5 force, {START}..{END}, {len(data)} sites")
    print(
        f"Seuils en vigueur : nuageux >= {T.CLOUDY_PERCENT:.0f} %, "
        f"couvert >= {T.OVERCAST_PERCENT:.0f} %, pluie >= {T.PRECIPITATION_MM} mm"
    )

    report_classes(data)
    report_ambiguity(data)
    report_traps(payloads)
    report_extra_variables(data)

    print(f"\n{'=' * 78}\nJOURS SANS LUMIERE DISPONIBLE\n{'=' * 78}\n")
    print("  Pres des poles en hiver le ciel clair tend vers zero et le rapport")
    print("  n'a plus de sens. La classe de ciel y repose sur la seule nebulosite.\n")
    for site, (latitude, _) in SITES.items():
        if site in payloads:
            share = _share_without_light(payloads[site], latitude)
            if share > 0:
                print(f"  {site:<14}{share:>6.1f}% des jours")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
