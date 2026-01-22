#!/usr/bin/env python3
"""
Environmental Monitoring Script

Reads temperature from DS18B20 and optionally temperature+humidity from BME280/DHT11.
Uses threading events for timing control and batch inserts readings to database.
"""

import argparse
import signal

from .config import Config
from .measurement_system import MeasurementSystem


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Environmental Monitoring System",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        "-m", "--measure-interval",
        type=float,
        default=5.0,
        help="Interval between measurements in seconds"
    )
    parser.add_argument(
        "-b", "--batch-interval",
        type=float,
        default=60.0,
        help="Interval between database batch inserts in seconds"
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
        "-s", "--station-id",
        type=str,
        default="station_1",
        help="Station identifier"
    )
    
    parser.add_argument(
        "-d", "--database",
        type=str,
        default="weather_data.db",
        help="SQLite database file path"
    )
    
    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()
    
    config = Config(
        measure_interval=args.measure_interval,
        batch_interval=args.batch_interval,
        use_bme280=not args.dht11,
        dht_pin=args.dht_pin,
        station_id=args.station_id,
        db_file=args.database
    )
    
    # Create and run measurement system
    system = MeasurementSystem(config)
    
    # Setup signal handlers for graceful shutdown
    def signal_handler(sig, frame):
        system.stop()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    if system.start():
        system.wait()
        system.stop()


if __name__ == "__main__":
    main()
