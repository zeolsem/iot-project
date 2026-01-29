import sqlite3
from datetime import datetime


class WeatherDatabase:
    def __init__(self, db_file='weather_data.db'):
        self.db_file = db_file
        self._create_tables()

    def _create_tables(self):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS temperature_measurements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                station_id TEXT,
                sensor_id TEXT,
                value REAL,
                timestamp TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS humidity_measurements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                station_id TEXT,
                sensor_id TEXT,
                value REAL,
                timestamp TEXT
            )
        ''')

        conn.commit()
        conn.close()
        print("Database and tables ensured.")

    @staticmethod
    def _now():
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def insert_temperature(self, station_id, sensor_id, value, timestamp=None):
        ts = timestamp or self._now()
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute(
            '''INSERT INTO temperature_measurements (station_id, sensor_id, value, timestamp)
               VALUES (?, ?, ?, ?)''',
            (station_id, sensor_id, value, ts),
        )
        conn.commit()
        conn.close()

    def insert_humidity(self, station_id, sensor_id, value, timestamp=None):
        ts = timestamp or self._now()
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute(
            '''INSERT INTO humidity_measurements (station_id, sensor_id, value, timestamp)
               VALUES (?, ?, ?, ?)''',
            (station_id, sensor_id, value, ts),
        )
        conn.commit()
        conn.close()

    def insert_temps_bulk(self, rows):
        if not rows:
            return 0
        prepared = []
        for r in rows:
            ts = r.get('timestamp') or self._now()
            prepared.append((r.get('station_id'), r.get('sensor_id'), r.get('value'), ts))
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.executemany(
            '''INSERT INTO temperature_measurements (station_id, sensor_id, value, timestamp)
               VALUES (?, ?, ?, ?)''',
            prepared,
        )
        conn.commit()
        conn.close()
        return len(prepared)

    def insert_hums_bulk(self, rows):
        if not rows:
            return 0
        prepared = []
        for r in rows:
            ts = r.get('timestamp') or self._now()
            prepared.append((r.get('station_id'), r.get('sensor_id'), r.get('value'), ts))
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.executemany(
            '''INSERT INTO humidity_measurements (station_id, sensor_id, value, timestamp)
               VALUES (?, ?, ?, ?)''',
            prepared,
        )
        conn.commit()
        conn.close()
        return len(prepared)

    def _fetch_measurements(self, table, station_id=None, start_time=None, end_time=None):
        clauses = []
        params = []
        if station_id:
            clauses.append("station_id = ?")
            params.append(station_id)
        if start_time and end_time:
            clauses.append("timestamp BETWEEN ? AND ?")
            params.extend([start_time, end_time])
        elif start_time:
            clauses.append("timestamp >= ?")
            params.append(start_time)
        elif end_time:
            clauses.append("timestamp <= ?")
            params.append(end_time)

        query = f"SELECT station_id, sensor_id, value, timestamp FROM {table}"
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY timestamp DESC"

        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        return rows

    def _merge_temp_hum(self, temps, hums):
        merged = {}
        for station_id, sensor_id, val, ts in temps:
            key = (station_id, ts)
            merged.setdefault(
                key,
                {
                    'station_id': station_id,
                    'timestamp': ts,
                    'temperature': None,
                    'humidity': None,
                    'temperature_sensor_id': None,
                    'humidity_sensor_id': None,
                },
            )
            merged[key]['temperature'] = val
            merged[key]['temperature_sensor_id'] = sensor_id

        for station_id, sensor_id, val, ts in hums:
            key = (station_id, ts)
            merged.setdefault(
                key,
                {
                    'station_id': station_id,
                    'timestamp': ts,
                    'temperature': None,
                    'humidity': None,
                    'temperature_sensor_id': None,
                    'humidity_sensor_id': None,
                },
            )
            merged[key]['humidity'] = val
            merged[key]['humidity_sensor_id'] = sensor_id

        # return sorted ascending by timestamp
        return sorted(merged.values(), key=lambda x: x['timestamp'])

    def get_readings(self, station_id=None, start_time=None, end_time=None):
        temps = self._fetch_measurements('temperature_measurements', station_id, start_time, end_time)
        hums = self._fetch_measurements('humidity_measurements', station_id, start_time, end_time)
        return self._merge_temp_hum(temps, hums)

    def get_all_readings(self):
        return self.get_readings()

    def get_readings_by_station(self, station_id):
        return self.get_readings(station_id=station_id)

    def get_latest_reading(self, station_id):
        rows = self.get_readings(station_id=station_id)
        return rows[-1] if rows else None

    def get_readings_in_time_range(self, station_id, start_time, end_time):
        return self.get_readings(station_id=station_id, start_time=start_time, end_time=end_time)

    def delete_readings_older_than(self, cutoff_time):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM temperature_measurements WHERE timestamp < ?', (cutoff_time,))
        deleted_t = cursor.rowcount
        cursor.execute('DELETE FROM humidity_measurements WHERE timestamp < ?', (cutoff_time,))
        deleted_h = cursor.rowcount
        conn.commit()
        conn.close()
        print(f"Deleted {deleted_t} temperature and {deleted_h} humidity readings older than {cutoff_time}.")
        return deleted_t + deleted_h

    def get_station_ids(self):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute('SELECT DISTINCT station_id FROM temperature_measurements')
        temps = {r[0] for r in cursor.fetchall()}
        cursor.execute('SELECT DISTINCT station_id FROM humidity_measurements')
        hums = {r[0] for r in cursor.fetchall()}
        conn.close()
        return sorted(temps.union(hums))

    def get_counts(self):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM temperature_measurements')
        t = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM humidity_measurements')
        h = cursor.fetchone()[0]
        conn.close()
        return {'temperature': t, 'humidity': h}