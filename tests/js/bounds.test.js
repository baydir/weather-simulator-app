/**
 * What the form refuses on its own, before a single request leaves.
 *
 * The API enforces the same three rules and keeps doing so — a limit only the
 * browser applies is not a limit. What is checked here is that the two agree,
 * and that the numbers come from the served config rather than from a constant
 * written into the page.
 */

import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { refuse, span } from "../../web/static/js/bounds.js";

/** What GET /api/config really answers. */
const CONFIG = {
  geocoding_url: "https://geocoding-api.open-meteo.com/v1/search",
  coverage_start: "1950-01-01",
  coverage_end: "2050-12-31",
  max_days: 92,
};

describe("how long a range is", () => {
  it("counts both ends", () => {
    assert.equal(span("2046-07-01", "2046-07-01"), 1);
    assert.equal(span("2046-07-01", "2046-07-02"), 2);
    assert.equal(span("2046-07-01", "2046-09-28"), 90);
  });

  it("does not flinch at the daylight-saving change", () => {
    // Read at midnight in a local zone, this range is 23 or 25 hours short of a
    // whole number of days, and the count comes out one too low.
    assert.equal(span("2046-03-24", "2046-03-31"), 8);
    assert.equal(span("2046-10-20", "2046-10-31"), 12);
  });
});

describe("what the form refuses", () => {
  it("lets an ordinary range through", () => {
    assert.equal(refuse({ start: "2046-07-01", end: "2046-07-14" }, CONFIG), null);
  });

  it("refuses an incomplete range", () => {
    assert.match(refuse({ start: "", end: "2046-07-14" }, CONFIG), /les deux dates/);
    assert.match(refuse({ start: "2046-07-01", end: "" }, CONFIG), /les deux dates/);
  });

  it("refuses a range that runs backwards", () => {
    assert.match(
      refuse({ start: "2046-07-14", end: "2046-07-01" }, CONFIG),
      /précède la date de début/,
    );
  });

  it("refuses a range outside the covered period, at either end", () => {
    assert.match(refuse({ start: "1949-12-31", end: "1950-02-01" }, CONFIG), /1950 à 2050/);
    assert.match(refuse({ start: "2050-12-01", end: "2051-01-01" }, CONFIG), /1950 à 2050/);
  });

  it("accepts the bounds themselves", () => {
    assert.equal(refuse({ start: "1950-01-01", end: "1950-01-31" }, CONFIG), null);
    assert.equal(refuse({ start: "2050-12-01", end: "2050-12-31" }, CONFIG), null);
  });

  it("refuses on the ninety-third day, not on the ninety-second", () => {
    // Ninety-two is the longest season — 21 June to 20 September — and the whole
    // point of the bound is that one fits.
    assert.equal(refuse({ start: "2046-07-01", end: "2046-09-30" }, CONFIG), null);
    assert.match(refuse({ start: "2046-07-01", end: "2046-10-01" }, CONFIG), /93 jours/);
  });

  it("obeys the served max_days, not a 92 written into the page", () => {
    // The one thing that would drift: a constant here would go on saying 92 the
    // day the API said something else. It said 90 until a season had to fit.
    const wider = { ...CONFIG, max_days: 120 };
    assert.equal(refuse({ start: "2046-07-01", end: "2046-10-01" }, wider), null);
    assert.match(refuse({ start: "2046-07-01", end: "2046-11-01" }, wider), /124 jours/);
  });

  it("obeys the served coverage bounds too", () => {
    const narrow = { ...CONFIG, coverage_start: "2000-01-01", coverage_end: "2030-12-31" };
    assert.match(refuse({ start: "1999-12-31", end: "2000-01-05" }, narrow), /2000 à 2030/);
  });
});
