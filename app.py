#!/usr/bin/env python3
from flask import Flask, jsonify, request, render_template, send_from_directory
from flask_cors import CORS
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

from WeatherDatabase import WeatherDatabase

load_dotenv()

DB_PATH = os.getenv('WEATHER_DB_PATH', 'weather_data.db')
LISTEN_HOST = os.getenv('HOST', '0.0.0.0')
LISTEN_PORT = int(os.getenv('PORT', 5000))

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)

db = WeatherDatabase(db_file=DB_PATH)


def parse_range_param(range_str: str):

    end = datetime.now()
    if not range_str or range_str == '1m':
        start = end - timedelta(minutes=1)
    elif range_str.endswith('m'):
        minutes = int(range_str[:-1])
        start = end - timedelta(minutes=minutes)
    elif range_str.endswith('h'):
        hours = int(range_str[:-1])
        start = end - timedelta(hours=hours)
    elif range_str.endswith('d'):
        days = int(range_str[:-1])
        start = end - timedelta(days=days)
    elif range_str == 'all':
        # None oznacza brak ograniczenia
        return None, end.strftime("%Y-%m-%d %H:%M:%S")
    else:
        # próbujemy sparsować jako ISO datę start; end może być podany przez param end
        try:
            start = datetime.fromisoformat(range_str)
        except Exception:
            # fallback do 1h
            start = end - timedelta(hours=1)
    return start.strftime("%Y-%m-%d %H:%M:%S"), end.strftime("%Y-%m-%d %H:%M:%S")


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/stations')
def api_stations():
    station_ids = db.get_station_ids()
    return jsonify({'stations': station_ids})


@app.route('/api/readings')
def api_readings():
    station = request.args.get('station')  # jeśli None lub 'all' -> wszystkie
    range_q = request.args.get('range', '1m')
    start_end = parse_range_param(range_q)

    if start_end is None:
        start_time = None
        end_time = None
    else:
        start_time, end_time = start_end

    if station and station != 'all':
        rows = db.get_readings(station_id=station, start_time=start_time, end_time=end_time)
    else:
        rows = db.get_readings(start_time=start_time, end_time=end_time)

    rows.sort(key=lambda x: x['timestamp'])
    # keep response shape compatible with frontend
    shaped = [
        {
            'station_id': r['station_id'],
            'temperature': r.get('temperature'),
            'humidity': r.get('humidity'),
            'timestamp': r['timestamp'],
        }
        for r in rows
    ]
    return jsonify({'readings': shaped})


@app.route('/api/average')
def api_average():
    # oblicza średnią temperaturę i wilgotność w zadanym zakresie
    range_q = request.args.get('range', '1m')
    start_end = parse_range_param(range_q)
    if start_end is None:
        start_time = None
        end_time = None
    else:
        start_time, end_time = start_end

    rows = db.get_readings(start_time=start_time, end_time=end_time)

    temps = [r.get('temperature') for r in rows if r.get('temperature') is not None]
    hums = [r.get('humidity') for r in rows if r.get('humidity') is not None]

    avg_t = sum(temps) / len(temps) if temps else None
    avg_h = sum(hums) / len(hums) if hums else None

    return jsonify({'avg_temperature': avg_t, 'avg_humidity': avg_h, 'count': len(rows)})


if __name__ == '__main__':
    print(f"Starting Flask app on {LISTEN_HOST}:{LISTEN_PORT}, DB={DB_PATH}")
    app.run(host=LISTEN_HOST, port=LISTEN_PORT, debug=False)