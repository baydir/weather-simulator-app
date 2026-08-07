"""Weather Simulator — daily weather simulation from 1950 to 2050.

The package is split along the boundaries set in docs/application.md:

- ``domain``       sky class, thresholds, bias correction rules
- ``transform``    transformation block, a no-op by default
- ``api``          HTTP endpoint and input validation
- ``calibration``  correction grid and interpolation
"""

__version__ = "0.1.0"
