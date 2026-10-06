"""Check decade summaries in a browser with entirely invented upstream data.

Use CLIMATE_BROWSER_CHANNEL=chrome if Playwright's bundled browser is unavailable.
All Open-Meteo calls are intercepted; this script consumes no live weather quota.
"""
from __future__ import annotations

import os
from datetime import date
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from playwright.sync_api import sync_playwright
from screenshots import PARIS, _payload, free_port, results_url, serve

from weather_simulator.sources.series import today_in_reference_zone


def main() -> None:
    port = free_port()
    server = serve(port)
    today = today_in_reference_zone()
    primary = today.year + 4
    missing = today.year + 3
    out = Path("/tmp/weather-means-offline")
    out.mkdir(exist_ok=True)
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel=os.environ.get("CLIMATE_BROWSER_CHANNEL"))
            context = browser.new_context(viewport={"width": 1280, "height": 1000})
            page = context.new_page()
            calls, errors = [], []
            fail_next = [False]
            page.on("pageerror", lambda error: errors.append(str(error)))

            def upstream(route):
                url = route.request.url
                calls.append(url)
                if fail_next[0]:
                    fail_next[0] = False
                    route.fulfill(status=429, json={"reason": "Offline rate-limit fixture"})
                    return
                payload = _payload(url, today, 6)
                start = parse_qs(urlsplit(url).query)["start_date"][0]
                if start == f"{missing}-07-01":
                    values = payload["daily"]["temperature_2m_min"]
                    payload["daily"]["temperature_2m_min"] = [
                        value if index % 2 else None for index, value in enumerate(values)
                    ]
                route.fulfill(json=payload)

            context.route("**://*.open-meteo.com/**", upstream)
            page.goto(results_url(f"http://127.0.0.1:{port}", PARIS,
                                  date(primary, 7, 1), date(primary, 7, 31)))
            page.wait_for_selector("#climate:not([hidden])")
            assert len(calls) == 1
            assert page.locator(".heat-counts").is_hidden()
            assert page.evaluate("""() => Boolean(document.querySelector('#comparison')
                .compareDocumentPosition(document.querySelector('#climate')) & Node.DOCUMENT_POSITION_FOLLOWING)""")
            page.click("#climate-start")
            page.wait_for_function("document.querySelector('#climate-status').textContent.startsWith('2 /')")
            page.click("#climate-stop")
            page.wait_for_selector("#climate-stop[hidden]", state="attached", timeout=60_000)
            stopped = len(calls)
            page.wait_for_timeout(1300)
            assert len(calls) == stopped
            page.click("#climate-start")
            page.wait_for_function("document.querySelector('#climate-status').textContent.startsWith('20 /')", timeout=120_000)
            page.wait_for_function("document.querySelectorAll('.climate-card')[1].textContent.includes('9/10')")
            assert page.locator("#climate-warning").is_visible()
            assert page.locator(".climate-chart").count() == 1
            assert page.locator(".climate-chart .simulated").count() > 0
            assert page.locator(".climate-card").nth(1).locator(".climate-metric strong").nth(1).inner_text() == "—"
            before = len(calls)
            page.locator("#climate-annual details summary").click()
            page.locator("#climate-table button").filter(has_text=str(primary + 1)).click()
            assert page.locator(".year-panel").count() == 2
            assert len(calls) == before
            page.locator("#climate-annual details summary").click()
            page.locator("#climate").screenshot(path=str(out / "desktop.png"))
            page.set_viewport_size({"width": 360, "height": 1000})
            page.locator("#climate").screenshot(path=str(out / "mobile.png"))
            assert page.evaluate("document.body.scrollWidth <= innerWidth")
            print("Loading, stop/resume, missing coverage and calendar-first layout passed.", flush=True)
            page.reload()
            page.wait_for_selector("#climate:not([hidden])")
            page.click("#climate-start")
            page.wait_for_function("document.querySelector('#climate-status').textContent.startsWith('20 /')", timeout=60_000)
            assert len(calls) == before, "cached raw responses were fetched again across visits"
            # A new place has no cache. Keep its original year, then interrupt
            # the batch with a quota error and check that resume sends no retry.
            url = results_url(f"http://127.0.0.1:{port}", {**PARIS, "lat": "47.1"},
                              date(today.year - 1, 7, 1), date(today.year - 1, 7, 31))
            page.goto(url)
            page.wait_for_selector("#climate:not([hidden])")
            assert not page.locator("#climate-warning").is_visible()
            fail_next[0] = True
            page.click("#climate-start")
            page.wait_for_selector("#climate-error:not([hidden])")
            failed = len(calls)
            assert page.locator(".year-panel").count() == 1
            page.click("#climate-start")
            page.wait_for_selector("#climate-error:not([hidden])")
            assert len(calls) == failed
            assert not errors, errors
            print(f"Offline comparison check passed. {len(calls)} invented upstream responses; screenshots: {out}")
            browser.close()
    finally:
        server.terminate()
        server.wait()


if __name__ == "__main__":
    main()
