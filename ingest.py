import os
import time
import threading

from MQTTwrapper import MQTTReceiver
from WeatherDatabase import WeatherDatabase


def main():
    db_path = os.getenv("WEATHER_DB_PATH", "/home/pi/weather_data.db")
    topic = os.getenv("MQTT_TOPIC", "weather/readings")
    client_id = os.getenv("MQTT_CLIENT_ID", "central-hub")
    flush_every_s = float(os.getenv("INGEST_FLUSH_INTERVAL", "1.0"))
    flush_batch = int(os.getenv("INGEST_FLUSH_BATCH", "50"))

    db = WeatherDatabase(db_file=db_path)
    rx = MQTTReceiver(topic=topic, client_id=client_id)

    buffer = []
    buf_lock = threading.Lock()
    last_flush = time.time()

    def handle(msg):
        # Expecting keys: station_id, temperature, humidity
        row = {
            "station_id": msg.get("station_id"),
            "sensor_id": msg.get("sensor_id", msg.get("station_id")),
            "temperature": msg.get("temperature"),
            "humidity": msg.get("humidity"),
            "timestamp": msg.get("timestamp"),
        }
        with buf_lock:
            buffer.append(row)

    print(f"[ingest] subscribing to topic='{topic}' as client_id='{client_id}'")
    if not rx.connect(handle):
        print("[ingest] failed to connect to MQTT broker")
        return

    try:
        while True:
            time.sleep(0.2)
            now = time.time()
            flush_now = False
            with buf_lock:
                if len(buffer) >= flush_batch:
                    flush_now = True
                elif now - last_flush >= flush_every_s and buffer:
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
                    sensor = r.get("sensor_id")
                    if r.get("temperature") is not None:
                        temps.append({"station_id": sid, "sensor_id": sensor, "value": r.get("temperature"), "timestamp": ts})
                    if r.get("humidity") is not None:
                        hums.append({"station_id": sid, "sensor_id": sensor, "value": r.get("humidity"), "timestamp": ts})

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