/**
 * What the interface shows, checked without a browser.
 *
 * `node --test`, no dependency, no install, no build step. Everything testable
 * this way was deliberately put in present.js; what is left only places nodes.
 *
 * The last suite is the one that matters most. CLAUDE.md rule 1 outranks
 * everything else in this project and forbids the vocabulary of forecasting on
 * a future date — until now that was a sentence in a document, which is to say
 * something a hurried edit walks straight past. Here it fails a test.
 */

import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { describe, it } from "node:test";
import { fileURLToPath } from "node:url";

import { texts } from "../../web/static/js/i18n.js";
import * as present from "../../web/static/js/present.js";

describe("the sky class", () => {
  // Reproduced from docs/application.md, on purpose rather than imported: the
  // point is to fail when the code and the document disagree.
  const DOCUMENTED = [
    ["clear", "☀️", "Dégagé"],
    ["cloudy", "⛅", "Nuageux"],
    ["overcast", "☁️", "Couvert"],
    ["rain", "🌧️", "Pluie"],
    ["snow", "🌨️", "Neige"],
  ];

  for (const [value, emoji, label] of DOCUMENTED) {
    it(`${value} shows ${emoji} and "${label}"`, () => {
      assert.deepEqual(present.sky(value), { emoji, label });
    });
  }

  it("the five classes, and nothing more", () => {
    assert.deepEqual(
      Object.keys(present.SKY),
      DOCUMENTED.map(([value]) => value),
    );
  });

  it("a day with no class gets a label, never an invented pictogram", () => {
    const absent = { emoji: "", label: "Ciel indéterminé" };
    assert.deepEqual(present.sky(null), absent);
    assert.deepEqual(present.sky(undefined), absent);
    // A class the server has never served must not fall through to a picture.
    assert.deepEqual(present.sky("fog"), absent);
  });
});

describe("the display rounding", () => {
  // Settled in docs/application.md and validated: whole degrees, whole km/h,
  // one decimal on millimetres. The last is the only one that is not cosmetic.
  it("temperatures as whole numbers", () => {
    assert.equal(present.temperature(21.34), "21");
    assert.equal(present.temperature(38.9), "39");
    assert.equal(present.temperature(-3.2), "-3");
  });

  it("winds as whole numbers", () => {
    assert.equal(present.wind(8.4), "8");
    assert.equal(present.wind(18.7), "19");
  });

  it("precipitation to a tenth, with a French decimal comma", () => {
    assert.equal(present.precipitation(0.44), "0,4");
    assert.equal(present.precipitation(1.24), "1,2");
    assert.equal(present.precipitation(12), "12,0");
  });

  it("the tenth tells a dry day from a wet one", () => {
    // The 1 mm gate commands two of the five sky classes. Showing "0 mm" on a
    // day carrying the rain pictogram would be a contradiction on screen.
    assert.notEqual(present.precipitation(0.4), present.precipitation(1.2));
  });
});

describe("the gaps", () => {
  it("a missing measure shows a dash, never NaN or undefined", () => {
    for (const format of [present.temperature, present.precipitation, present.wind]) {
      for (const gap of [null, undefined]) {
        assert.equal(format(gap), "—");
      }
    }
  });

  it("isMissing does not take zero for an absence", () => {
    assert.equal(present.isMissing(0), false);
    assert.equal(present.precipitation(0), "0,0");
    assert.equal(present.isMissing(null), true);
  });
});

describe("the dates", () => {
  it("carry the day, the month and the year in French", () => {
    assert.equal(present.dayLabel("2046-07-14"), "samedi 14");
    assert.equal(present.monthLabel("2046-07-14"), "juillet");
    assert.equal(present.fullDate("2046-07-14"), "14 juillet 2046");
  });

  it("are read in UTC, wherever the visitor is", () => {
    // Left to the local zone, "2046-07-14" lands on midnight UTC and slides
    // back a day west of Greenwich — the card would carry the 13th while the
    // server had the 14th. A fresh process is the only way to prove it: the
    // zone is fixed when this one starts.
    const west = execFileSync(
      process.execPath,
      [
        "--input-type=module",
        "-e",
        "const m = await import('./web/static/js/present.js');" +
          "console.log(m.dayLabel('2046-07-14'), '|', m.fullDate('2046-07-14'));",
      ],
      {
        cwd: fileURLToPath(new URL("../..", import.meta.url)),
        env: { ...process.env, TZ: "America/Los_Angeles" },
        encoding: "utf8",
      },
    ).trim();
    assert.equal(west, "samedi 14 | 14 juillet 2046");
  });

  it("the month marker turns on the month, not on the day", () => {
    assert.equal(present.monthKey("2046-07-14"), present.monthKey("2046-07-31"));
    assert.notEqual(present.monthKey("2046-07-31"), present.monthKey("2046-08-01"));
  });
});

describe("the vocabulary, rule 1", () => {
  const FORBIDDEN = ["prévision", "prévisions", "il fera"];

  // The sentences whose whole job is to place the word correctly. Widening this
  // list is the moment to stop and think, which is why it is written out.
  //
  // `provenance.forecast` is the third, and it was added on the day the series
  // stopped handing tomorrow to the climate model. The ban exists so that a
  // trajectory is never sold as a forecast; it was never meant to stop the
  // interface naming a forecast that is genuinely one. Calling the fortnight
  // ahead a simulation would now be the lie the rule was written against, in
  // the other direction.
  //
  // What the ban still covers, untouched: every string describing a simulated
  // day, and "il fera" everywhere — a forecast states a likelihood, not what
  // the day will be.
  const ALLOWED = ["warning.notAForecast", "warning.scenario", "provenance.forecast"];

  /** Every string in the dictionary, including those a function returns. */
  function* strings(node, path = "") {
    if (typeof node === "string") {
      yield [path, node];
    } else if (typeof node === "function") {
      yield [path, String(node("…", "…"))];
    } else if (node && typeof node === "object") {
      for (const [key, child] of Object.entries(node)) {
        yield* strings(child, path ? `${path}.${key}` : key);
      }
    }
  }

  it("no string speaks of a forecast, but the two that deny one", () => {
    for (const [path, text] of strings(texts)) {
      if (ALLOWED.includes(path)) continue;
      for (const word of FORBIDDEN) {
        assert.ok(!text.toLowerCase().includes(word), `"${word}" in texts.${path}: ${text}`);
      }
    }
  });

  it("and the warning does deny it", () => {
    assert.match(texts.warning.notAForecast, /prévision/);
  });

  it("the maximum wind is never a gust", () => {
    // wind_speed_10m_max is the strongest *sustained* wind of the day; a gust
    // commonly runs to twice it.
    for (const [path, text] of strings(texts)) {
      assert.ok(!text.toLowerCase().includes("rafale"), `"rafale" in texts.${path}`);
    }
  });
});
