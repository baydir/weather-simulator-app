/**
 * The results page: read the URL, run the search, put what comes back on screen.
 *
 * The search travels in the query string rather than in memory, which is what
 * makes the URL shareable and the back button work. Building the cards is
 * band.js; this file is the wiring.
 *
 * `has_simulated` is read from the response, not worked out from the days. The
 * server already answers that question for itself — it is what sends it looking
 * for a cloud-cover correction — and it is the fact CLAUDE.md rule 1 hangs on.
 *
 * The season is the one thing here decided from the URL rather than from the
 * answer, and deliberately: it is a background, it must be right before the four
 * round trips rather than after them, and a refused search deserves its ground
 * as much as a served one.
 *
 * A refusal is shown as the server wrote it, word for word. The API answers in
 * French under a single `message` field whatever the cause, so an interface
 * that rewrote them would only be inventing a second, less accurate version.
 */

import { loadConfig, search, SearchError } from "./fetch.js";
import { sources, strip } from "./band.js";
import { chart } from "./chart.js";
import { applyTexts, el } from "./dom.js";
import { texts } from "./i18n.js";
import { fullDate } from "./present.js";
import { dominantSeason } from "./season.js";

const place = document.getElementById("place");
const range = document.getElementById("range");
const count = document.getElementById("count");
const warning = document.getElementById("warning");
const wait = document.getElementById("wait");
const failure = document.getElementById("failure");
const band = document.getElementById("days");
const chartPanel = document.getElementById("chart-panel");
const provenance = document.getElementById("provenance");
const provenanceGrid = document.getElementById("provenance-grid");

applyTexts();

/**
 * The band ladder the chart graduates its axis on, asked for at once and waited
 * on at the end.
 *
 * It is a second call, and deliberately not one the page hangs on: the chart is
 * a second reading of days the strip already carries in full, so a config that
 * does not arrive costs the drawing and not the results. Hence the failure
 * folded into `null` here rather than thrown — the search has its own refusals
 * to report, and none of them is this one.
 */
const ladder = loadConfig().then(
  (config) => ({ edges: config.temperature_band_edges, step: config.temperature_band_step }),
  () => null,
);

const query = new URLSearchParams(window.location.search);
const asked = {
  place: query.get("lieu") ?? "",
  latitude: Number(query.get("lat")),
  longitude: Number(query.get("lon")),
  start: query.get("debut") ?? "",
  end: query.get("fin") ?? "",
};

// The ground, before anything is fetched and before the first paint — this is a
// module, so it runs on the parsed document and the page never shows one season
// then another. Nothing is written when the range is unusable: the markup
// carries a season of its own, and that is the one fallback.
const season = dominantSeason(asked);
if (season) document.body.dataset.season = season;

// textContent, never innerHTML: the name came from the query string, which is
// to say from outside.
place.textContent = asked.place;
range.textContent = texts.results.range(fullDate(asked.start), fullDate(asked.end));

run();

async function run() {
  try {
    const series = await search(asked, (done, total) => {
      wait.textContent = texts.results.progress(done, total);
    });
    await show(series);
  } catch (error) {
    fail(error instanceof SearchError ? error.message : texts.transport.serviceFailed);
  }
}

async function show(series) {
  wait.hidden = true;
  warning.hidden = !series.has_simulated;
  count.textContent = texts.results.count(series.days.length);
  band.append(...strip(series.days));

  // After the strip, always: the days are what the visitor came for, and the
  // drawing waits on a call of its own.
  const scale = await ladder;
  if (scale) {
    chartPanel.append(chart(series.days, scale));
    chartPanel.hidden = false;
  }

  const pairs = sources(series.grid);
  if (pairs.length === 0) {
    provenanceGrid.replaceWith(el("p", { text: texts.provenance.noGrid }));
  } else {
    provenanceGrid.append(...pairs);
  }
  provenance.hidden = false;
}

function fail(message) {
  wait.hidden = true;
  failure.hidden = false;
  failure.textContent = message;
}
