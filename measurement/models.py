from dataclasses import dataclass


@dataclass
class SensorReading:
    """Represents a single sensor reading."""
    station_id: str
    temperature: float | None
    humidity: float | None
    timestamp: str
