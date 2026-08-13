/**
 * Which ground a search lands on.
 *
 * Three decisions are checked here rather than described: the astronomical
 * bounds and their eve, the season the count settles on when a range straddles
 * two, and the reversal below the equator. The ninety-day limit is what keeps
 * the third candidate out of the count, so a range longer than any search can be
 * is checked too — the URL is typed by hand often enough.
 */

import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { dominantSeason, seasonOf } from "../../web/static/js/season.js";

/** Northern unless a latitude says otherwise. */
const north = { latitude: 48.8566 }; // Paris
const south = { latitude: -33.4489 }; // Santiago

describe("the season of one day", () => {
  it("turns on the twenty-first, not on the twentieth", () => {
    assert.equal(seasonOf("2046-03-20"), "winter");
    assert.equal(seasonOf("2046-03-21"), "spring");
    assert.equal(seasonOf("2046-06-20"), "spring");
    assert.equal(seasonOf("2046-06-21"), "summer");
    assert.equal(seasonOf("2046-09-20"), "summer");
    assert.equal(seasonOf("2046-09-21"), "autumn");
    assert.equal(seasonOf("2046-12-20"), "autumn");
    assert.equal(seasonOf("2046-12-21"), "winter");
  });

  it("carries December's winter into January", () => {
    assert.equal(seasonOf("2046-12-31"), "winter");
    assert.equal(seasonOf("2046-01-01"), "winter");
  });

  it("reverses below the equator", () => {
    assert.equal(seasonOf("2046-01-15", south.latitude), "summer");
    assert.equal(seasonOf("2046-07-14", south.latitude), "winter");
    assert.equal(seasonOf("2046-04-01", south.latitude), "autumn");
    assert.equal(seasonOf("2046-10-01", south.latitude), "spring");
  });

  it("reads a latitude it cannot use as northern", () => {
    // A hand-edited URL gives NaN, and NaN < 0 is false. The calendar is the
    // right answer to give there, not an error.
    assert.equal(seasonOf("2046-01-15", Number("")), "winter");
    assert.equal(seasonOf("2046-01-15", undefined), "winter");
    // The equator itself counts as northern, which is a choice and not a
    // measurement: at 0° neither season means much.
    assert.equal(seasonOf("2046-01-15", 0), "winter");
  });
});

describe("the season a range belongs to", () => {
  it("takes the season a range sits inside", () => {
    assert.equal(dominantSeason({ start: "2046-07-01", end: "2046-07-14", ...north }), "summer");
    assert.equal(dominantSeason({ start: "2046-01-05", end: "2046-02-20", ...north }), "winter");
  });

  it("takes the better represented of two — the documented example", () => {
    // 1 June to 1 August: twenty days of spring, forty-two of summer.
    assert.equal(dominantSeason({ start: "2046-06-01", end: "2046-08-01", ...north }), "summer");
  });

  it("counts rather than looks at either end", () => {
    // Starts in winter, ends in spring, and is winter all the same: 69 to 21.
    assert.equal(dominantSeason({ start: "2046-01-11", end: "2046-04-10", ...north }), "winter");
  });

  it("gives a tie to the season the range ends in", () => {
    // Ten days of summer, then ten of autumn.
    assert.equal(dominantSeason({ start: "2046-09-11", end: "2046-09-30", ...north }), "autumn");
    // And the other way round, so the rule is not the alphabet.
    assert.equal(dominantSeason({ start: "2046-06-11", end: "2046-06-30", ...north }), "summer");
  });

  it("crosses the new year", () => {
    assert.equal(dominantSeason({ start: "2045-12-21", end: "2046-01-10", ...north }), "winter");
    assert.equal(dominantSeason({ start: "2045-12-01", end: "2046-01-15", ...north }), "winter");
  });

  it("does not flinch at the daylight-saving change", () => {
    // The walk steps by exact days at noon UTC. Read at local midnight, these
    // ranges lose or repeat a day, and a count is what this file is.
    assert.equal(dominantSeason({ start: "2046-03-21", end: "2046-03-31", ...north }), "spring");
    assert.equal(dominantSeason({ start: "2046-10-20", end: "2046-10-31", ...north }), "autumn");
  });

  it("reverses below the equator", () => {
    assert.equal(dominantSeason({ start: "2046-01-05", end: "2046-02-20", ...south }), "summer");
    assert.equal(dominantSeason({ start: "2046-06-01", end: "2046-08-01", ...south }), "winter");
  });

  it("still answers on a range no search could ask for", () => {
    // Three seasons at once cannot come out of the form — ninety days is the
    // limit and the shortest season is ninety days long — but it can be typed
    // into the address bar, and the count holds: 92 summer, 91 autumn, 90
    // winter.
    assert.equal(dominantSeason({ start: "2046-06-21", end: "2047-03-20", ...north }), "summer");
  });

  it("has nothing to say about a range that is not one", () => {
    // Null rather than a season invented: the page keeps the ground its markup
    // already carries, and the refusal is drawn on it.
    assert.equal(dominantSeason({ start: "", end: "2046-07-14", ...north }), null);
    assert.equal(dominantSeason({ start: "2046-07-14", end: "", ...north }), null);
    assert.equal(dominantSeason({ start: "2046-07-14", end: "2046-07-01", ...north }), null);
    assert.equal(dominantSeason({ start: "avant", end: "hier", ...north }), null);
  });
});
