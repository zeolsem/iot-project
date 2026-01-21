import sqlite3
from datetime import datetime

class WeatherDatabase:
    def __init__(self, db_file='weather_data.db'):
        self.db_file = db_file
        self._create_table()
        
    def _create_table(self):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS weather_readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                station_id TEXT,
                temperature REAL,
                humidity REAL,
                timestamp TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
        print("Database and table created successfully.")
        
    def insert_reading(self, station_id, temperature, humidity, timestamp=None):
        if timestamp is None:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
       INSERT INTO weather_readings (station_id, temperature, humidity, timestamp)
            VALUES (?, ?, ?, ?)
        ''', (station_id, temperature, humidity, timestamp))
            
        conn.commit()
        conn.close()
        print(f"Inserted reading: {station_id}, {temperature}, {humidity}, {timestamp}")
            
            
    def get_all_readings(self):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM weather_readings ORDER BY timestamp DESC')
        rows = cursor.fetchall()
        conn.close()
        return rows

    def get_readings_by_station(self, station_id):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM weather_readings WHERE station_id = ? ORDER BY timestamp DESC', (station_id,))
        rows = cursor.fetchall()
        
        conn.close()
        return rows
        
    def get_latest_reading(self, station_id):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
            
        cursor.execute('''
            SELECT * FROM weather_readings 
            WHERE station_id = ? 
            ORDER BY timestamp DESC 
            LIMIT 1
        ''', (station_id,))
        row = cursor.fetchone()
            
        conn.close()
        return row

    def get_readings_in_time_range(self, station_id, start_time, end_time):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM weather_readings 
            WHERE station_id = ? AND timestamp BETWEEN ? AND ?
        ''', (station_id, start_time, end_time))
        rows = cursor.fetchall()
            
        conn.close()
        return rows
        
    def delete_readings_older_than(self, cutoff_time):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
            
        cursor.execute('DELETE FROM weather_readings WHERE timestamp < ?', (cutoff_time,))
        deleted_count = cursor.rowcount
            
        conn.commit()
        conn.close()
        print(f"Deleted {deleted_count} readings older than {cutoff_time}.")
        return deleted_count