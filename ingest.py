import os
import time
import threading

from MQTTwrapper import MQTTReceiver
from WeatherDatabase import WeatherDatabase


BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def main():
    db_path = os.getenv("WEATHER_DB_PATH", os.path.join(BASE_DIR, "weather_data.db"))
    topic = os.getenv("MQTT_TOPIC", "weather/readings")
    client_id = os.getenv("MQTT_CLIENT_ID", "central-hub")
    flush_every_s = float(os.getenv("INGEST_FLUSH_INTERVAL", "0"))
    flush_batch = int(os.getenv("INGEST_FLUSH_BATCH", "1"))

    db = WeatherDatabase(db_file=db_path)
    rx = MQTTReceiver(topic=topic, client_id=client_id)

    buffer = []
    buf_lock = threading.Lock()
    last_flush = time.time()

    def handle(msg):
        # Expecting keys: station_id, temperature, humidity
        ts = msg.get("timestamp")
        station_id = msg.get("station_id")
        if "measurements" in msg and isinstance(msg["measurements"], list):
            rows = []
            for m in msg["measurements"]:
                if not isinstance(m, dict):
                    continue
                mtype = m.get("type")
                if mtype not in ("temperature", "humidity"):
                    continue
                rows.append({
                    "station_id": station_id,
                    "measurement_type": mtype,
                    "value": m.get("value"),
                    "sensor_id": m.get("sensor_id") or station_id,
                    "timestamp": ts,
                })
            with buf_lock:
                buffer.extend(rows)
        else:
            row = {
                "station_id": station_id,
                "measurement_type": None,  # will be split below
                "temperature": msg.get("temperature"),
                "temperature_sensor_id": msg.get("temperature_sensor_id") or msg.get("sensor_id") or station_id,
                "humidity": msg.get("humidity"),
                "humidity_sensor_id": msg.get("humidity_sensor_id") or msg.get("sensor_id") or station_id,
                "timestamp": ts,
            }
            with buf_lock:
                buffer.append(row)

    print(f"[ingest] subscribing to topic='{topic}' as client_id='{client_id}'")
    if not rx.connect(handle):
        print("[ingest] failed to connect to MQTT broker")
        return

    try:
        while True:
            time.sleep(0.05)
            now = time.time()
            flush_now = False
            with buf_lock:
                if len(buffer) >= flush_batch:
                    flush_now = True
                elif (flush_every_s <= 0 and buffer):
                    flush_now = True
                elif flush_every_s > 0 and now - last_flush >= flush_every_s and buffer:
                    flush_now = True
                if flush_now:
                    batch = buffer[:]
                    buffer.clear()
            if flush_now:
                temps = []
                hums = []
                for r in batch:
                    ts = r.get("timestamp")
                    sid = r.get("station_id")
                    mtype = r.get("measurement_type")
                    if mtype == "temperature":
                        temps.append({"station_id": sid, "sensor_id": r.get("sensor_id"), "value": r.get("value"), "timestamp": ts})
                    elif mtype == "humidity":
                        hums.append({"station_id": sid, "sensor_id": r.get("sensor_id"), "value": r.get("value"), "timestamp": ts})
                    else:
                        if r.get("temperature") is not None:
                            temps.append({"station_id": sid, "sensor_id": r.get("temperature_sensor_id"), "value": r.get("temperature"), "timestamp": ts})
                        if r.get("humidity") is not None:
                            hums.append({"station_id": sid, "sensor_id": r.get("humidity_sensor_id"), "value": r.get("humidity"), "timestamp": ts})

                count_t = db.insert_temps_bulk(temps)
                count_h = db.insert_hums_bulk(hums)
                last_flush = now
                total = count_t + count_h
                if total:
                    print(f"[ingest] flushed {total} readings (T={count_t}, H={count_h})")
    except KeyboardInterrupt:
        print("\n[ingest] stopping...")
    finally:
        rx.disconnect()


if __name__ == "__main__":
    main()