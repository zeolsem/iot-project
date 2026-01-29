
const colorPalette = [
    '#1f77b4', // Niebieski
    '#ff7f0e', // Pomarańczowy
    '#2ca02c', // Zielony
    '#d62728', // Czerwony
    '#9467bd', // Fioletowy
    '#8c564b', // Brązowy
    '#e377c2', // Różowy
    '#7f7f7f', // Szary
    '#bcbd22', // Oliwkowy
    '#17becf'  // Cyjan
];

const seriesColorMap = {};

async function fetchJson(url) {
    const r = await fetch(url);
    return await r.json();
}

async function loadStations() {
    const data = await fetchJson('/api/stations');
    const sel = document.getElementById('stationSelect');

    sel.innerHTML = '<option value="all">Wszystkie stacje</option>';

    data.stations.forEach((s) => {
        const opt = document.createElement('option');
        opt.value = s;
        opt.textContent = s;
        sel.appendChild(opt);
    });
}

async function refresh() {
    const station = document.getElementById('stationSelect').value;
    const range = document.getElementById('rangeSelect').value;

    try {
        const apiUrl = `/api/readings?range=${encodeURIComponent(range)}&station=${encodeURIComponent(station)}`;
        const payload = await fetchJson(apiUrl);
        const readings = payload.readings;

        // Grupowanie po (station_id, sensor_id) osobno dla temp i hum
        const tempGroups = {};
        const humGroups = {};

        readings.forEach(r => {
            if (r.temperature !== null && r.temperature !== undefined) {
                const key = `${r.station_id}|temp|${r.temperature_sensor_id || 'unknown'}`;
                if (!tempGroups[key]) tempGroups[key] = { x: [], y: [], label: `${r.temperature_sensor_id || 'temp'}` };
                tempGroups[key].x.push(r.timestamp);
                tempGroups[key].y.push(r.temperature);
            }
            if (r.humidity !== null && r.humidity !== undefined) {
                const key = `${r.station_id}|hum|${r.humidity_sensor_id || 'unknown'}`;
                if (!humGroups[key]) humGroups[key] = { x: [], y: [], label: `${r.humidity_sensor_id || 'hum'}` };
                humGroups[key].x.push(r.timestamp);
                humGroups[key].y.push(r.humidity);
            }
        });

        const commonLayout = {
            margin: { t: 20, r: 20, l: 50, b: 40 },
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(0,0,0,0)',
            hovermode: 'x unified',
            uirevision: 'true',
            xaxis: { showgrid: true, gridcolor: '#e9ecef', automargin: true },
            yaxis: { showgrid: true, gridcolor: '#e9ecef', zeroline: false },
            legend: { orientation: 'h', y: 1.1 }
        };

        // TEMPERATURA
        const tempTraces = Object.keys(tempGroups).map((key, idx) => ({
            x: tempGroups[key].x.map(s => new Date(s)),
            y: tempGroups[key].y,
            mode: 'lines',
            line: {
                width: 3,
                shape: 'spline',
                color: seriesColorMap[key] || (seriesColorMap[key] = colorPalette[idx % colorPalette.length])
            },
            name: tempGroups[key].label
        }));

        Plotly.react('tempPlot', tempTraces, {
            ...commonLayout,
            yaxis: { ...commonLayout.yaxis, title: 'Stopnie Celsjusza (°C)' }
        }, { responsive: true });

        // WILGOTNOŚĆ
        const humTraces = Object.keys(humGroups).map((key, idx) => ({
            x: humGroups[key].x.map(s => new Date(s)),
            y: humGroups[key].y,
            mode: 'lines',
            line: {
                width: 3,
                shape: 'spline',
                color: seriesColorMap[key] || (seriesColorMap[key] = colorPalette[idx % colorPalette.length])
            },
            name: humGroups[key].label
        }));

        Plotly.react('humPlot', humTraces, {
            ...commonLayout,
            yaxis: { ...commonLayout.yaxis, title: 'Procent (%)' }
        }, { responsive: true });

        // STATYSTYKI
        const avg = await fetchJson(`/api/average?range=${encodeURIComponent(range)}`);
        const tempElem = document.getElementById('avgTemp');
        const humElem = document.getElementById('avgHum');

        tempElem.innerText = avg.avg_temperature ? avg.avg_temperature.toFixed(2) + ' °C' : '--';
        humElem.innerText = avg.avg_humidity ? avg.avg_humidity.toFixed(1) + ' %' : '--';

    } catch (error) {
        console.error("Błąd:", error);
    }
}

window.addEventListener('load', async () => {
    await loadStations();

    document.getElementById('stationSelect').addEventListener('change', refresh);
    document.getElementById('rangeSelect').addEventListener('change', refresh);

    setInterval(refresh, 1000);
    refresh();
});