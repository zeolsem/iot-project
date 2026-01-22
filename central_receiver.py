#!/usr/bin/env python3
"""
Central Hub Receiver

Receives weather data via MQTT from measuring stations and stores it in the database.
Runs on the central Raspberry Pi (broker).
"""

import argparse
import signal
import sys
import threading
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))
from MQTTwrapper import MQTTReceiver
from WeatherDatabase import WeatherDatabase


TOPIC = "weather/readings"


class CentralReceiver:
    """Receives weather data via MQTT and stores in database."""
    
    def __init__(self, broker_address: str, db_file: str):
        self.broker_address = broker_address
        self.db = WeatherDatabase(db_file)
        
        self.receiver = MQTTReceiver(
            broker_address=broker_address,
            topic=TOPIC,
            client_id="central_receiver"
        )
        
        self._stop_event = threading.Event()
        self._message_count = 0
    
    def _on_message(self, data: dict):
        """Handle incoming weather data."""
        try:
            station_id = data.get("station_id", "unknown")
            temperature = data.get("temperature")
            humidity = data.get("humidity")
            timestamp = data.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            
            # Store in database
            self.db.insert_reading(station_id, temperature, humidity, timestamp)
            self._message_count += 1
            
            # Log
            temp_str = f"{temperature:.2f}°C" if temperature else "N/A"
            hum_str = f"{humidity:.1f}%" if humidity else "N/A"
            print(f"[{timestamp}] {station_id}: Temp={temp_str}, Humidity={hum_str}")
            
        except Exception as e:
            print(f"[ERR] Message processing error: {e}")
    
    def start(self) -> bool:
        """Start the receiver."""
        print("=" * 50)
        print("CENTRAL HUB RECEIVER")
        print("=" * 50)
        print(f"Broker: {self.broker_address}")
        print(f"Topic: {TOPIC}")
        print(f"Database: {self.db.db_file}")
        print("=" * 50)
        
        if not self.receiver.connect(self._on_message):
            print("[ERR] Failed to connect to broker")
            return False
        
        print("\n[INFO] Receiver started. Press Ctrl+C to stop.\n")
        return True
    
    def stop(self):
        """Stop the receiver gracefully."""
        print("\n[INFO] Stopping receiver...")
        self._stop_event.set()
        self.receiver.disconnect()
        print(f"[STATS] Total messages received: {self._message_count}")
        print("[DONE] Receiver stopped.")
    
    def wait(self):
        """Block until stop event is set."""
        try:
            while not self._stop_event.is_set():
                self._stop_event.wait(timeout=0.5)
        except KeyboardInterrupt:
            pass


def main():
    parser = argparse.ArgumentParser(
        description="Central Hub Receiver - receives weather data via MQTT",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        "-b", "--broker",
        type=str,
        default="127.0.0.1",
        help="MQTT broker address"
    )
    parser.add_argument(
        "-d", "--database",
        type=str,
        default="weather_data.db",
        help="SQLite database file path"
    )
    
    args = parser.parse_args()
    
    receiver = CentralReceiver(
        broker_address=args.broker,
        db_file=args.database
    )
    
    def signal_handler(sig, frame):
        receiver.stop()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    if receiver.start():
        receiver.wait()
        receiver.stop()


if __name__ == "__main__":
    main()
