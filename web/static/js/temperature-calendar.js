/** Daily calendar tiles using server-classified temperature bands unchanged. */
import { el } from "./dom.js";
import { eachDay, at } from "./calendar.js";
import { fullDate, monthLabel, temperature, isMissing } from "./present.js";
import { texts } from "./i18n.js";
import { seamIndex } from "./series.js";

export function temperatureCalendar(days, range, reading = "max") {
  const field = `temperature_${reading}`;
  const bandField = `${field}_band`;
  const label = reading === "max" ? texts.measure.high : texts.measure.low;
  const found = new Map(days.map((day) => [day.date, day]));
  const seam = seamIndex(days);
  const seamDate = seam < 0 ? null : days[seam].date;
  const months = new Map();
  for (const date of eachDay(range.start, range.end)) {
    const key = date.slice(0, 7);
    if (!months.has(key)) months.set(key, []);
    months.get(key).push(date);
  }
  return el("div", { className: "temperature-calendar" }, [...months.values()].map((dates) => {
    const grid = el("div", { className: "calendar-grid" });
    for (const weekday of texts.heatCalendar.weekdays) {
      grid.append(el("span", { className: "calendar-weekday", text: weekday, attrs: { "aria-hidden": "true" } }));
    }
    const monthStart = `${dates[0].slice(0, 8)}01`;
    const offset = (new Date(at(monthStart)).getUTCDay() + 6) % 7 + Number(dates[0].slice(8)) - 1;
    for (let i = 0; i < offset; i += 1) grid.append(el("span", { attrs: { "aria-hidden": "true" } }));
    for (const date of dates) {
      const day = found.get(date);
      const value = day?.[field];
      const origin = day ? texts.export.origin[day.origin] : texts.measure.missingLabel;
      const description = `${fullDate(date)} · ${label} : ${isMissing(value) ? texts.measure.missingLabel : `${temperature(value)} °C`} · ${origin}`;
      const tile = el("button", {
        className: `calendar-day${isMissing(value) ? " calendar-day--missing" : ""}${date === seamDate ? " calendar-day--seam" : ""}`,
        attrs: {
          type: "button", "data-band": day?.[bandField], "data-date": date,
          "data-origin": day?.origin, "aria-label": description,
          title: description, "aria-pressed": "false",
        },
      }, [
        el("span", { className: "calendar-day-number", text: date.slice(8).replace(/^0/, "") }),
        el("span", { className: "calendar-day-value", text: isMissing(value) ? "—" : `${temperature(value)}°` }),
      ]);
      tile.addEventListener("click", () => {
        for (const button of grid.querySelectorAll(".calendar-day")) button.setAttribute("aria-pressed", "false");
        tile.setAttribute("aria-pressed", "true");
        detail.textContent = date === seamDate ? `${description} · ${texts.results.seam}` : description;
      });
      grid.append(tile);
    }
    for (let i = offset + dates.length; i < 42; i += 1) grid.append(el("span", { attrs: { "aria-hidden": "true" } }));
    const detail = el("p", { className: "calendar-detail", text: texts.heatCalendar.tap, attrs: { "aria-live": "polite" } });
    return el("section", { className: "calendar-month" }, [
      el("h4", { text: monthLabel(dates[0]) }), grid, detail,
    ]);
  }));
}

/** Labels describe the same band boundaries the server sends in /api/config. */
export function temperatureLegend(edges) {
  return el("div", { className: "calendar-scale" }, Array.from({ length: edges.length + 1 }, (_, index) => {
    const label = index === 0 ? `< ${edges[0]} °C`
      : index === edges.length ? `≥ ${edges.at(-1)} °C`
      : `${edges[index - 1]} ≤ °C < ${edges[index]}`;
    return el("span", { className: "calendar-scale-item" }, [
      el("span", { className: "calendar-swatch", attrs: { "data-band": index, "aria-hidden": "true" } }),
      el("span", { text: label }),
    ]);
  }));
}
