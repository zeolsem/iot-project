#!/bin/bash

echo "[2/2] Starting Mosquitto Service..."
sudo systemctl start mosquitto.service

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_NAME="broker"

echo "[1/2] Running ${SCRIPT_NAME}.py with arguments: $@"
sudo "${SCRIPT_DIR}/.venv/bin/python" "${SCRIPT_DIR}/${SCRIPT_NAME}.py" "$@"

echo "[2/2] Closing..."
