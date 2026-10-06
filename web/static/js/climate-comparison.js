/** Two decade summaries and one continuous chart of server-computed annual means. */
import { coveredYears, shiftRange } from "./compare.js";
import { el, svg } from "./dom.js";
import { texts } from "./i18n.js";
import { decimal, signedDecimal, fullDate } from "./present.js";
import { temperatureWindow, ticks } from "./chart.js";

/** Calendar navigation only. The current calendar year is excluded from both windows. */
export function climateWindows(range, config, today) {
  const year = Number(today.slice(0, 4));
  const count = config.climate_window_years;
  const covered = coveredYears(range, config);
  return {
    past: covered.filter((item) => item < year && shiftRange(range, item, config.max_days).end < today).slice(-count),
    future: covered.filter((item) => item > year && item <= year + count),
    required: count,
  };
}

const readings = ["temperature_max", "temperature_min"];
const valueLabel = (value, format = decimal) => value === null || value === undefined ? "—" : `${format(value)} °C`;

export function climateCards(summary, windows) {
  return el("div", { className: "climate-cards" }, ["past", "future"].map((side) => {
    const years = windows[side];
    const data = summary?.[side];
    return el("section", { className: "climate-card" }, [
      el("p", { className: "eyebrow", text: texts.climate[side] }),
      el("h3", { text: texts.climate.years(years[0], years.at(-1)) }),
      ...readings.map((reading) => el("div", { className: "climate-metric" }, [
        el("span", { text: texts.climate.reading[reading] }),
        el("strong", { text: valueLabel(data?.[reading]) }),
      ])),
      el("p", { className: "reading-note", text: data
        ? texts.climate.complete(data.complete_max_years, data.complete_min_years, windows.required)
        : texts.climate.waiting }),
      ...(side === "future" ? [el("p", { className: "climate-delta", text: texts.climate.difference(
        valueLabel(summary?.difference?.temperature_max, signedDecimal), valueLabel(summary?.difference?.temperature_min, signedDecimal),
      ) })] : []),
    ]);
  }));
}

/** Shared axis; each supplied record is one annual period, never a derived JS mean. */
export function climateChart(entries, scale, width = 800) {
  const height = 290;
  const left = 52, right = 14, top = 34, bottom = 42;
  const graph = svg("svg", { className: "climate-chart", attrs: {
    viewBox: `0 0 ${width} ${height}`, role: "img", "aria-label": texts.climate.chart,
  } });
  graph.append(svg("title", { text: texts.climate.chart }));
  const data = entries.map((entry) => ({
    temperature_max: entry.means?.temperature_max ?? null,
    temperature_min: entry.means?.temperature_min ?? null,
  }));
  const domain = temperatureWindow(data, scale.step);
  if (!domain || !entries.length) return el("p", { className: "reading-note", text: texts.climate.waiting });
  const first = entries[0].year, last = entries.at(-1).year;
  const x = (year) => left + (year - first) / Math.max(1, last - first) * (width - left - right);
  const y = (value) => height - bottom - (value - domain.bottom) / (domain.top - domain.bottom) * (height - top - bottom);
  for (const value of ticks(domain, scale.edges, scale.step)) {
    graph.append(svg("line", { className: "climate-grid", attrs: { x1: left, x2: width - right, y1: y(value), y2: y(value) } }));
    graph.append(svg("text", { attrs: { x: left - 8, y: y(value) + 4, "text-anchor": "end" }, text: decimal(value) }));
  }
  graph.append(svg("text", { attrs: { x: 0, y: 16 }, text: "°C" }));
  const futureStart = entries.find((entry) => entry.side === "future");
  if (futureStart) {
    const boundary = x(futureStart.year - .5);
    graph.append(svg("line", { className: "climate-boundary", attrs: { x1: boundary, x2: boundary, y1: top, y2: height - bottom } }));
    graph.append(svg("text", { attrs: { x: width - right, y: 17, "text-anchor": "end" }, text: texts.climate.future }));
  }
  graph.append(svg("text", { attrs: { x: left, y: 17 }, text: texts.climate.past }));
  const labelEvery = width < 500 ? 7 : 4;
  entries.forEach((entry, index) => {
    if (index !== 0 && index !== entries.length - 1 && index % labelEvery !== 0) return;
    // Avoid crowding the final tick when a regular tick falls nearby.
    if (index !== entries.length - 1 && index > entries.length - 1 - labelEvery) return;
    graph.append(svg("text", { attrs: { x: x(entry.year), y: height - 12,
      "text-anchor": index === 0 ? "start" : index === entries.length - 1 ? "end" : "middle",
    }, text: String(entry.year) }));
  });
  for (const reading of readings) {
    let previous = null;
    for (const entry of entries) {
      const value = entry.means?.[reading];
      if (value === null || value === undefined) { previous = null; continue; }
      const simulated = entry.hasSimulated;
      // Only connect successive requested periods. An unloaded/incomplete year
      // breaks the path; the explicitly excluded current year has no invented point.
      if (previous) graph.append(svg("line", {
        className: `climate-line ${reading} ${simulated ? "simulated" : ""}`,
        attrs: { x1: x(previous.year), y1: y(previous.value), x2: x(entry.year), y2: y(value) },
      }));
      const point = svg(reading === "temperature_max" ? "circle" : "rect", {
        className: `climate-point ${reading}`,
        attrs: reading === "temperature_max" ? { cx: x(entry.year), cy: y(value), r: 3.5 }
          : { x: x(entry.year) - 3, y: y(value) - 3, width: 6, height: 6 },
      });
      point.append(svg("title", { text: `${entry.year} · ${texts.climate.reading[reading]} : ${valueLabel(value)} · ${(entry.origins ?? []).map((origin) => texts.export.origin[origin]).join(" · ")}` }));
      graph.append(point);
      previous = { year: entry.year, value };
    }
  }
  return graph;
}

/** The same exact values and coverage as the chart, accessible without hovering. */
export function climateTable(entries, select) {
  return el("table", { className: "climate-table" }, [
    el("caption", { text: texts.climate.details }),
    el("thead", {}, [el("tr", {}, [texts.explorer.year, texts.climate.high, texts.climate.low, texts.climate.coverage]
      .map((text) => el("th", { text, attrs: { scope: "col" } })))]),
    el("tbody", {}, entries.map((entry) => {
      const button = el("button", { className: "link", text: String(entry.year), attrs: { type: "button" } });
      button.disabled = !entry.means;
      button.addEventListener("click", () => select(entry.year));
      return el("tr", {}, [
        el("th", { attrs: { scope: "row" } }, [button,
          el("small", { text: `${fullDate(entry.range.start)} – ${fullDate(entry.range.end)}` }),
          el("small", { text: entry.origins.map((origin) => texts.export.origin[origin]).join(" · ") }),
        ]),
        ...readings.map((reading) => el("td", { text: valueLabel(entry.means?.[reading]) })),
        el("td", { text: entry.means ? texts.climate.days(
          entry.means.available_max_days, entry.means.available_min_days, entry.means.requested_days,
        ) : texts.climate.unloaded }),
      ]);
    })),
  ]);
}
