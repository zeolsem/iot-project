from dataclasses import dataclass
from enum import Enum


@dataclass
class Config:
    """Configuration for the measurement system."""
    # Timing configuration
    measure_interval: float = 5.0       # seconds between measurements
    batch_interval: float = 60.0        # seconds between database batch inserts
    
    # Sensor configuration
    use_bme280: bool = True             # True for BME280 (default), False for DHT11
    dht_pin: int = 16                   # GPIO pin for DHT11 (GPIO 16 = Pin 36)
    
    # Station identification
    station_id: str = "station_1"
    
    # Database configuration
    db_file: str = "weather_data.db"


class SensorType(Enum):
    """Supported humidity sensor types."""
    DHT11 = "dht11"
    BME280 = "bme280"
