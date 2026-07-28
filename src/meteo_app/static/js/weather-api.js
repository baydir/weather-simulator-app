// weather-api.js
// Handles all communication with the Open-Meteo APIs (archive + climate).
// Mirrors the branching logic in get_meteo.py, but runs in the browser.

const ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive";
const CLIMATE_URL = "https://climate-api.open-meteo.com/v1/climate";
const DAILY_VARIABLES = "temperature_2m_max,temperature_2m_min,precipitation_sum";
const MAX_PROJECTED_DATE = "2050-12-31";

/**
 * Fetches past weather data (ERA5 reanalysis) for a date range.
 * @returns {Promise<Object>} raw JSON from the archive API
 */
async function fetchArchive(latitude, longitude, startDate, endDate) {
    const url = `${ARCHIVE_URL}?latitude=${latitude}&longitude=${longitude}` +
                `&start_date=${startDate}&end_date=${endDate}` +
                `&daily=${DAILY_VARIABLES}&timezone=Europe/Paris`;
    const response = await fetch(url);
    return response.json();
}

/**
 * Fetches projected weather data (CMIP6 model) for a date range.
 * @returns {Promise<Object>} raw JSON from the climate API
 */
async function fetchClimate(latitude, longitude, startDate, endDate, model) {
    const cappedEndDate = endDate > MAX_PROJECTED_DATE ? MAX_PROJECTED_DATE : endDate;
    const url = `${CLIMATE_URL}?latitude=${latitude}&longitude=${longitude}` +
                `&start_date=${startDate}&end_date=${cappedEndDate}` +
                `&models=${model}&daily=${DAILY_VARIABLES}&timezone=Europe/Paris`;
    const response = await fetch(url);
    return response.json();
}

/**
 * Adds one day to a "YYYY-MM-DD" string, working entirely in UTC to avoid
 * timezone-related off-by-one bugs (see explanation below).
 */
function addOneDay(dateString) {
    const date = new Date(dateString + "T00:00:00Z");
    date.setUTCDate(date.getUTCDate() + 1);
    return date.toISOString().split("T")[0];
}

/**
 * Decides which API(s) to call based on the date range and today's date,
 * mirroring the branching logic in get_meteo.py.
 *
 * @param {string} today - today's date as "YYYY-MM-DD", provided by the
 *   server (Flask), so every visitor shares the same reference regardless
 *   of their own browser's timezone.
 * @returns {Promise<{archive: Object|null, climate: Object|null}>}
 */
export async function getWeatherData(latitude, longitude, startDate, endDate, today, model) {
    const result = { archive: null, climate: null };
    const pendingCalls = [];

    if (startDate <= today) {
        const archiveEndDate = endDate < today ? endDate : today;
        pendingCalls.push(
            fetchArchive(latitude, longitude, startDate, archiveEndDate)
                .then(json => { result.archive = json; })
        );
    }

    if (endDate > today) {
        const climateStartDate = startDate > today ? startDate : addOneDay(today);
        pendingCalls.push(
            fetchClimate(latitude, longitude, climateStartDate, endDate, model)
                .then(json => { result.climate = json; })
        );
    }

    await Promise.all(pendingCalls);
    return result;
}