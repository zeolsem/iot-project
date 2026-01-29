#!/usr/bin/env bash
set -euo pipefail

# Simple readiness checker for a fresh Raspberry Pi to run this project.
# It only reports status and hints; it does NOT modify system settings.

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PATH="$PROJECT_DIR/.venv"
CONFIG_TXT="/boot/config.txt"

ok()  { printf "[OK] %s\n" "$1"; }
warn(){ printf "[WARN] %s\n" "$1"; }
err() { printf "[ERR] %s\n" "$1"; }

check_cmd() {
  local name="$1"; shift
  if command -v "$name" >/dev/null 2>&1; then
    ok "$name is installed"
    return 0
  else
    err "$name not found; install it"
    return 1
  fi
}

echo "--- Project readiness check ---"
echo "Project dir: $PROJECT_DIR"

# 1) Network overlay
check_cmd tailscale || warn "Install tailscale and run 'sudo tailscale up' so edge/central can talk."
if command -v tailscale >/dev/null 2>&1; then
  if tailscale status >/dev/null 2>&1; then
    ok "tailscale status reachable"
  else
    warn "tailscale installed but not logged in ('sudo tailscale up')."
  fi
fi

# 2) MQTT broker
if systemctl is-active --quiet mosquitto; then
  ok "mosquitto service is running"
else
  warn "mosquitto not running; install/start with 'sudo apt-get install -y mosquitto' && 'sudo systemctl enable --now mosquitto'"
fi

# 3) Interfaces (1-Wire for DS18B20, I2C for BME280)
if [[ -f "$CONFIG_TXT" ]]; then
  if grep -Eq '^dtoverlay=w1-gpio' "$CONFIG_TXT"; then
    ok "1-Wire enabled (dtoverlay=w1-gpio)"
  else
    warn "1-Wire not enabled; add 'dtoverlay=w1-gpio' to $CONFIG_TXT and reboot."
  fi
  if grep -Eq '^dtparam=i2c_arm=on' "$CONFIG_TXT"; then
    ok "I2C enabled (dtparam=i2c_arm=on)"
  else
    warn "I2C not enabled; add 'dtparam=i2c_arm=on' to $CONFIG_TXT and reboot."
  fi
else
  warn "$CONFIG_TXT not found; cannot check 1-Wire/I2C."
fi

# 4) Tooling (uv for deps)
check_cmd uv || warn "Install uv (https://docs.astral.sh/uv) or pip will be slower."

# 5) Virtualenv / deps
if [[ -d "$VENV_PATH" ]]; then
  ok "venv exists at $VENV_PATH"
else
  warn "venv missing; create with 'python -m venv $VENV_PATH'"
fi

if [[ -d "$VENV_PATH" ]]; then
  if "$VENV_PATH/bin/python" -c "import MQTTwrapper" >/dev/null 2>&1; then
    ok "project dependencies appear installed in venv"
  else
    warn "deps not installed; run 'source $VENV_PATH/bin/activate && uv pip install . || pip install .'"
  fi
fi

# 6) Connectivity test to broker (optional)
BROKER_IP=${MQTT_BROKER_ADDRESS:-""}
if [[ -n "$BROKER_IP" ]]; then
  if command -v nc >/dev/null 2>&1; then
    if nc -z -w2 "$BROKER_IP" ${MQTT_BROKER_PORT:-1883}; then
      ok "Broker reachable at ${BROKER_IP}:${MQTT_BROKER_PORT:-1883}"
    else
      warn "Cannot reach broker at ${BROKER_IP}:${MQTT_BROKER_PORT:-1883}; check network/firewall."
    fi
  else
    warn "nc not installed; skip broker TCP check."
  fi
else
  warn "MQTT_BROKER_ADDRESS not set; skip broker reachability check."
fi

# 7) Summary
echo "--- Summary ---"
echo "Review any [WARN]/[ERR] lines above. No changes were made."