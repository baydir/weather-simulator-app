"""What the client does when the network misbehaves.

No socket is opened: ``urlopen`` is replaced, and the pause is replaced too, so
the retries cost nothing.
"""

from __future__ import annotations

import http.client
import io
import json
import urllib.error
from typing import Any

import pytest

from weather_simulator.sources import client
from weather_simulator.sources.errors import FetchError

PAYLOAD = {"daily": {"time": ["2024-01-01"], "temperature_2m_max": [7.0]}}


class _Response(io.BytesIO):
    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


def _answers(*outcomes: Any):
    """An ``urlopen`` returning — or raising — one outcome per call, in order."""
    remaining = list(outcomes)
    attempts: list[str] = []

    def urlopen(target: str, timeout: int = 0) -> Any:
        attempts.append(target)
        outcome = remaining.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return _Response(json.dumps(outcome).encode())

    return urlopen, attempts


def _get(monkeypatch: pytest.MonkeyPatch, *outcomes: Any, retries: int = 4) -> Any:
    urlopen, attempts = _answers(*outcomes)
    monkeypatch.setattr(client.urllib.request, "urlopen", urlopen)
    result = client.get_json(
        "https://example.test/v1", {"latitude": 46.9}, retries=retries, sleep=lambda _: None
    )
    return result, attempts


def test_returns_the_decoded_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    result, attempts = _get(monkeypatch, PAYLOAD)
    assert result == PAYLOAD
    assert len(attempts) == 1
    assert "latitude=46.9" in attempts[0]


def test_rate_limiting_is_retried(monkeypatch: pytest.MonkeyPatch) -> None:
    limited = urllib.error.HTTPError("u", 429, "Too Many Requests", {}, None)  # type: ignore[arg-type]
    result, attempts = _get(monkeypatch, limited, PAYLOAD)
    assert result == PAYLOAD
    assert len(attempts) == 2


def test_a_dropped_connection_is_retried(monkeypatch: pytest.MonkeyPatch) -> None:
    """The failure that killed a collection run: not a URLError, and not caught.

    ``RemoteDisconnected`` is raised while reading the status line, after the
    request has gone out, so urllib never wraps it. It has to be retried like
    any other transport failure.
    """
    dropped = http.client.RemoteDisconnected("Remote end closed connection without response")
    result, attempts = _get(monkeypatch, dropped, PAYLOAD)
    assert result == PAYLOAD
    assert len(attempts) == 2


def test_transport_failures_leave_as_a_fetch_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Whatever the transport raised, a caller has one exception to catch."""
    for failure in (
        http.client.RemoteDisconnected("closed"),
        urllib.error.URLError("unreachable"),
        ConnectionResetError("reset by peer"),
        TimeoutError("timed out"),
    ):
        with pytest.raises(FetchError):
            _get(monkeypatch, failure, failure, retries=2)


def test_an_http_error_is_not_retried(monkeypatch: pytest.MonkeyPatch) -> None:
    """A 400 means the request is wrong; repeating it would only be slower."""
    body = io.BytesIO(json.dumps({"reason": "Invalid date"}).encode())
    refused = urllib.error.HTTPError("u", 400, "Bad Request", {}, body)  # type: ignore[arg-type]
    urlopen, attempts = _answers(refused, PAYLOAD)
    monkeypatch.setattr(client.urllib.request, "urlopen", urlopen)

    with pytest.raises(FetchError, match="Invalid date"):
        client.get_json("https://example.test/v1", {}, sleep=lambda _: None)
    assert len(attempts) == 1
