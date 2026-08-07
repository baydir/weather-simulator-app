"""A small HTTP client for the offline tooling.

The standard library is enough here, as the verification scripts already
demonstrate, and it keeps the package free of a runtime dependency that the
request path would never use anyway.

Rate limiting is the one thing worth handling: Open-Meteo limits per IP
address, and the limit was reached repeatedly during the preparatory work from
a single machine. A 429 or a 503 is therefore retried with a growing pause
rather than treated as a failure.

It is not, however, the only way a long request ends badly. A server under
pressure also drops the connection outright, after the request has been sent
and before a status line comes back. That arrives as ``RemoteDisconnected``,
which ``urllib`` does not wrap in a ``URLError`` — it escaped this module
untouched and killed a collection run three quarters of the way through. Every
transport failure is retried here, and whatever survives the retries leaves as
a ``FetchError`` like the rest, so that a caller has one exception to catch.
"""

from __future__ import annotations

import http.client
import json
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Any

from weather_simulator.sources import openmeteo
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
    target = openmeteo.encode(url, params)

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
        # Everything else the transport can raise: a name that will not resolve,
        # a refused or reset connection, a timeout, a reply that is not HTTP.
        # OSError covers URLError and the connection errors; HTTPException
        # covers a malformed or absent status line, which is not an OSError.
        except (OSError, http.client.HTTPException) as error:
            last = error
            if attempt < retries - 1:
                sleep(backoff * (attempt + 1))
                continue
            raise FetchError(f"{url} unreachable: {error!r}") from error

    raise FetchError(f"{url} gave up after {retries} attempts: {last}")


def _reason(error: urllib.error.HTTPError) -> str:
    try:
        body = json.load(error)
    except Exception:
        return error.reason or "no detail"
    return str(body.get("reason") or body)
