#!/usr/bin/env python3
import os
import time
import signal
import argparse
import sys
from dotenv import load_dotenv
import paho.mqtt.client as mqtt

CERT_PATH = "/etc/mosquitto/ca_certificates"
CA_CERT = os.path.join(CERT_PATH, "ca.crt")

TOPIC = "test/topic"
running = True

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print("[OK] Connected to broker, subscribing...")
        client.subscribe(TOPIC)
    else:
        print(f"[ERR] Connect failed rc={rc}")

def on_message(client, userdata, msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[MSG {ts}] topic='{msg.topic}' payload='{msg.payload.decode(errors='replace')}'")

def handle_sigint(sig, frame):
    global running
    print("\n[INFO] Shutting down...")
    running = False

def main():
    load_dotenv()
    
    broker = os.getenv("BROKER_IP") or "127.0.0.1"
    user = os.getenv("MQTT_USER")
    pw = os.getenv("MQTT_PASS")

    parser = argparse.ArgumentParser(description="MQTT Receiver")
    parser.add_argument("--auth", action="store_true", help="Enable username/password auth")
    parser.add_argument("--tls", action="store_true", help="Enable TLS (port 8883)")
    args = parser.parse_args()

    port = 8883 if args.tls else 1883

    print("[INFO] MQTT Receiver")
    print(f" -> broker: {broker}:{port}")
    print(f" -> tls: {'enabled' if args.tls else 'disabled'}")

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message

    if args.auth:
        if not user or not pw:
            print("[ERR] Auth requested but MQTT_USER/PASS missing.")
            return
        client.username_pw_set(user, pw)
        print(f"[INFO] Using auth user='{user}'")

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
        signal.signal(signal.SIGINT, handle_sigint)
        client.loop_start()

        while running:
            time.sleep(0.1)

        client.disconnect()
        client.loop_stop()
        print("[DONE] Exit")
        
    except Exception as e:
        print(f"[ERR] Connection Error: {e}")
        if "Permission denied" in str(e):
            print("[HINT] Run with 'sudo' to read /etc/ certificates.")

if __name__ == "__main__":
    main()
