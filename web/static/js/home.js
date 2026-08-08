/**
 * The form: fill in what the API needs that the visitor did not type.
 *
 * Two things only. The date fields get their bounds from `/api/config`, so the
 * interface refuses what the API refuses instead of keeping a second copy of
 * the numbers — CLAUDE.md rule 3. And the place name becomes coordinates,
 * because `/api/plan` asks for a latitude and a longitude and a name is not one.
 *
 * **The visitor picks the place, this file never picks for them.** Geocoding
 * answers with candidates, not an answer: there are eight Saint-Denis in France
 * and a Paris in Texas. Taking the first would be right most of the time, which
 * is exactly what makes it hard to notice when it is not — so submission stays
 * blocked until a candidate has been chosen.
 */

import { geocode, loadConfig, SearchError } from "./fetch.js";
import { refuse } from "./bounds.js";
import { applyTexts, el } from "./dom.js";
import { texts } from "./i18n.js";

const form = document.getElementById("search");
const place = document.getElementById("lieu");
const candidates = document.getElementById("candidates");
const chosen = document.getElementById("chosen");
const chosenName = document.getElementById("chosen-name");
const change = document.getElementById("change");
const latitude = document.getElementById("lat");
const longitude = document.getElementById("lon");
const from = document.getElementById("debut");
const to = document.getElementById("fin");
const status = document.getElementById("status");
const placeStatus = document.getElementById("place-status");
const found = document.getElementById("found");

applyTexts();
fillDefaultDates();

let config = null;

// The bounds, served rather than written here. `min` and `max` let the browser
// refuse an impossible date in its own picker; `refuse()` catches what typing
// gets past it.
loadConfig()
  .then((served) => {
    config = served;
    for (const field of [from, to]) {
      field.min = served.coverage_start;
      field.max = served.coverage_end;
    }
  })
  .catch((error) => say(error.message));

// --- choosing the place ------------------------------------------------------

const PAUSE_MS = 300;
let pending = null;

place.addEventListener("input", () => {
  forget();
  clearTimeout(pending);
  const name = place.value.trim();
  if (name.length < 2) {
    offer([]);
    aboutPlace("");
    return;
  }
  // Not on every keystroke: someone typing "Pontarlier" would fire ten
  // searches, and Open-Meteo counts every one of them against their address.
  pending = setTimeout(() => propose(name), PAUSE_MS);
});

async function propose(name) {
  aboutPlace(texts.form.searching);
  try {
    // `matches`, not `candidates`: that name is the list element above.
    const matches = await geocode(name, config ?? (await loadConfig()));
    // A slower answer to an older query must not overwrite a newer one.
    if (place.value.trim() !== name) return;
    offer(matches);
    aboutPlace(matches.length === 0 ? texts.form.notFound : "");
    // Said aloud only. On screen the list is the answer, and counting five
    // visible items back to the reader is noise.
    found.textContent = matches.length ? texts.form.candidates(matches.length) : "";
  } catch (error) {
    offer([]);
    aboutPlace(error instanceof SearchError ? error.message : texts.transport.serviceFailed);
  }
}

function offer(shown) {
  candidates.replaceChildren(
    ...shown.map((candidate) =>
      el("li", { attrs: { role: "option" } }, [
        el("button", {
          className: "candidate",
          text: describe(candidate),
          attrs: { type: "button" },
        }),
      ]),
    ),
  );
  for (const [index, node] of [...candidates.querySelectorAll("button")].entries()) {
    node.addEventListener("click", () => keep(shown[index]));
  }
  candidates.hidden = shown.length === 0;
  place.setAttribute("aria-expanded", String(shown.length > 0));
}

function keep(candidate) {
  latitude.value = candidate.latitude;
  longitude.value = candidate.longitude;
  place.value = candidate.name;
  chosenName.textContent = texts.form.chosen(describe(candidate));
  chosen.hidden = false;
  place.hidden = true;
  offer([]);
  aboutPlace("");
  found.textContent = "";
  say("");
}

/** Back to typing: the coordinates go with the name that produced them. */
function forget() {
  latitude.value = "";
  longitude.value = "";
  chosen.hidden = true;
  place.hidden = false;
}

change.addEventListener("click", () => {
  forget();
  place.focus();
  place.select();
});

/** "Paris, Île-de-France, France" — enough to tell two homonyms apart. */
function describe(candidate) {
  return [candidate.name, candidate.admin1, candidate.country].filter(Boolean).join(", ");
}

// --- what leaves, and what does not ------------------------------------------

form.addEventListener("submit", (event) => {
  if (!latitude.value || !longitude.value) {
    event.preventDefault();
    say(texts.form.placeRequired);
    place.hidden = false;
    place.focus();
    return;
  }
  // Without the config there are no bounds to check against, and inventing
  // them here is the copy rule 3 forbids. The API refuses all the same.
  const reason = config && refuse({ start: from.value, end: to.value }, config);
  if (reason) {
    event.preventDefault();
    say(reason);
  }
});

// --- odds and ends -----------------------------------------------------------

/** Refusals and failures that concern the whole search: shown by the button. */
function say(message) {
  status.textContent = message;
}

/** What is happening to the place field: shown beside the place field. */
function aboutPlace(message) {
  placeStatus.textContent = message;
}

/**
 * A fortnight from today, so the page is usable the moment it loads.
 *
 * Only a default in a form field: nothing is displayed from it, the visitor
 * overwrites it freely, and where the observed stops is still decided by the
 * server's clock and not by this one.
 */
function fillDefaultDates() {
  const today = new Date();
  from.value = isoDay(today, 0);
  to.value = isoDay(today, 13);
}

function isoDay(base, offset) {
  const day = new Date(base);
  day.setDate(day.getDate() + offset);
  return `${day.getFullYear()}-${pad(day.getMonth() + 1)}-${pad(day.getDate())}`;
}

function pad(n) {
  return String(n).padStart(2, "0");
}
