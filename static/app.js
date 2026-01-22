
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

const stationColorMap = {};

async function fetchJson(url) {
    const r = await fetch(url);
    return await r.json();
}

async function loadStations() {
    const data = await fetchJson('/api/stations');
    const sel = document.getElementById('stationSelect');

    sel.innerHTML = '<option value="all">Wszystkie stacje</option>';

    data.stations.forEach((s, index) => {
        const opt = document.createElement('option');
        opt.value = s;
        opt.textContent = s;
        sel.appendChild(opt);

        stationColorMap[s] = colorPalette[index % colorPalette.length];
    });
}

async function refresh() {
    const station = document.getElementById('stationSelect').value;
    const range = document.getElementById('rangeSelect').value;

    try {
        const apiUrl = `/api/readings?range=${encodeURIComponent(range)}&station=${encodeURIComponent(station)}`;
        const payload = await fetchJson(apiUrl);
        const readings = payload.readings;

        // Grupowanie po station_id
        const groups = {};
        readings.forEach(r => {
            if (!groups[r.station_id]) groups[r.station_id] = { x: [], t: [], h: [] };
            groups[r.station_id].x.push(r.timestamp);
            groups[r.station_id].t.push(r.temperature);
            groups[r.station_id].h.push(r.humidity);
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
        const tempTraces = Object.keys(groups).map(k => ({
            x: groups[k].x.map(s => new Date(s)),
            y: groups[k].t,
            mode: 'lines',
            line: {
                width: 3,
                shape: 'spline',
                color: stationColorMap[k]
            },
            name: k
        }));

        Plotly.react('tempPlot', tempTraces, {
            ...commonLayout,
            yaxis: { ...commonLayout.yaxis, title: 'Stopnie Celsjusza (°C)' }
        }, { responsive: true });

        // WILGOTNOŚĆ
        const humTraces = Object.keys(groups).map(k => ({
            x: groups[k].x.map(s => new Date(s)),
            y: groups[k].h,
            mode: 'lines',
            line: {
                width: 3,
                shape: 'spline',
                color: stationColorMap[k]
            },
            name: k
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
    } finally {
        btn.textContent = originalText;
        btn.disabled = false;
    }
}

window.addEventListener('load', async () => {
    await loadStations();

    document.getElementById('stationSelect').addEventListener('change', refresh);
    document.getElementById('rangeSelect').addEventListener('change', refresh);

    setInterval(refresh, 1000);
    refresh();
});