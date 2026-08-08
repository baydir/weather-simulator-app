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
 * A refusal is shown as the server wrote it, word for word. The API answers in
 * French under a single `message` field whatever the cause, so an interface
 * that rewrote them would only be inventing a second, less accurate version.
 */

import { search, SearchError } from "./fetch.js";
import { sources, strip } from "./band.js";
import { applyTexts, el } from "./dom.js";
import { texts } from "./i18n.js";
import { fullDate } from "./present.js";

const place = document.getElementById("place");
const range = document.getElementById("range");
const count = document.getElementById("count");
const warning = document.getElementById("warning");
const wait = document.getElementById("wait");
const failure = document.getElementById("failure");
const band = document.getElementById("days");
const provenance = document.getElementById("provenance");
const provenanceGrid = document.getElementById("provenance-grid");

applyTexts();

const query = new URLSearchParams(window.location.search);
const asked = {
  place: query.get("lieu") ?? "",
  latitude: Number(query.get("lat")),
  longitude: Number(query.get("lon")),
  start: query.get("debut") ?? "",
  end: query.get("fin") ?? "",
};

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
    show(series);
  } catch (error) {
    fail(error instanceof SearchError ? error.message : texts.transport.serviceFailed);
  }
}

function show(series) {
  wait.hidden = true;
  warning.hidden = !series.has_simulated;
  count.textContent = texts.results.count(series.days.length);
  band.append(...strip(series.days));

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
