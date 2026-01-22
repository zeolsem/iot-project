#!/usr/bin/env python3
"""
Measurement Station Sender

Reads sensors and sends data via MQTT to the central hub.
Runs on the edge nodes (measuring stations).
"""

import argparse
import signal
import sys
import threading
from datetime import datetime
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))
from MQTTwrapper import MQTTSender
from measurement.sensors import DS18B20Sensor, DHT11Sensor, BME280Sensor


TOPIC = "weather/readings"


class MeasurementSender:
    """Reads sensors and sends data via MQTT."""
    
    def __init__(
        self,
        broker_address: str,
        station_id: str,
        measure_interval: float = 5.0,
        use_bme280: bool = True,
        dht_pin: int = 16
    ):
        self.station_id = station_id
        self.measure_interval = measure_interval
        self.use_bme280 = use_bme280
        self.dht_pin = dht_pin
        
        # MQTT sender
        self.sender = MQTTSender(
            broker_address=broker_address,
            topic=TOPIC,
            client_id=station_id
        )
        
        # Sensors
        self._ds18b20 = DS18B20Sensor()
        self._humidity_sensor = None
        
        # Threading
        self._stop_event = threading.Event()
        self._measure_thread: threading.Thread | None = None
        
        # Stats
        self._readings_count = 0
        self._sent_count = 0
    
    def _init_sensors(self) -> bool:
        """Initialize all sensors."""
        ds18_ok = self._ds18b20.init()
        
        if self.use_bme280:
            self._humidity_sensor = BME280Sensor()
        else:
            self._humidity_sensor = DHT11Sensor(self.dht_pin)
        
        humidity_ok = self._humidity_sensor.init()
        
        return ds18_ok or humidity_ok
    
    def start(self) -> bool:
        """Start the measurement sender."""
        print("=" * 50)
        print("MEASUREMENT STATION SENDER")
        print("=" * 50)
        print(f"Station ID: {self.station_id}")
        print(f"Broker: {self.sender.broker_address}")
        print(f"Topic: {TOPIC}")
        print(f"Measure interval: {self.measure_interval}s")
        print(f"Humidity sensor: {'BME280' if self.use_bme280 else 'DHT11'}")
        print("=" * 50)
        
        # Initialize sensors
        if not self._init_sensors():
            print("[FATAL] No sensors available. Exiting.")
            return False
        
        # Connect to MQTT broker
        if not self.sender.connect():
            print("[ERR] Failed to connect to broker")
            return False
        
        # Start measurement thread
        self._stop_event.clear()
        self._measure_thread = threading.Thread(
            target=self._measurement_loop,
            name="MeasurementThread",
            daemon=True
        )
        self._measure_thread.start()
        
        print("\n[INFO] Sender started. Press Ctrl+C to stop.\n")
        return True
    
    def stop(self):
        """Stop the sender gracefully."""
        print("\n[INFO] Stopping sender...")
        
        self._stop_event.set()
        
        if self._measure_thread and self._measure_thread.is_alive():
            self._measure_thread.join(timeout=2.0)
        
        self.sender.disconnect()
        
        self._ds18b20.cleanup()
        if self._humidity_sensor:
            self._humidity_sensor.cleanup()
        
        print(f"\n[STATS] Total readings: {self._readings_count}")
        print(f"[STATS] Total sent: {self._sent_count}")
        print("[DONE] Sender stopped.")
    
    def wait(self):
        """Block until stop event is set."""
        try:
            while not self._stop_event.is_set():
                self._stop_event.wait(timeout=0.5)
        except KeyboardInterrupt:
            pass
    
    def _measurement_loop(self):
        """Periodically read sensors and send via MQTT."""
        while not self._stop_event.wait(timeout=self.measure_interval):
            reading = self._take_reading()
            if reading:
                self._send_reading(reading)
    
    def _take_reading(self) -> dict | None:
        """Take a single sensor reading."""
        ds_temp = self._ds18b20.read_temperature()
        
        humid_temp, humidity = None, None
        if self._humidity_sensor:
            humid_temp, humidity = self._humidity_sensor.read()
        
        temperature = ds_temp if ds_temp is not None else humid_temp
        
        if temperature is None and humidity is None:
            return None
        
        self._readings_count += 1
        
        return {
            "temperature": temperature,
            "humidity": humidity,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    
    def _send_reading(self, reading: dict):
        """Send a reading via MQTT."""
        if self.sender.send_message(reading):
            self._sent_count += 1
            temp_str = f"{reading['temperature']:.2f}°C" if reading['temperature'] else "N/A"
            hum_str = f"{reading['humidity']:.1f}%" if reading['humidity'] else "N/A"
            print(f"[{reading['timestamp']}] Sent: Temp={temp_str}, Humidity={hum_str}")


def main():
    parser = argparse.ArgumentParser(
        description="Measurement Station Sender - reads sensors and sends via MQTT",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        "-b", "--broker",
        type=str,
        default="192.168.0.252",
        help="MQTT broker address"
    )
    parser.add_argument(
        "-s", "--station-id",
        type=str,
        default="station_1",
        help="Station identifier"
    )
    parser.add_argument(
        "-m", "--measure-interval",
        type=float,
        default=5.0,
        help="Interval between measurements in seconds"
    )
    parser.add_argument(
        "--dht11",
        action="store_true",
        help="Use DHT11 instead of BME280 for humidity"
    )
    parser.add_argument(
        "--dht-pin",
        type=int,
        default=16,
        help="GPIO pin for DHT11 sensor"
    )
    
    args = parser.parse_args()
    
    sender = MeasurementSender(
        broker_address=args.broker,
        station_id=args.station_id,
        measure_interval=args.measure_interval,
        use_bme280=not args.dht11,
        dht_pin=args.dht_pin
    )
    
    def signal_handler(sig, frame):
        sender.stop()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    if sender.start():
        sender.wait()
        sender.stop()


if __name__ == "__main__":
    main()
