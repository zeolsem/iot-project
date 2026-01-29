#!/usr/bin/env python3
import os
import time
import socket
from typing import Optional, Tuple

from dotenv import load_dotenv

from MQTTwrapper import MQTTSender

try:
    import board
    import adafruit_dht
except Exception:
    adafruit_dht = None

try:
    from w1thermsensor import W1ThermSensor
except Exception:
    W1ThermSensor = None

try:
    import adafruit_bme280.basic as adafruit_bme280
    import busio
except Exception:
    adafruit_bme280 = None


def init_dht() -> Optional[object]:
    if not adafruit_dht:
        print("[sender] DHT11 library not available")
        return None
    try:
        return adafruit_dht.DHT11(board.D16, use_pulseio=False)
    except Exception:
        print("[sender] DHT11 init failed")
        return None


def init_ds18() -> Optional[object]:
    if not W1ThermSensor:
        print("[sender] DS18B20 library not available (enable 1-Wire?)")
        return None
    try:
        return W1ThermSensor()
    except Exception:
        print("[sender] DS18B20 init failed (check 1-Wire config/wiring)")
        return None


def init_bme280() -> Optional[object]:
    if not adafruit_bme280:
        print("[sender] BME280 library not available")
        return None
    try:
        i2c = busio.I2C(board.SCL, board.SDA)
        return adafruit_bme280.Adafruit_BME280_I2C(i2c, address=0x76)
    except Exception as e:
        print(f"[sender] BME280 init failed: {e}")
        return None


def read_dht(dht) -> Tuple[Optional[float], Optional[float]]:
    if not dht:
        return None, None
    try:
        return dht.temperature, dht.humidity
    except Exception as e:
        print(f"[sender] DHT11 read error: {e}")
        return None, None


def read_ds18(ds) -> Optional[float]:
    if not ds:
        return None
    try:
        return ds.get_temperature()
    except Exception as e:
        print(f"[sender] DS18B20 read error: {e}")
        return None


def read_bme280(bme) -> Tuple[Optional[float], Optional[float]]:
    if not bme:
        return None, None
    try:
        return bme.temperature, bme.relative_humidity
    except Exception as e:
        print(f"[sender] BME280 read error: {e}")
        return None, None


def choose_temperature(ds_temp, aux_temp):
    return ds_temp if ds_temp is not None else aux_temp


def main():
    load_dotenv()

    station_id = os.getenv("STATION_ID", socket.gethostname())
    sensor_combo = os.getenv("SENSOR_COMBO", "dht11_ds18").lower()
    topic = "weather/readings"

    use_bme = sensor_combo == "bme280_ds18"

    # Sensor IDs for labeling per-sensor series
    default_temp_id = "ds18b20"
    default_aux_temp_id = "bme280" if use_bme else "dht11"
    default_hum_id = "bme280" if use_bme else "dht11"

    temp_sensor_id_ds = os.getenv("TEMP_SENSOR_ID", f"{station_id}-{default_temp_id}")
    temp_sensor_id_aux = os.getenv("AUX_TEMP_SENSOR_ID", f"{station_id}-{default_aux_temp_id}")
    hum_sensor_id = os.getenv("HUM_SENSOR_ID", f"{station_id}-{default_hum_id}")

    dht = init_dht() if not use_bme else None
    bme = init_bme280() if use_bme else None
    ds = init_ds18()

    if not ds and (use_bme and not bme) and (not use_bme and not dht):
        print("[sender] No sensors detected, exiting")
        return

    tx = MQTTSender(topic=topic, client_id=station_id)
    if not tx.connect():
        print("[sender] MQTT connect failed")
        return

    print(f"[sender] station_id={station_id} combo={sensor_combo} topic={topic}")

    try:
        while True:
            ds_temp = read_ds18(ds)
            if use_bme:
                aux_temp, hum = read_bme280(bme)
            else:
                aux_temp, hum = read_dht(dht)

            measurements = []
            if ds_temp is not None:
                measurements.append({
                    "type": "temperature",
                    "sensor_id": temp_sensor_id_ds,
                    "value": ds_temp,
                })
            if aux_temp is not None:
                measurements.append({
                    "type": "temperature",
                    "sensor_id": temp_sensor_id_aux,
                    "value": aux_temp,
                })
            if hum is not None:
                measurements.append({
                    "type": "humidity",
                    "sensor_id": hum_sensor_id,
                    "value": hum,
                })

            if measurements:
                payload = {
                    "station_id": station_id,
                    "measurements": measurements,
                }
                tx.send_message(payload)
            else:
                print("[sender] skip send, missing data (no measurements)")

            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[sender] stopping...")
    finally:
        tx.disconnect()


if __name__ == "__main__":
    main()
