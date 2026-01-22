#!/bin/bash
# Deploy and run the measurement station sender (192.168.0.253)
# This script should be run ON the measuring station Pi

set -e

BROKER_IP="${BROKER_IP:-192.168.0.252}"
STATION_ID="${STATION_ID:-station_1}"
MEASURE_INTERVAL="${MEASURE_INTERVAL:-5}"

echo "=== Measurement Station Deployment ==="

# Navigate to project directory
cd "$(dirname "$0")"

# Sync dependencies
echo "[1/3] Syncing Python dependencies..."
uv sync

# Install sensor packages (Raspberry Pi specific)
echo "[2/3] Installing sensor packages..."
uv add RPi.GPIO w1thermsensor adafruit-circuitpython-bme280 adafruit-blinka 2>/dev/null || true

# Enable 1-Wire if not already enabled (for DS18B20)
if ! grep -q "dtoverlay=w1-gpio" /boot/config.txt 2>/dev/null; then
    echo "  [WARN] 1-Wire not enabled. Add 'dtoverlay=w1-gpio' to /boot/config.txt and reboot."
fi

# Enable I2C if not already enabled (for BME280)
if ! grep -q "dtparam=i2c_arm=on" /boot/config.txt 2>/dev/null; then
    echo "  [WARN] I2C not enabled. Add 'dtparam=i2c_arm=on' to /boot/config.txt and reboot."
fi

# Run the station sender
echo "[3/3] Starting Measurement Station..."
echo "  Broker: $BROKER_IP"
echo "  Station ID: $STATION_ID"
echo "  Measure interval: ${MEASURE_INTERVAL}s"
echo ""
uv run python station_sender.py \
    --broker "$BROKER_IP" \
    --station-id "$STATION_ID" \
    --measure-interval "$MEASURE_INTERVAL"
