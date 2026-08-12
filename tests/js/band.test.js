/**
 * The strip: what it shows, and where it puts its two reading marks.
 *
 * These are the rules that live in the interface rather than on the server —
 * the seam, the month markers, the card for a day without a sky class — so a
 * document is the only other thing holding them. Here they are executable.
 */

import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { byClass, install, reads, textOf, walk } from "./dom-stub.js";

// Before the import, not after: `el` reaches for the global on its first call.
install();

const { card, sources, strip } = await import("../../web/static/js/band.js");
const { texts } = await import("../../web/static/js/i18n.js");

/** A day of the series, as /api/days serves one. */
function day(date, origin, extra = {}) {
  return {
    date,
    origin,
    source: origin === "simulated" ? "MRI_AGCM3_2_S" : "era5",
    temperature_min: 14.2,
    temperature_max: 27.6,
    precipitation: 0.44,
    cloud_cover: 22.4,
    wind_speed_mean: 8.4,
    wind_speed_max: 18.7,
    sky: "clear",
    ...extra,
  };
}

describe("the daily card", () => {
  const only = card(day("2046-07-14", "simulated"), true);

  it("carries the four measures, each one named", () => {
    // What a screen reader gets, in order — so each number arrives with a word.
    assert.equal(
      reads(only).replace(/\s+/g, " "),
      "juillet samedi 14 Minimale 14 Maximale 28 °C Dégagé " +
        "Précipitations 0,4 mm Vent maximal 19 km/h",
    );
  });

  it("carries one wind, the maximum, and never a gust", () => {
    const spoken = reads(only);
    assert.match(spoken, /Vent maximal/);
    assert.doesNotMatch(spoken, /Vent moyen/);
    assert.doesNotMatch(spoken, /rafale/i);
  });

  it("doubles the pictogram with a written equivalent", () => {
    assert.equal(textOf(only, "card-emoji"), "☀️");
    assert.equal(textOf(only, "card-sky"), "Dégagé");
    // The emoji is hidden from screen readers; the written class is not.
    assert.equal(byClass(only, "card-emoji")[0].attrs["aria-hidden"], "true");
    assert.match(reads(only), /Dégagé/);
  });

  it("carries its source as an attribute, for diagnosing the seams", () => {
    assert.equal(only.attrs.title, "MRI_AGCM3_2_S");
  });
});

describe("a day with gaps", () => {
  const holed = card(
    day("2046-07-14", "observed", {
      temperature_max: null,
      precipitation: null,
      wind_speed_max: null,
      sky: null,
    }),
    false,
  );

  it("shows a dash, never NaN or undefined", () => {
    const spoken = reads(holed);
    assert.doesNotMatch(spoken, /NaN|undefined|null/);
    assert.match(spoken, /—/);
  });

  it("says 'data missing' to anyone who cannot see the dash", () => {
    const labelled = walk(holed).filter(
      (node) => node.attrs["aria-label"] === texts.measure.missingLabel,
    );
    assert.equal(labelled.length, 3);
  });

  it("with no sky class, a label and no invented pictogram", () => {
    assert.equal(textOf(holed, "card-emoji"), "");
    assert.equal(textOf(holed, "card-sky"), "Ciel indéterminé");
  });
});

describe("the seam", () => {
  const days = [
    day("2026-08-06", "observed"),
    day("2026-08-07", "observed"),
    day("2026-08-08", "simulated"),
    day("2026-08-09", "simulated"),
  ];

  it("is marked once, right before the first simulated day", () => {
    const nodes = strip(days);
    const seams = nodes.filter((node) => node.className === "seam");
    assert.equal(seams.length, 1);
    assert.equal(nodes.indexOf(seams[0]), 2);
    assert.equal(nodes[3].className, "card card--simulated");
  });

  it("is written, not only tinted", () => {
    // Colour alone must never be what carries the information.
    const [seam] = strip(days).filter((node) => node.className === "seam");
    assert.match(reads(seam), /À partir d'ici, simulation/);
  });

  it("does not appear on a range lying wholly in the past", () => {
    const past = strip([day("2024-06-01", "observed"), day("2024-06-02", "observed")]);
    assert.equal(past.filter((node) => node.className === "seam").length, 0);
  });

  it("nor on a range lying wholly in the model", () => {
    // No bank to leave: a marker on the very first card would announce a
    // passage that never happens. The warning at the top covers that case.
    const future = strip([day("2046-07-01", "simulated"), day("2046-07-02", "simulated")]);
    assert.equal(future.filter((node) => node.className === "seam").length, 0);
  });

  it("falls at the end of the forecast, not at tonight", () => {
    // The whole point of the IFS segment: tomorrow is weather, and the crossing
    // belongs where forecasting stops rather than where the calendar turns.
    const nodes = strip([
      day("2026-08-11", "observed"),
      day("2026-08-12", "forecast"),
      day("2026-08-13", "forecast"),
      day("2026-08-14", "simulated"),
    ]);
    const seams = nodes.filter((node) => node.className === "seam");
    assert.equal(seams.length, 1);
    assert.equal(nodes.indexOf(seams[0]), 3);
  });

  it("is still marked on a range that starts tomorrow", () => {
    // Forecast then simulated, never observed. Reading "observed" alone to
    // decide there was a bank to leave would let this crossing go unmarked.
    const nodes = strip([
      day("2026-08-12", "forecast"),
      day("2026-08-13", "forecast"),
      day("2026-08-14", "simulated"),
    ]);
    assert.equal(nodes.filter((node) => node.className === "seam").length, 1);
  });

  it("does not appear on a range that never leaves the forecast", () => {
    const ahead = strip([day("2026-08-12", "forecast"), day("2026-08-13", "forecast")]);
    assert.equal(ahead.filter((node) => node.className === "seam").length, 0);
  });
});

describe("the month marker", () => {
  it("names the month only where it turns", () => {
    const nodes = strip([
      day("2046-07-30", "observed"),
      day("2046-07-31", "observed"),
      day("2046-08-01", "observed"),
    ]);
    assert.deepEqual(
      nodes.map((node) => textOf(node, "card-month")),
      ["juillet", "", "août"],
    );
  });

  it("names the month on the first card, whatever happens", () => {
    const [first] = strip([day("2046-07-31", "observed")]);
    assert.equal(textOf(first, "card-month"), "juillet");
  });
});

describe("where the days come from", () => {
  const grid = {
    model: "MRI_AGCM3_2_S",
    calibration_start: "1985-01-01",
    calibration_end: "2014-12-31",
    projection_start: "2021-01-01",
    projection_end: "2050-12-31",
    step: 0.5,
    generated: "2026-08-04",
  };

  it("gives the model, the periods, the step and the generation date", () => {
    const said = sources(grid).map((node) => node.textContent);
    assert.deepEqual(said, [
      "Modèle climatique",
      "MRI_AGCM3_2_S",
      "Période de calibration",
      "1 janvier 1985 – 31 décembre 2014",
      "Période de projection",
      "1 janvier 2021 – 31 décembre 2050",
      "Pas de la grille",
      "0,5°",
      "Table de correction générée le",
      "4 août 2026",
    ]);
  });

  it("says nothing when nothing was corrected", () => {
    assert.deepEqual(sources(null), []);
  });
});
