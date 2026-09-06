/**
 * The file the visitor takes away.
 *
 * Two things are checked here that nothing else can check: that every row says
 * what produced it, and that the numbers survive the trip. The first is
 * CLAUDE.md rule 1 applied to a file rather than a screen — a temperature that
 * leaves this page with no origin beside it can be read as a measurement for as
 * long as the file exists. The second is arithmetic on strings, which is what
 * this module is.
 */

import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { fileName, toCsv } from "../../web/static/js/csv.js";
import { texts } from "../../web/static/js/i18n.js";

/** A served day, with everything the file writes. */
function day(over = {}) {
  return {
    date: "2046-07-14",
    origin: "simulated",
    source: "MRI_AGCM3_2_S",
    temperature_min: 21.4,
    temperature_max: 39,
    precipitation: 0,
    cloud_cover: 12.5,
    wind_speed_mean: 9,
    wind_speed_max: 24.2,
    sky: "clear",
    ...over,
  };
}

const lines = (text) => text.split("\r\n");
const cells = (line) => line.split(";");

describe("the days as a file", () => {
  it("opens on the header the dictionary declares", () => {
    assert.deepEqual(cells(lines(toCsv([day()]))[0]), texts.export.columns());
  });

  it("borrows the two labels the page already fixes", () => {
    // `docs/application.md` settles that the strongest sustained wind is
    // labelled "vent maximal" and never "vent": written out a second time here,
    // the two would drift the day one of them is edited.
    const header = texts.export.columns();

    assert.ok(header.includes(`${texts.measure.windMax} (${texts.units.kilometresPerHour})`));
    assert.ok(header.some((name) => name.endsWith(`(${texts.units.celsius})`)));
  });

  it("writes one row a day, in the order of the header", () => {
    const [, row] = lines(toCsv([day()]));

    assert.deepEqual(cells(row), [
      "2046-07-14",
      "Simulation",
      "MRI_AGCM3_2_S",
      "21,4",
      "39",
      "0",
      "12,5",
      "9",
      "24,2",
      "Dégagé",
    ]);
  });

  it("names what produced every day, whatever produced it", () => {
    // The column CLAUDE.md rule 1 turns on. A row with an empty origin is a
    // number that can be taken for a measurement once the file is out of sight
    // of the page that wrote it.
    const days = [
      day({ origin: "observed" }),
      day({ origin: "forecast" }),
      day({ origin: "simulated" }),
    ];
    const written = lines(toCsv(days))
      .slice(1, 4)
      .map((row) => cells(row)[1]);

    assert.deepEqual(written, ["Observé", "Prévision", "Simulation"]);
    for (const name of written) assert.notEqual(name, "");
  });

  it("leaves a missing reading empty rather than filling it", () => {
    const [, row] = lines(toCsv([day({ temperature_min: null, sky: null })]));

    assert.equal(cells(row)[3], "");
    assert.equal(cells(row).at(-1), "");
    // And the row still has every column: an empty cell, not a missing one.
    assert.equal(cells(row).length, texts.export.columns().length);
  });

  it("writes a decimal the way the file's separator obliges", () => {
    // Semicolons and commas go together: a decimal point here would be read as
    // a French thousands separator, and 21,4 as 214.
    const [, row] = lines(toCsv([day({ temperature_max: 8.5 })]));

    assert.equal(cells(row)[4], "8,5");
    assert.ok(!row.includes("8.5"));
  });

  it("quotes a value that would otherwise shift every column after it", () => {
    const [, row] = lines(toCsv([day({ source: "essai;deux" })]));

    assert.ok(row.includes('"essai;deux"'));
    assert.equal(cells(row).length, texts.export.columns().length + 1, "the split sees the quotes");
  });

  it("ends on a line ending, and uses the one every spreadsheet accepts", () => {
    const text = toCsv([day(), day({ date: "2046-07-15" })]);

    assert.ok(text.endsWith("\r\n"));
    assert.equal(lines(text).length, 4, "header, two days, and the empty tail");
    assert.ok(!text.includes("\n\n"));
  });

  it("writes a header and nothing else for a series with no day", () => {
    assert.deepEqual(lines(toCsv([])), [texts.export.columns().join(";"), ""]);
  });
});

describe("what the file is called", () => {
  it("carries the place and the range", () => {
    assert.equal(fileName("Brest", "2046-07-01", "2046-07-31"), "meteo-brest-2046-07-01-2046-07-31.csv");
  });

  it("takes the accents and the spaces out of a place name", () => {
    // The name travels to filesystems this page knows nothing about, and the
    // place is whatever the visitor typed.
    assert.equal(
      fileName("Saint-Étienne du Rouvray", "2046-01-01", "2046-01-05"),
      "meteo-saint-etienne-du-rouvray-2046-01-01-2046-01-05.csv",
    );
  });

  it("stays a name when there is no place to name", () => {
    // The place comes from the query string, which can carry anything or
    // nothing; a name ending on a stray dash is still a name, but this one does
    // not.
    assert.equal(fileName("", "2046-01-01", "2046-01-05"), "meteo-2046-01-01-2046-01-05.csv");
    assert.equal(fileName("!!!", "2046-01-01", "2046-01-05"), "meteo-2046-01-01-2046-01-05.csv");
  });
});
