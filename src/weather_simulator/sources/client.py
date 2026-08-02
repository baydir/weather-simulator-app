"""A small HTTP client for the offline tooling.

The standard library is enough here, as the verification scripts already
demonstrate, and it keeps the package free of a runtime dependency that the
request path would never use anyway.

Rate limiting is the one thing worth handling: Open-Meteo limits per IP
address, and the limit was reached repeatedly during the preparatory work from
a single machine. A 429 or a 503 is therefore retried with a growing pause
rather than treated as a failure.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from typing import Any

from weather_simulator.sources.errors import FetchError

DEFAULT_TIMEOUT = 180
DEFAULT_RETRIES = 4
DEFAULT_BACKOFF = 25

RATE_LIMITED = (429, 503)


def get_json(
    url: str,
    params: dict[str, object],
    *,
    timeout: int = DEFAULT_TIMEOUT,
    retries: int = DEFAULT_RETRIES,
    backoff: int = DEFAULT_BACKOFF,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    """GET ``url`` with ``params`` and return the decoded payload."""
    query = urllib.parse.urlencode(params, doseq=True)
    target = f"{url}?{query}"

    last: Exception | None = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(target, timeout=timeout) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            last = error
            if error.code in RATE_LIMITED and attempt < retries - 1:
                sleep(backoff * (attempt + 1))
                continue
            # Open-Meteo puts a usable explanation in the error body.
            detail = _reason(error)
            raise FetchError(f"HTTP {error.code} from {url}: {detail}") from error
        except (urllib.error.URLError, TimeoutError) as error:
            last = error
            if attempt < retries - 1:
                sleep(backoff * (attempt + 1))
                continue
            raise FetchError(f"{url} unreachable: {error}") from error

    raise FetchError(f"{url} gave up after {retries} attempts: {last}")


def _reason(error: urllib.error.HTTPError) -> str:
    try:
        body = json.load(error)
    except Exception:
        return error.reason or "no detail"
    return str(body.get("reason") or body)
