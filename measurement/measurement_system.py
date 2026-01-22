"""Main measurement system that coordinates sensor readings and database writes."""

import sqlite3
import threading
from datetime import datetime
from queue import Queue

from .config import Config
from .models import SensorReading
from .sensors import DS18B20Sensor, DHT11Sensor, BME280Sensor

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from WeatherDatabase import WeatherDatabase


class MeasurementSystem:
    """
    Main measurement system that coordinates sensor readings and database writes.
    Uses threading events for timing instead of sleep.
    """
    
    def __init__(self, config: Config):
        self.config = config
        
        # Sensors
        self._ds18b20 = DS18B20Sensor()
        self._humidity_sensor = None
        
        # Database
        self._db = WeatherDatabase(config.db_file)
        
        # Reading queue for batch inserts
        self._reading_queue: Queue[SensorReading] = Queue()
        
        # Threading control
        self._stop_event = threading.Event()
        self._measure_thread: threading.Thread | None = None
        self._batch_thread: threading.Thread | None = None
        
        # Statistics
        self._readings_count = 0
        self._inserts_count = 0
    
    def _init_humidity_sensor(self) -> bool:
        """Init the appropriate humidity sensor based on config."""
        if self.config.use_bme280:
            self._humidity_sensor = BME280Sensor()
        else:
            self._humidity_sensor = DHT11Sensor(self.config.dht_pin)
        
        return self._humidity_sensor.init()
    
    def start(self) -> bool:
        print("=" * 50)
        """Start the measurements."""
        print("=" * 50)
        print(f"Station ID: {self.config.station_id}")
        print(f"Measure interval: {self.config.measure_interval}s")
        print(f"Batch insert interval: {self.config.batch_interval}s")
        print(f"Humidity sensor: {'BME280' if self.config.use_bme280 else 'DHT11'}")
        print("=" * 50)
        
        # Initialize sensors
        ds18_ok = self._ds18b20.init()
        humidity_ok = self._init_humidity_sensor()
        
        if not ds18_ok and not humidity_ok:
            print("[FATAL] No sensors available. Exiting.")
            return False
        
        # Start worker threads
        self._stop_event.clear()
        
        self._measure_thread = threading.Thread(
            target=self._measurement_loop,
            name="MeasurementThread",
            daemon=True
        )
        self._measure_thread.start()
        
        self._batch_thread = threading.Thread(
            target=self._batch_insert_loop,
            name="BatchInsertThread",
            daemon=True
        )
        self._batch_thread.start()
        
        print("\n[INFO] System started. Press Ctrl+C to stop.\n")
        return True
    
    def stop(self) -> None:
        """Stop the measurement system gracefully."""
        print("\n[INFO] Stopping measurement system...")
        
        # Signal threads to stop
        self._stop_event.set()
        
        # Wait for threads to finish
        if self._measure_thread and self._measure_thread.is_alive():
            self._measure_thread.join(timeout=2.0)
        
        if self._batch_thread and self._batch_thread.is_alive():
            self._batch_thread.join(timeout=2.0)
        
        # Flush remaining readings to database
        self._flush_queue()
        
        # Cleanup sensors
        self._ds18b20.cleanup()
        if self._humidity_sensor:
            self._humidity_sensor.cleanup()
        
        print(f"\n[STATS] Total readings: {self._readings_count}")
        print(f"[STATS] Total batch inserts: {self._inserts_count}")
        print("[DONE] System stopped. Goodbye.")
    
    def wait(self) -> None:
        """Wait for the system to be stopped (blocking)."""
        try:
            while not self._stop_event.is_set():
                self._stop_event.wait(timeout=0.5)
        except KeyboardInterrupt:
            pass
    
    def _measurement_loop(self) -> None:
        """Worker thread: Periodically read sensors and queue readings."""
        while not self._stop_event.wait(timeout=self.config.measure_interval):
            reading = self._take_reading()
            if reading:
                self._reading_queue.put(reading)
                self._readings_count += 1
                self._print_reading(reading)
    
    def _batch_insert_loop(self) -> None:
        """Worker thread: Periodically flush queue to database."""
        while not self._stop_event.wait(timeout=self.config.batch_interval):
            self._flush_queue()
    
    def _take_reading(self) -> SensorReading | None:
        """Take a single reading from all available sensors."""
        # Read DS18B20 temperature (primary)
        ds_temp = self._ds18b20.read_temperature()
        
        # Read humidity sensor (secondary)
        humid_temp, humidity = None, None
        if self._humidity_sensor:
            humid_temp, humidity = self._humidity_sensor.read()
        
        # Use DS18B20 temp as primary, fallback to humidity sensor temp
        temperature = ds_temp if ds_temp is not None else humid_temp
        
        # Skip if no data available
        if temperature is None and humidity is None:
            return None
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        return SensorReading(
            station_id=self.config.station_id,
            temperature=temperature,
            humidity=humidity,
            timestamp=timestamp
        )
    
    def _flush_queue(self) -> None:
        """Flush all queued readings to database."""
        readings = []
        
        while not self._reading_queue.empty():
            try:
                readings.append(self._reading_queue.get_nowait())
            except Exception:
                break
        
        if not readings:
            return
        
        # Batch insert
        self._batch_insert_readings(readings)
        self._inserts_count += 1
        print(f"[DB] Batch inserted {len(readings)} readings")
    
    def _batch_insert_readings(self, readings: list[SensorReading]) -> None:
        """Insert multiple readings into database efficiently."""
        conn = sqlite3.connect(self._db.db_file)
        cursor = conn.cursor()
        
        try:
            cursor.executemany(
                '''INSERT INTO weather_readings (station_id, temperature, humidity, timestamp)
                   VALUES (?, ?, ?, ?)''',
                [(r.station_id, r.temperature, r.humidity, r.timestamp) for r in readings]
            )
            conn.commit()
        except Exception as e:
            print(f"[DB ERROR] Batch insert failed: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def _print_reading(self, reading: SensorReading) -> None:
        """Print a reading to console."""
        parts = [f"[{reading.timestamp}]"]
        
        if reading.temperature is not None:
            parts.append(f"Temp: {reading.temperature:.2f}°C")
        
        if reading.humidity is not None:
            parts.append(f"Humidity: {reading.humidity:.1f}%")
        
        parts.append(f"(Queue: {self._reading_queue.qsize()})")
        
        print(" | ".join(parts))
