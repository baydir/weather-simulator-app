/** Wire the optional decade comparison without replacing the daily calendars. */
import { climateWindows, climateCards, climateChart, climateTable } from "./climate-comparison.js";
import { PeriodBatch } from "./period-loader.js";
import { shiftRange } from "./compare.js";
import { summarizeClimate } from "./fetch.js";
import { texts } from "./i18n.js";

export function mountClimate({ asked, config, today, cache, load, select }) {
  const get = (id) => document.getElementById(id);
  const windows = climateWindows(asked, config, today);
  const years = [...windows.past, ...windows.future];
  const scale = { edges: config.temperature_band_edges, step: config.temperature_band_step };
  let summary = null;
  let summaryError = null;
  let requestedKey = "";
  let revision = 0;
  const entries = () => ["past", "future"].flatMap((side) => windows[side].map((year) => {
    const series = cache.get(year);
    return { year, side, range: shiftRange(asked, year, config.max_days),
      means: series?.temperature_means, hasSimulated: series?.has_simulated ?? false,
      origins: [...new Set(series?.days.map((day) => day.origin) ?? [])],
    };
  }));
  const batch = new PeriodBatch({ years, cache, load, changed: refresh });

  function renderChart() {
    const width = Math.max(280, get("climate-plot").clientWidth);
    get("climate-plot").replaceChildren(climateChart(entries(), scale, width));
  }

  function render() {
    const items = entries();
    const done = years.filter((year) => cache.has(year)).length;
    get("climate-cards").replaceChildren(climateCards(summary, windows));
    get("climate-warning").hidden = !items.some((entry) => entry.hasSimulated);
    get("climate-coverage-limit").hidden = years.length === windows.required * 2;
    const status = batch.stopping ? (batch.running ? texts.climate.stopping : texts.climate.stopped)
      : batch.active ? texts.climate.loading(batch.active) : "";
    get("climate-status").textContent = [texts.climate.progress(done, years.length), status].filter(Boolean).join(" · ");
    get("climate-start").textContent = batch.started ? texts.climate.resume : texts.climate.start;
    get("climate-start").disabled = batch.running || (done === years.length && !summaryError);
    get("climate-stop").hidden = !batch.running;
    get("climate-stop").disabled = batch.stopping;
    const error = batch.error ?? summaryError;
    get("climate-error").hidden = !error;
    get("climate-error").textContent = error ? (error.status === 429 ? texts.climate.rateLimited : error.message || texts.transport.serviceFailed) : "";
    renderChart();
    get("climate-table").replaceChildren(climateTable(items, select));
  }

  function refresh() {
    render();
    const data = (side) => windows[side].map((year) => cache.get(year)?.temperature_means).filter(Boolean);
    const past = data("past"), future = data("future");
    const key = JSON.stringify([past, future]);
    if (key === requestedKey || (!past.length && !future.length)) return;
    requestedKey = key;
    const current = ++revision;
    summarizeClimate({ past, future }).then((result) => {
      if (current !== revision) return;
      summary = result;
      summaryError = null;
      render();
    }).catch((error) => {
      if (current !== revision) return;
      requestedKey = "";
      summaryError = error;
      render();
    });
  }

  get("climate").hidden = false;
  get("climate-window").textContent = texts.climate.window(windows.required);
  get("climate-start").addEventListener("click", () => batch.run());
  get("climate-stop").addEventListener("click", () => batch.stop());
  get("climate-annual").addEventListener("toggle", renderChart);
  new ResizeObserver(renderChart).observe(get("climate-plot"));
  refresh();
  return { refresh };
}
