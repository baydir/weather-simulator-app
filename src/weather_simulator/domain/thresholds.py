"""The numbers the sky class turns on, and where each one comes from.

Values only. The decision tree that reads them belongs to step 3; what matters
here is that every threshold is written once, with its provenance attached, so
that changing one is a deliberate act rather than an edit in passing.
"""

from __future__ import annotations

# The wet gate. A day below this is not a precipitation day, whatever fell.
# Conventional for daily totals, and shared by the snow and rain rules so that
# the two partition the same set of days rather than overlap.
PRECIPITATION_MM = 1.0

# Snow, among wet days: below this daily mean temperature, the precipitation is
# shown as snow.
#
# Calibrated by script 21 over 35 winters at Strasbourg and Briancon, against
# the snow depth the reanalyses actually record — not against weather_code,
# which is the daily maximum of 24 hourly codes and therefore fires on a single
# snowy hour. That inflates snow by 16 points at Strasbourg and saturates
# outright at Briancon, where 999 wet days in 1000 carry a snow code.
#
# At 1.5 degrees: 90% of winter days right at Strasbourg, 82% at Briancon. No
# single value suits both. Above 1300 m snow settles even on days averaging well
# over 2 degrees — it falls at night, or higher up — and a daily mean cannot
# carry that. The rule under-calls snow in the mountains by construction.
#
# Provisional in the same sense as the cloud thresholds below: two sites and one
# season are a thin basis, and the design document says as much of its own
# measurements.
SNOW_TEMPERATURE_C = 1.5

# Cloud cover. Still the values carried over from the design document, to be set
# against the observed distribution so that the frequency of each class stays
# plausible over the historical period. Step 3.
OVERCAST_PERCENT = 70.0
CLOUDY_PERCENT = 30.0

# What the design document originally called a snow day, and what the criterion
# above is calibrated to reproduce. The climate model serves snow depth too
# irregularly to read it directly — hence the derived rule — but the reanalyses
# serve it faithfully, which is what makes the calibration possible at all.
SNOW_DEPTH_CM = 1.0
