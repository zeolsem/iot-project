#!/usr/bin/env python3
import os
import time
import argparse
import sys
from dotenv import load_dotenv
import paho.mqtt.client as mqtt

CERT_PATH = "/etc/mosquitto/ca_certificates"
CA_CERT = os.path.join(CERT_PATH, "ca.crt")

TOPIC = "test/topic"
PAYLOAD = "hello from Raspberry Pi"

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print("[OK] Connected")
    else:
        print(f"[ERR] Connect failed rc={rc}")

def on_publish(client, userdata, mid, reason_code=None, properties=None):
    print(f"[OK] Published: mid={mid} topic={TOPIC}")

def main():
    load_dotenv()
    
    broker = os.getenv("BROKER_IP") or "192.168.0.252"
    user = os.getenv("MQTT_USER")
    pw = os.getenv("MQTT_PASS")

    parser = argparse.ArgumentParser(description="MQTT Sender")
    parser.add_argument("--auth", action="store_true", help="Enable username/password auth")
    parser.add_argument("--tls", action="store_true", help="Enable TLS (port 8883)")
    args = parser.parse_args()

    port = 8883 if args.tls else 1883

    print("[INFO] MQTT Sender")
    print(f" -> broker: {broker}:{port}")
    print(f" -> tls: {'enabled' if args.tls else 'disabled'}")

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_publish = on_publish

    if args.auth:
        if not user or not pw:
            print("[ERR] Auth requested but MQTT_USER/PASS missing.")
            return
        client.username_pw_set(user, pw)

    if args.tls:
        import ssl
        if not os.path.exists(CA_CERT):
            print(f"[ERR] TLS requested but '{CA_CERT}' not found.")
            sys.exit(1)

        print(f"[INFO] TLS Enabled. Loading CA: {CA_CERT}")
        
        client.tls_set(
            ca_certs=CA_CERT,
            tls_version=ssl.PROTOCOL_TLSv1_2,
        )

    print("[INFO] Connecting...")
    try:
        client.connect(broker, port, keepalive=60)
        client.loop_start()
        time.sleep(0.2)

        print(f"[INFO] Publishing to {TOPIC}...")
        client.publish(TOPIC, PAYLOAD)

        time.sleep(0.5)
        client.disconnect()
        client.loop_stop()
        print("[DONE] Exit")
        
    except Exception as e:
        print(f"[ERR] Connection Error: {e}")
        if "Permission denied" in str(e):
            print("[HINT] Run with 'sudo' to read /etc/ certificates.")

if __name__ == "__main__":
    main()
