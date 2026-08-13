"""Measure the contrast of every text on the results page, on each of its grounds.

Nothing here asserts. It prints the table `docs/application.md` publishes, one
column per season, so that a palette which moves is re-measured by a command
rather than by hand — four seasons of twelve lines is not a thing anyone checks
twice with an eyedropper.

**Where each number comes from.** The *positions* are read off a real render:
the page is served, driven by a real Chromium and asked where each element
actually sits and what colour it computes to. The *ground* is then worked out
from the gradient itself — the stops are read back from the stylesheet through
``getComputedStyle``, never copied into this file, and interpolated in sRGB,
which is what the browser does with a plain ``linear-gradient`` of opaque
colours. So the two halves of every ratio come from the page: one measured on
the render, the other from the declaration that painted it.

That is also the check on the method: run it on summer and the numbers must come
back as docs/application.md already publishes them.

**One geometry, four palettes.** The page measured is the ``results`` view —
ten days back and forty ahead, which is what puts a warning at the top and a
seam in the middle — and the season is then forced on the body, four times over.
Not a trick: a range crossing today in January *is* a winter page with a warning
and a seam. It is the only way to compare four grounds on the same page, since
which season a real crossing lands on depends on the day the script is run.

**A text on a card is measured against the card**, not against the sky behind
it. The cards are opaque and the two temperatures live on them — that is why
those two are the same on all four seasons.

**It needs a browser, and by default the network too.** ``--offline`` answers
Open-Meteo from this process, exactly as ``screenshots.py`` does — the ground and
the geometry are what is being measured here, and both are the real thing
whether the weather behind them is invented or not.

    ./venv/bin/python scripts/ink_contrast.py --offline
    ./venv/bin/python scripts/ink_contrast.py --offline --season winter
    ./venv/bin/python scripts/ink_contrast.py --offline --size 1280x720
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from playwright.sync_api import sync_playwright  # noqa: E402
from screenshots import (  # noqa: E402
    SEASON_RANGES,
    free_port,
    results,
    serve,
    stub_openmeteo,
)

# The rows of the published table, in its order. The label is French because it
# is what the table prints; the selector is what the page calls the thing.
ROWS = [
    ("le lieu", "#place"),
    ("la plage", "#range"),
    ("nouvelle recherche", "header.banner a"),
    ("l'avertissement", "#warning p:first-of-type"),
    ("le scénario", "#warning p:last-of-type"),
    ("le mois", ".card-month"),
    ("le jour", ".card-day"),
    ("la maximale", ".card-degrees.high .value"),
    ("la minimale", ".card-degrees.low .value"),
    ("les deux mesures", ".card-measure"),
    ("la couture", ".seam span"),
    ("la provenance", ".provenance summary"),
]

# What each element sits on. Anything inside a card body is on the card, which is
# opaque; everything else is on the sky, at its own height.
ON_THE_CARD = ".card-body"


def channel(value: float) -> float:
    value /= 255
    return value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4


def luminance(colour: tuple[float, float, float]) -> float:
    red, green, blue = (channel(c) for c in colour)
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def ratio(one, other) -> float:
    first, second = luminance(one), luminance(other)
    high, low = max(first, second), min(first, second)
    return (high + 0.05) / (low + 0.05)


def over(ink, ground):
    """A translucent ink on its ground, as the compositor lays it.

    The provenance is written at 72 % white and the rule above it at 30 %, so
    reading their colour and stopping there would report the contrast of a white
    that is not on the page. It is what the ratio is *for*: the colour the eye
    actually receives.
    """
    colour, alpha = ink
    return tuple(colour[i] * alpha + ground[i] * (1 - alpha) for i in range(3))


def parse_colour(text: str):
    """ "#rrggbb", "rgb(r, g, b)" or "rgba(r, g, b, a)" — what the page hands back.

    Returns the three channels and the alpha separately: the alpha has a ground
    to be laid on before it means anything.
    """
    if text.startswith("#"):
        digits = text[1:]
        return tuple(int(digits[i : i + 2], 16) for i in (0, 2, 4)), 1.0
    numbers = [float(n) for n in re.findall(r"[\d.]+", text)]
    return tuple(numbers[:3]), numbers[3] if len(numbers) > 3 else 1.0


def parse_stops(gradient: str) -> list[tuple[float, tuple[float, float, float]]]:
    """The stops of a `linear-gradient(to bottom, …)`, as read from the page.

    A custom property comes back as its token stream with every ``var()``
    already substituted — so the stop written as ``var(--sky-head)`` arrives
    here as the colour it stands for, which is the point of asking the browser
    rather than reading the file. The tokens themselves are untouched, hence the
    two spellings.
    """
    found = re.findall(r"(#[0-9a-fA-F]{3,8}|rgba?\([^)]*\))\s+([\d.]+)%", gradient)
    if not found:
        raise SystemExit(f"no stops read in this gradient:\n{gradient}")
    return [(float(percent), parse_colour(colour)[0]) for colour, percent in found]


def ground_at(stops, fraction: float) -> tuple[float, float, float]:
    """The gradient's colour at a fraction of its height, interpolated in sRGB."""
    percent = max(0.0, min(100.0, fraction * 100))
    for (low, first), (high, second) in zip(stops, stops[1:], strict=False):
        if low <= percent <= high:
            share = 0.0 if high == low else (percent - low) / (high - low)
            return tuple(first[i] + (second[i] - first[i]) * share for i in range(3))
    return stops[-1][1]


