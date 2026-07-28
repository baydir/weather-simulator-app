// results.js
// Orchestrates the results page: reads the URL, geocodes the location,
// fetches weather data (client-side), sends it for processing, and
// displays the outcome. Rendering is intentionally basic for now — it
// will be replaced by the Chart.js view in a later step.

import { getWeatherData } from "./weather-api.js";

const container = document.getElementById("results-container");

function showError(message) {
    container.textContent = message;
}

function renderTable(data) {
    const table = document.createElement("table");
    table.border = "1";

    const header = table.insertRow();
    ["Date", "Température min (°C)", "Température max (°C)", "Précipitations (mm)"]
        .forEach(text => {
            const cell = header.insertCell();
            cell.textContent = text;
        });

    data.forEach(day => {
        const row = table.insertRow();
        [day.date, day.temperature_2m_min, day.temperature_2m_max, day.precipitation_sum]
            .forEach(value => {
                const cell = row.insertCell();
                cell.textContent = value;
            });
    });

    container.innerHTML = "";
    container.appendChild(table);
}

async function main() {
    const params = new URLSearchParams(window.location.search);
    const location = params.get("location");
    const startDate = params.get("start_date");
    const endDate = params.get("end_date");
    const model = params.get("model") || "CMCC_CM2_VHR4";
    const today = document.body.dataset.today;

    if (!location || !startDate || !endDate) {
        showError("Paramètres de recherche manquants.");
        return;
    }

    const geocodeResponse = await fetch(`/api/geocode?location=${encodeURIComponent(location)}`);
    const geocodeData = await geocodeResponse.json();
    if (geocodeData.error) {
        showError(geocodeData.error);
        return;
    }

    document.getElementById("page-title").textContent = `Météo à ${location}`;

    const raw = await getWeatherData(
        geocodeData.latitude, geocodeData.longitude,
        startDate, endDate, today, model
    );

    const processResponse = await fetch("/api/process", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ archive: raw.archive, climate: raw.climate, model }),
    });
    const processData = await processResponse.json();
    if (processData.error) {
        showError(processData.error);
        return;
    }

    renderTable(processData);
}

main();