#!/usr/bin/env python3
"""
Measurement Station Sender

Reads sensors and sends batched data via MQTT to the central hub.
Runs on the edge nodes (measuring stations).
"""

import argparse
import signal
import sys
import threading
from datetime import datetime
from pathlib import Path
from queue import Queue

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))
from MQTTwrapper import MQTTSender
from sensors import DS18B20Sensor, DHT11Sensor, BME280Sensor


TOPIC = "weather/readings"


class MeasurementSender:
    """Reads sensors and sends batched data via MQTT."""
    
    def __init__(
        self,
        broker_address: str,
        station_id: str,
        measure_interval: float = 5.0,
        batch_interval: float = 60.0,
        use_bme280: bool = True,
        dht_pin: int = 16,
        bme280_address: int = 0x76
    ):
        self.station_id = station_id
        self.measure_interval = measure_interval
        self.batch_interval = batch_interval
        self.use_bme280 = use_bme280
        self.dht_pin = dht_pin
        self.bme280_address = bme280_address
        
        # MQTT sender
        self.sender = MQTTSender(
            broker_address=broker_address,
            topic=TOPIC,
            client_id=station_id
        )
        
        # Sensors
        self._ds18b20 = DS18B20Sensor()
        self._humidity_sensor = None
        
        # Reading queue for batching
        self._reading_queue: Queue[dict] = Queue()
        
        # Threading
        self._stop_event = threading.Event()
        self._measure_thread: threading.Thread | None = None
        self._batch_thread: threading.Thread | None = None
        
        # Stats
        self._readings_count = 0
        self._batches_sent = 0
    
    def _init_sensors(self) -> bool:
        """Initialize all sensors."""
        ds18_ok = self._ds18b20.init()
        
        if self.use_bme280:
            self._humidity_sensor = BME280Sensor(address=self.bme280_address)
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
        print(f"Central Hub: {self.sender.broker_address}")
        print(f"Topic: {TOPIC}")
        print(f"Measure interval: {self.measure_interval}s")
        print(f"Batch send interval: {self.batch_interval}s")
        print(f"Humidity sensor: {'BME280' if self.use_bme280 else 'DHT11'}")
        print("=" * 50)
        
        # Initialize sensors
        if not self._init_sensors():
            print("[FATAL] No sensors available. Exiting.")
            return False
        
        # Connect to MQTT broker
        if not self.sender.connect():
            print("[ERR] Failed to connect to central hub")
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
            target=self._batch_send_loop,
            name="BatchSendThread",
            daemon=True
        )
        self._batch_thread.start()
        
        print("\n[INFO] Sender started. Press Ctrl+C to stop.\n")
        return True
    
    def stop(self):
        """Stop the sender gracefully."""
        print("\n[INFO] Stopping sender...")
        
        self._stop_event.set()
        
        if self._measure_thread and self._measure_thread.is_alive():
            self._measure_thread.join(timeout=2.0)
        
        if self._batch_thread and self._batch_thread.is_alive():
            self._batch_thread.join(timeout=2.0)
        
        # Send any remaining readings
        self._send_batch()
        
        self.sender.disconnect()
        
        self._ds18b20.cleanup()
        if self._humidity_sensor:
            self._humidity_sensor.cleanup()
        
        print(f"\n[STATS] Total readings: {self._readings_count}")
        print(f"[STATS] Total batches sent: {self._batches_sent}")
        print("[DONE] Sender stopped.")
    
    def wait(self):
        """Block until stop event is set."""
        try:
            while not self._stop_event.is_set():
                self._stop_event.wait(timeout=0.5)
        except KeyboardInterrupt:
            pass
    
    def _measurement_loop(self):
        """Periodically read sensors and queue readings."""
        while not self._stop_event.wait(timeout=self.measure_interval):
            readings = self._take_readings()
            for reading in readings:
                self._reading_queue.put(reading)
                self._readings_count += 1
            
            if readings:
                temp_str = f"{readings[0].get('temperature', 'N/A')}"
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Queued {len(readings)} readings (Queue: {self._reading_queue.qsize()})")
    
    def _batch_send_loop(self):
        """Periodically send batched readings via MQTT."""
        while not self._stop_event.wait(timeout=self.batch_interval):
            self._send_batch()
    
    def _take_readings(self) -> list[dict]:
        """Take readings from all sensors. Returns list of reading dicts."""
        readings = []
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # DS18B20 temperature
        ds_temp = self._ds18b20.read_temperature()
        if ds_temp is not None:
            readings.append({
                "sensor_id": f"{self.station_id}_ds18b20",
                "sensor_type": "ds18b20",
                "temperature": ds_temp,
                "timestamp": timestamp
            })
        
        # Humidity sensor (BME280 or DHT11 - both report as "bme280" for DB compatibility)
        if self._humidity_sensor:
            humid_temp, humidity = self._humidity_sensor.read()
            
            if humid_temp is not None or humidity is not None:
                readings.append({
                    "sensor_id": f"{self.station_id}_bme280",
                    "sensor_type": "bme280",  # DHT11 "spoofs" as BME280 - same data format
                    "temperature": humid_temp,
                    "humidity": humidity,
                    "timestamp": timestamp
                })
        
        return readings
    
    def _send_batch(self):
        """Send all queued readings as a batch."""
        readings = []
        
        while not self._reading_queue.empty():
            try:
                readings.append(self._reading_queue.get_nowait())
            except Exception:
                break
        
        if not readings:
            return
        
        # Send batch via MQTT
        batch_message = {
            "station_id": self.station_id,
            "readings": readings
        }
        
        if self.sender.send_message(batch_message):
            self._batches_sent += 1
            print(f"[BATCH] Sent {len(readings)} readings to central hub")
        else:
            # Re-queue readings on failure
            for r in readings:
                self._reading_queue.put(r)
            print(f"[ERR] Failed to send batch, re-queued {len(readings)} readings")


def main():
    parser = argparse.ArgumentParser(
        description="Measurement Station Sender - reads sensors and sends via MQTT",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        "-b", "--broker",
        type=str,
        default="192.168.0.252",
        help="Central hub (MQTT broker) address"
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
        "-B", "--batch-interval",
        type=float,
        default=60.0,
        help="Interval between batch sends in seconds"
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
    parser.add_argument(
        "--bme280-address",
        type=lambda x: int(x, 0),
        default=0x76,
        help="I2C address for BME280 (0x76 or 0x77, default: 0x76)"
    )
    
    args = parser.parse_args()
    
    sender = MeasurementSender(
        broker_address=args.broker,
        station_id=args.station_id,
        measure_interval=args.measure_interval,
        batch_interval=args.batch_interval,
        use_bme280=not args.dht11,
        dht_pin=args.dht_pin,
        bme280_address=args.bme280_address
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
