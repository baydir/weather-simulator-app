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

# Cloud cover, among dry days — the wet ones are already taken by the two rules
# above, so these two thresholds partition those and nothing else.
#
# Confirmed at step 3, not merely carried over. They were provisional, and the
# obvious yardsticks for settling them both turned out to be traps.
# sunshine_duration overstates real sunshine by a third to a factor of two, the
# error growing with cloudiness; weather_code is the daily maximum of 24 hourly
# codes, calls half of Marseille's dry days overcast, and is circular anyway —
# a deterministic function of cloud cover itself.
#
# What settles them is the light that actually reaches the ground, from
# shortwave radiation over a clear-sky estimate. Script scripts/sky_thresholds/
# measures, over ten sites, that the three classes receive about 90 %, 80 % and
# 60 % of what a clear sky would give. Three clear steps, ordered the same way
# everywhere. No candidate pair did better: raising the overcast bar lowers the
# median but widens the spread by as much.
#
# Where "cloudy" ends and "overcast" begins remains a convention of language
# over a continuum. Measurement cannot place that line; it can only say what
# falls either side of it, which is what these figures do.
OVERCAST_PERCENT = 70.0
CLOUDY_PERCENT = 30.0

# The temperature colour scale: eight boundaries, nine bands.
#
# **Absolute, not an anomaly.** A band depends on the temperature and on nothing
# else — not on the date, not on the place. January is cold and July is warm, and
# the scale says so, which is what the public weather maps do.
#
# **Placed on what France actually recorded**, by scripts/temperature_scale/:
# twelve towns, one per French climate, 1981-2010, ERA5-Land — 131 484 days. The
# reference period is the WMO normal, and it is deliberately a cold one for a
# site that shows the future: at Paris, days at or above 30 °C run to 4.9 a year
# over 1981-2010 and to 21 over 2036-2050 in the climate model. The scale reddens
# as the century advances because the reference does not move.
#
# **The source is the reanalysis, not the record books.** A grid cell smooths
# extremes: no French cell of these thirty years reaches 40 °C, where station
# records do. Boundaries taken from an almanac would be colours the page could
# not display. The top band is therefore the one the reference climate never
# reaches and the simulated future does.
#
# **Nine bands, at five degrees.** Measured on the same data, over a 47-day
# search — the length of a typical one — a step of 10 °C shows 1.9 to 2.8 distinct
# colours and the strip reads as one flat wash; a step of 5 °C shows 2.7 to 4.0.
# Nine is also what a palette can name: dark blue, light blue, light green,
# yellow, orange, light red, dark red, dark violet, light violet. A scale whose
# steps cannot be named is a gradient, and a gradient claims a precision daily
# aggregates do not have.
#
# **Where the ladder starts is what keeps the colours honest.** Running 5 to 40
# rather than 0 to 35 puts each colour where a French reader expects it — yellow
# on 15-20, orange on 20-25, red from 25 — and leaves the top band, which the
# reference climate never reaches, to the heat the simulated future brings. The
# price is a coarse cold end: everything under 5 °C is one colour, which is 7 %
# of French maxima and 28 % of minima.
#
# The bands are a display convention over a continuum, exactly as "cloudy" and
# "overcast" are. Measurement says what falls either side of a line; it cannot
# say where to draw it.
TEMPERATURE_BAND_STEP_C = 5.0
TEMPERATURE_BAND_EDGES = tuple(5.0 + TEMPERATURE_BAND_STEP_C * step for step in range(8))

# What the design document originally called a snow day, and what the criterion
# above is calibrated to reproduce. The climate model serves snow depth too
# irregularly to read it directly — hence the derived rule — but the reanalyses
# serve it faithfully, which is what makes the calibration possible at all.
SNOW_DEPTH_CM = 1.0
