"""Hardware abstraction layer for sensors."""


class DS18B20Sensor:
    """DS18B20 temperature sensor wrapper."""
    
    def __init__(self):
        self._device = None
        
    def init(self) -> bool:
        """Initialize the DS18B20 sensor."""
        try:
            from w1thermsensor import W1ThermSensor
            self._device = W1ThermSensor()
            print("[DS18B20] Sensor initialized successfully")
            return True
        except ImportError:
            print("[DS18B20 ERROR] w1thermsensor not installed")
            print("[DS18B20 HINT] Run: uv add w1thermsensor")
            return False
        except Exception as e:
            print(f"[DS18B20 WARN] Sensor not detected: {e}")
            print("[DS18B20 HINT] Ensure 1-Wire is enabled in /boot/config.txt")
            return False
    
    def read_temperature(self) -> float | None:
        """Read temperature from DS18B20."""
        if not self._device:
            return None
        try:
            return self._device.get_temperature()
        except Exception as e:
            print(f"[DS18B20 ERROR] Read failed: {e}")
            return None
    
    def cleanup(self) -> None:
        """Cleanup resources (no-op for DS18B20)."""
        pass


class DHT11Sensor:
    """DHT11 temperature and humidity sensor wrapper."""
    
    def __init__(self, pin_id):
        self._pin_id = pin_id
        self._device = None
        
    def init(self) -> bool:
        """Initialize the DHT11 sensor."""
        try:
            import board
            import adafruit_dht
            
            # Map GPIO number to board pin
            pin = getattr(board, f"D{self._pin_id}")
            # use_pulseio=False helps with timing issues on RPi 4/5
            self._device = adafruit_dht.DHT11(pin, use_pulseio=False)
            print(f"[DHT11] Sensor initialized on GPIO{self._pin_id}")
            return True
        except ImportError as e:
            print(f"[DHT11 ERROR] Missing package: {e}")
            print("[DHT11 HINT] Run: uv add adafruit-circuitpython-dht")
            return False
        except Exception as e:
            print(f"[DHT11 ERROR] Failed to initialize: {e}")
            return False
    
    def read(self) -> tuple[float | None, float | None]:
        """
        Read temperature and humidity from DHT11.
        Returns: (temperature, humidity) or (None, None) on error.
        """
        if not self._device:
            return None, None
        try:
            temperature = self._device.temperature
            humidity = self._device.humidity
            return temperature, humidity
        except RuntimeError:
            # DHT sensors often throw RuntimeError for checksum failures - normal behavior
            return None, None
        except Exception as e:
            print(f"[DHT11 CRITICAL] Read error: {e}")
            return None, None
    
    def cleanup(self) -> None:
        """Release sensor resources."""
        if self._device:
            self._device.exit()
            print("[DHT11] Resources released")


class BME280Sensor:
    """BME280 temperature and humidity sensor wrapper (I2C)."""
    
    def __init__(self):
        self._device = None
        self._i2c = None
        
    def init(self) -> bool:
        """Initialize the BME280 sensor via I2C."""
        try:
            import board
            import adafruit_bme280.advanced as adafruit_bme280
            
            self._i2c = board.I2C()
            self._device = adafruit_bme280.Adafruit_BME280_I2C(self._i2c)
            print("[BME280] Sensor initialized successfully")
            return True
        except ImportError as e:
            print(f"[BME280 ERROR] Missing package: {e}")
            print("[BME280 HINT] Run: uv add adafruit-circuitpython-bme280")
            return False
        except Exception as e:
            print(f"[BME280 ERROR] Failed to initialize: {e}")
            return False
    
    def read(self) -> tuple[float | None, float | None]:
        """
        Read temperature and humidity from BME280.
        Returns: (temperature, humidity) or (None, None) on error.
        """
        if not self._device:
            return None, None
        try:
            temperature = self._device.temperature
            humidity = self._device.relative_humidity
            return temperature, humidity
        except Exception as e:
            print(f"[BME280 ERROR] Read failed: {e}")
            return None, None
    
    def cleanup(self) -> None:
        """Release sensor resources."""
        # BME280 doesn't require explicit cleanup
        pass