"""Failures worth distinguishing when talking to Open-Meteo."""

from __future__ import annotations


class SourceError(Exception):
    """Base class for every failure raised by this package."""


class CoverageError(SourceError):
    """The requested range falls outside what the sources cover."""


class FetchError(SourceError):
    """The request did not come back with a usable payload."""


class MissingVariableError(SourceError):
    """A requested variable came back entirely null.

    The Climate API answers HTTP 200 with null values and an ``undefined`` unit
    for variables it does not serve; ERA5-Land does the same for everything
    that is not temperature. The absence is silent, so it has to be detected
    explicitly — trusting the status code is exactly the trap.
    """

    def __init__(self, variable: str, source: str) -> None:
        super().__init__(f"{source} returned no value at all for {variable!r}")
        self.variable = variable
        self.source = source
