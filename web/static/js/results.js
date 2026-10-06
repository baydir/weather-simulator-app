/** City exploration: daily series fetched unchanged through the existing API. */
import { loadConfig, search, SearchError } from "./fetch.js";
import { strip } from "./band.js";
import { coveredYears, shiftRange, yearColors } from "./compare.js";
import { applyTexts, el } from "./dom.js";
import { texts } from "./i18n.js";
import { fullDate } from "./present.js";
import { dominantSeason } from "./season.js";
import { heatCounts } from "./heat-counts.js";
import { temperatureCalendar, temperatureLegend } from "./temperature-calendar.js";

import { periodLoader } from "./period-loader.js";
import { mountClimate } from "./climate-controller.js";

const get = (id) => document.getElementById(id);
applyTexts();
const query = new URLSearchParams(window.location.search);
const asked = {
  place: query.get("lieu") ?? "",
  latitude: Number(query.get("lat")),
  longitude: Number(query.get("lon")),
  start: query.get("debut") ?? "",
  end: query.get("fin") ?? "",
};
const primaryYear = Number(asked.start.slice(0, 4));
const selected = new Map();
const cache = new Map();
const colors = new Map([[primaryYear, yearColors(0)]]);
let config;
let climate;
const loadYear = periodLoader(cache, (year) => search({ ...asked, ...shiftRange(asked, year, config.max_days) }));
let loading = false;
let calendarReading = "max";
for (const [id, reading] of [["calendar-highs", "max"], ["calendar-lows", "min"]]) {
  get(id).addEventListener("click", () => {
    calendarReading = reading;
    get("calendar-highs").setAttribute("aria-pressed", String(reading === "max"));
    get("calendar-lows").setAttribute("aria-pressed", String(reading === "min"));
    get("calendar-reading").textContent = reading === "max" ? texts.heatCalendar.highNote : texts.heatCalendar.lowNote;
    if (config) render();
  });
}
const season = dominantSeason(asked);
if (season) document.body.dataset.season = season;
get("place").textContent = asked.place;
get("range").textContent = texts.results.range(fullDate(asked.start), fullDate(asked.end));

run();

async function run() {
  // A failed configuration must not discard daily weather that did arrive.
  const settings = loadConfig().catch(() => null);
  try {
    const series = await search(asked, (done, total) => {
      get("wait").textContent = texts.results.progress(done, total);
    });
    get("wait").hidden = true;
    get("count").textContent = texts.results.count(series.days.length);
    get("warning").hidden = !series.has_simulated;
    get("days").append(...strip(series.days, series.humid_heat_peak));
    get("daily").hidden = false;
    if (series.humid_heat_peak) {
      get("humid-note").textContent = texts.humidHeat.note[series.humid_heat_peak];
      get("humid-note").hidden = false;
    }
    selected.set(primaryYear, series);
    cache.set(primaryYear, series);
    config = await settings;
    if (!config) {
      get("failure").textContent = texts.transport.serviceFailed;
      get("failure").hidden = false;
      return;
    }
    get("comparison").hidden = false;
    render();
    get("add-year").addEventListener("submit", addYear);
    // Older servers keep the existing calendar view usable without this feature.
    if (config.climate_window_years) {
      climate = mountClimate({ asked, config, today: series.today, cache, load: loadYear, select: selectYear });
    }
  } catch (error) {
    get("wait").hidden = true;
    get("failure").hidden = false;
    get("failure").textContent = message(error);
  }
}

function refreshMenu() {
  const pick = get("compare-year");
  const previous = Number(pick.value);
  const available = coveredYears(asked, config).filter((year) => !selected.has(year));
  const placeholder = el("option", { text: texts.explorer.year });
  placeholder.value = "";
  pick.replaceChildren(
    placeholder,
    ...available.map((year) => el("option", { text: String(year), attrs: { value: year } })),
  );
  // No reference year is selected on the visitor's behalf.
  pick.value = available.includes(previous) ? String(previous) : "";
  pick.required = true;
  pick.disabled = loading || !available.length;
  get("add-button").disabled = pick.disabled;
  if (!available.length) get("compare-status").textContent = texts.explorer.empty;
}

async function addYear(event) {
  event.preventDefault();
  const year = Number(get("compare-year").value);
  if (loading || selected.has(year) || !coveredYears(asked, config).includes(year)) return;
  loading = true;
  refreshMenu();
  get("compare-failure").hidden = true;
  get("compare-status").textContent = texts.explorer.loading(year);
  try {
    await loadYear(year);
    selectYear(year);
    climate?.refresh();
  } catch (error) {
    get("compare-failure").textContent = message(error);
    get("compare-failure").hidden = false;
  } finally {
    loading = false;
    get("compare-status").textContent = "";
    refreshMenu();
  }
}

function render() {
  const scale = { edges: config.temperature_band_edges, step: config.temperature_band_step };
  const entries = [...selected.entries()].sort(([a], [b]) => a - b);
  const warning = el("p", { className: "warning", text: texts.warning.notAForecast });
  warning.hidden = !entries.some(([, series]) => series.has_simulated);
  get("year-charts").replaceChildren(
    warning,
    temperatureLegend(config.temperature_band_edges),
    el("div", { className: "year-legends" }, entries.map(([year, series]) => yearPanel(year, series))),
  );
  refreshMenu();
}

function yearPanel(year, series) {
  const shifted = year === primaryYear ? asked : shiftRange(asked, year, config.max_days);
  const heading = el("h3", { text: String(year) });
  const header = el("div", { className: "year-heading" }, [heading]);
  if (year !== primaryYear) {
    const remove = el("button", { className: "link", text: texts.explorer.remove(year), attrs: { type: "button" } });
    remove.addEventListener("click", () => {
      selected.delete(year);
      render();
      get("compare-year").focus();
    });
    header.append(remove);
  }
  const origins = [...new Set(series.days.map((day) => day.origin))];
  const pair = colors.get(year);
  const panel = el("article", { className: "year-panel", attrs: { style: `--year-high: ${pair.high}; --year-low: ${pair.low}` } }, [
    header,
    el("p", { className: "year-period", text: texts.explorer.period(fullDate(shifted.start), fullDate(shifted.end)) }),
    el("p", { className: "origin-label", text: origins.map((origin) => texts.export.origin[origin]).join(" · ") }),
  ]);
  panel.append(temperatureCalendar(series.days, shifted, calendarReading));
  panel.append(heatCounts(series.heat_counts, shifted));
  return panel;
}

function message(error) {
  return error instanceof SearchError ? error.message : texts.transport.serviceFailed;
}

function selectYear(year) {
  if (!cache.has(year)) return;
  if (!colors.has(year)) colors.set(year, yearColors(colors.size));
  selected.set(year, cache.get(year));
  render();
}
