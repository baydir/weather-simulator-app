import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { install, byClass, reads } from "./dom-stub.js";
import { temperatureCalendar, temperatureLegend } from "../../web/static/js/temperature-calendar.js";

install();
const day = (date, extra = {}) => ({ date, origin: "simulated", temperature_max: 32,
  temperature_min: 19, temperature_max_band: 6, temperature_min_band: 3, ...extra });

describe("daily heat calendars", () => {
  it("uses served bands rather than reclassifying temperatures", () => {
    const node = temperatureCalendar([day("2050-07-01")], { start: "2050-07-01", end: "2050-07-01" });
    assert.equal(byClass(node, "calendar-day")[0].attrs["data-band"], "6");
    const low = temperatureCalendar([day("2050-07-01")], { start: "2050-07-01", end: "2050-07-01" }, "min");
    assert.equal(byClass(low, "calendar-day")[0].attrs["data-band"], "3");
  });
  it("keeps a missing day visible and does not give it a temperature color", () => {
    const node = temperatureCalendar([day("2050-07-01")], { start: "2050-07-01", end: "2050-07-02" });
    const missing = byClass(node, "calendar-day--missing");
    assert.equal(missing.length, 1);
    assert.equal(missing[0].attrs["data-band"], undefined);
    assert.match(missing[0].attrs["aria-label"], /donnée manquante/);
  });
  it("includes leap day and splits months in calendar order", () => {
    const node = temperatureCalendar([], { start: "2048-02-28", end: "2048-03-01" });
    assert.equal(byClass(node, "calendar-month").length, 2);
    assert.deepEqual(byClass(node, "calendar-day").map((n) => n.attrs["data-date"]), ["2048-02-28", "2048-02-29", "2048-03-01"]);
  });
  it("names the source regime and retains the same seam as the daily cards", () => {
    const node = temperatureCalendar([day("2050-07-01", { origin: "forecast" }), day("2050-07-02")], { start: "2050-07-01", end: "2050-07-02" });
    assert.match(byClass(node, "calendar-day")[0].attrs["aria-label"], /Prévision/);
    assert.equal(byClass(node, "calendar-day--seam")[0].attrs["data-date"], "2050-07-02");
  });
  it("reads the scale from the server-provided boundaries", () => {
    const node = temperatureLegend([0, 10]);
    assert.equal(byClass(node, "calendar-swatch").length, 3);
    assert.match(reads(node), /< 0 °C/);
    assert.match(reads(node), /≥ 10 °C/);
  });
});