# Read in the page: where every row sits, what colour it is, and what the sky is
# made of. One round trip rather than twelve, and no selector resolved twice.
#
# A row with no box is left out rather than reported at the top of the page: an
# element that is `hidden` measures zero everywhere, and a zero divided by the
# page height is a perfectly plausible-looking 0 %, near-white, flattering and
# false.
PROBE = """
([rows, onTheCard]) => {
  const body = document.body;
  const sky = document.querySelector('.sky');
  const seen = [];
  for (const [label, selector] of rows) {
    const node = document.querySelector(selector);
    if (!node) continue;
    const box = node.getBoundingClientRect();
    if (box.height === 0) continue;
    const card = node.closest(onTheCard);
    seen.push({
      label,
      colour: getComputedStyle(node).color,
      middle: (box.top + window.scrollY + box.height / 2) / sky.offsetHeight,
      card: card ? getComputedStyle(card).backgroundColor : null,
    });
  }
  return {
    season: body.dataset.season,
    height: sky.offsetHeight,
    gradient: getComputedStyle(body).getPropertyValue('--sky'),
    rows: seen,
  };
}
"""


# The temperature ramp, read the same way: the browser resolves each band class
# to a colour, and the two card papers are read off a real card. Asking the page
# rather than the file is what keeps this from becoming a second copy of the
# ramp — the numbers here come from whatever the stylesheet currently says.
RAMP_PROBE = """
(count) => {
  const card = document.querySelector('.card-body');
  const probe = document.createElement('span');
  probe.className = 'card-degrees';
  card.append(probe);
  const bands = [];
  for (let i = 0; i < count; i++) {
    probe.setAttribute('data-band', String(i));
    const style = getComputedStyle(probe);
    bands.push({ ground: style.backgroundColor, ink: style.color });
  }
  probe.remove();
  return bands;
}
"""

BAND_COUNT = 9


def measure_ramp(page) -> list[tuple[int, str, str, float]]:
    """Every band of the temperature scale, under the ink it actually carries.

    The number sits *on* the band, so the ratio that matters is the ink against
    its own ground — the card behind it never shows through. The ink is read
    rather than assumed: it turns over with the ground, white on the dark bands
    and near-black on the light ones, and reading it here is what keeps this
    from being a second opinion about which is which.
    """
    rows = []
    for index, band in enumerate(page.evaluate(RAMP_PROBE, BAND_COUNT)):
        ground = parse_colour(band["ground"])[0]
        ink = parse_colour(band["ink"])
        as_hex = lambda colour: "#" + "".join(f"{round(c):02x}" for c in colour)  # noqa: E731
        rows.append((index, as_hex(ground), as_hex(ink[0]), ratio(over(ink, ground), ground)))
    return rows


def measure(page, season: str) -> dict:
    """The page as it stands, repainted in one season and read."""
    page.evaluate("(season) => { document.body.dataset.season = season; }", season)
    read = page.evaluate(PROBE, [ROWS, ON_THE_CARD])

    stops = parse_stops(read["gradient"])
    measured = {}
    for row in read["rows"]:
        ground = parse_colour(row["card"])[0] if row["card"] else ground_at(stops, row["middle"])
        measured[row["label"]] = ratio(over(parse_colour(row["colour"]), ground), ground)
    return {"height": read["height"], "rows": measured}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--season", choices=sorted(SEASON_RANGES), help="one of the four")
    parser.add_argument("--size", default="1440x960", help="the window, as WIDTHxHEIGHT")
    parser.add_argument(
        "--offline",
        action="store_true",
        help="inventer les données au lieu d'appeler Open-Meteo — les positions restent vraies",
    )
    parser.add_argument("--lag", type=int, default=6, help="retard des réanalyses, avec --offline")
    chosen = parser.parse_args()

    width, _, height = chosen.size.partition("x")
    size = {"width": int(width), "height": int(height)}
    wanted = [chosen.season] if chosen.season else list(SEASON_RANGES)

    port = free_port()
    server = serve(port)
    base = f"http://127.0.0.1:{port}"
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(args=["--lang=fr-FR"])
            context = browser.new_context(viewport=size, locale="fr-FR")
            page = context.new_page()
            if chosen.offline:
                stub_openmeteo(page, date.today(), chosen.lag)
            # The reference geometry, and the same call the screenshots make: a
            # range spanning today, so the warning and the seam are both there.
            results(page, base)
            measured = {season: measure(page, season) for season in wanted}
            ramp = measure_ramp(page)
            browser.close()
    finally:
        server.terminate()

    heights = {reading["height"] for reading in measured.values()}
    print(f"\nfenêtre {size['width']} × {size['height']}, page {max(heights)} px")
    print("\n| Texte | " + " | ".join(wanted) + " |")
    print("|---|" + "---|" * len(wanted))
    floor = (None, 99.0)
    for label, _ in ROWS:
        cells = []
        for season in wanted:
            value = measured[season]["rows"].get(label)
            cells.append("—" if value is None else f"{value:.1f}:1".replace(".", ","))
            if value is not None and value < floor[1]:
                floor = (f"{label}, {season}", value)
        print(f"| {label} | " + " | ".join(cells) + " |")
    print(f"\nplancher : {floor[0]}, à {floor[1]:.1f}:1".replace(".", ","))

    # The two temperatures are no longer one colour each, so they cannot be one
    # row each: what has to hold is the whole ramp, on both papers a card takes.
    print("\nLa rampe des températures : le chiffre sur son aplat\n")
    print("| bande | aplat | encre | chiffre |")
    print("|---|---|---|---|")
    for index, hexa, ink, on_band in ramp:
        print(f"| {index} | `{hexa}` | `{ink}` | {on_band:.2f}:1 |".replace(".", ","))
    print(f"\nplancher de la rampe : {min(r[3] for r in ramp):.2f}:1".replace(".", ","))


if __name__ == "__main__":
    main()
