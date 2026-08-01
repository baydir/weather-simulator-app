"""HTTP layer: the single processing endpoint and input validation.

The browser fetches the raw data from Open-Meteo itself — Open-Meteo rate-limits
per IP address — and posts it here. The server is stateless and derives
everything the browser displays.
"""
