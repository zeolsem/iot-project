#!/bin/bash
# Deploy and run the central receiver on the broker Pi (192.168.0.252)
# This script should be run ON the broker Pi

set -e

echo "=== Central Hub Deployment ==="

# Navigate to project directory
cd "$(dirname "$0")"

# Sync dependencies
echo "[1/4] Syncing Python dependencies..."
uv sync

# Ensure mosquitto is running
echo "[2/4] Checking Mosquitto broker..."
if systemctl is-active --quiet mosquitto; then
    echo "  Mosquitto is running"
else
    echo "  Starting Mosquitto..."
    sudo systemctl start mosquitto
fi

# Configure Mosquitto for anonymous access if needed
echo "[3/4] Checking Mosquitto configuration..."
MOSQUITTO_CONF="/etc/mosquitto/mosquitto.conf"
if ! grep -q "allow_anonymous true" "$MOSQUITTO_CONF" 2>/dev/null; then
    echo "  Configuring Mosquitto for anonymous access..."
    echo -e "\nlistener 1883 0.0.0.0\nallow_anonymous true" | sudo tee -a "$MOSQUITTO_CONF" > /dev/null
    sudo systemctl restart mosquitto
    echo "  Mosquitto restarted with new config"
else
    echo "  Mosquitto already configured"
fi

# Run the central receiver
echo "[4/4] Starting Central Receiver..."
echo ""
uv run python central_receiver.py --broker 127.0.0.1 --database weather_data.db
