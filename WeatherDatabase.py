import sqlite3
from datetime import datetime


class WeatherDatabase:
    """Database for storing sensor readings in separate tables per sensor type."""
    
    def __init__(self, db_file: str = 'weather_data.db'):
        self.db_file = db_file
        self._create_tables()
        
    def _create_tables(self):
        """Create the ds18b20 and bme280 tables."""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ds18b20_readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sensor_id TEXT,
                temperature REAL,
                timestamp TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bme280_readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sensor_id TEXT,
                temperature REAL,
                humidity REAL,
                timestamp TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
        print("[DB] Database tables created successfully.")
    
    def insert_ds18b20(self, sensor_id: str, temperature: float, timestamp: str | None = None):
        """Insert a DS18B20 temperature reading."""
        if timestamp is None:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO ds18b20_readings (sensor_id, temperature, timestamp)
            VALUES (?, ?, ?)
        ''', (sensor_id, temperature, timestamp))
            
        conn.commit()
        conn.close()
    
    def insert_bme280(self, sensor_id: str, temperature: float | None, humidity: float | None, timestamp: str | None = None):
        """Insert a BME280 reading (temperature and/or humidity)."""
        if timestamp is None:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO bme280_readings (sensor_id, temperature, humidity, timestamp)
            VALUES (?, ?, ?, ?)
        ''', (sensor_id, temperature, humidity, timestamp))
            
        conn.commit()
        conn.close()
    
    def insert_batch(self, readings: list[dict]):
        """
        Insert a batch of readings.
        Each reading dict should have: sensor_id, sensor_type, timestamp, and temperature/humidity.
        sensor_id format: "{station_id}_{sensor_type}" e.g. "station_1_ds18b20"
        """
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        ds18b20_count = 0
        bme280_count = 0
        
        try:
            for r in readings:
                sensor_id = r.get("sensor_id", "unknown")
                sensor_type = r.get("sensor_type", "unknown")
                timestamp = r.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                
                if sensor_type == "ds18b20":
                    if r.get("temperature") is not None:
                        cursor.execute('''
                            INSERT INTO ds18b20_readings (sensor_id, temperature, timestamp)
                            VALUES (?, ?, ?)
                        ''', (sensor_id, r["temperature"], timestamp))
                        ds18b20_count += 1
                
                elif sensor_type == "bme280":
                    cursor.execute('''
                        INSERT INTO bme280_readings (sensor_id, temperature, humidity, timestamp)
                        VALUES (?, ?, ?, ?)
                    ''', (sensor_id, r.get("temperature"), r.get("humidity"), timestamp))
                    bme280_count += 1
            
            conn.commit()
            print(f"[DB] Batch inserted: {ds18b20_count} DS18B20, {bme280_count} BME280 readings")
        except Exception as e:
            print(f"[DB ERROR] Batch insert failed: {e}")
            conn.rollback()
        finally:
            conn.close()
        
        return ds18b20_count, bme280_count
    
    def get_ds18b20_readings(self, sensor_id: str | None = None, limit: int = 100):
        """Get DS18B20 readings, optionally filtered by sensor_id."""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        if sensor_id:
            cursor.execute('''
                SELECT * FROM ds18b20_readings 
                WHERE sensor_id = ? 
                ORDER BY timestamp DESC LIMIT ?
            ''', (sensor_id, limit))
        else:
            cursor.execute('SELECT * FROM ds18b20_readings ORDER BY timestamp DESC LIMIT ?', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        return rows
    
    def get_bme280_readings(self, sensor_id: str | None = None, limit: int = 100):
        """Get BME280 readings, optionally filtered by sensor_id."""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        if sensor_id:
            cursor.execute('''
                SELECT * FROM bme280_readings 
                WHERE sensor_id = ? 
                ORDER BY timestamp DESC LIMIT ?
            ''', (sensor_id, limit))
        else:
            cursor.execute('SELECT * FROM bme280_readings ORDER BY timestamp DESC LIMIT ?', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        return rows
    
    def get_latest_ds18b20(self, sensor_id: str):
        """Get the most recent DS18B20 reading for a sensor."""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM ds18b20_readings 
            WHERE sensor_id = ? 
            ORDER BY timestamp DESC LIMIT 1
        ''', (sensor_id,))
        row = cursor.fetchone()
        
        conn.close()
        return row
    
    def get_latest_bme280(self, sensor_id: str):
        """Get the most recent BME280 reading for a sensor."""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM bme280_readings 
            WHERE sensor_id = ? 
            ORDER BY timestamp DESC LIMIT 1
        ''', (sensor_id,))
        row = cursor.fetchone()
        
        conn.close()
        return row
    
    def get_readings_in_time_range(self, table: str, sensor_id: str, start_time: str, end_time: str):
        """Get readings from a table within a time range."""
        if table not in ('ds18b20_readings', 'bme280_readings'):
            raise ValueError("Invalid table name")
        
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute(f'''
            SELECT * FROM {table} 
            WHERE sensor_id = ? AND timestamp BETWEEN ? AND ?
            ORDER BY timestamp DESC
        ''', (sensor_id, start_time, end_time))
        rows = cursor.fetchall()
        
        conn.close()
        return rows
    
    def delete_readings_older_than(self, cutoff_time: str):
        """Delete readings older than cutoff from both tables."""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM ds18b20_readings WHERE timestamp < ?', (cutoff_time,))
        ds18b20_deleted = cursor.rowcount
        
        cursor.execute('DELETE FROM bme280_readings WHERE timestamp < ?', (cutoff_time,))
        bme280_deleted = cursor.rowcount
        
        conn.commit()
        conn.close()
        print(f"[DB] Deleted {ds18b20_deleted} DS18B20, {bme280_deleted} BME280 readings older than {cutoff_time}")
        return ds18b20_deleted, bme280_deleted