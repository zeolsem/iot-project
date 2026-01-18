#!/bin/bash

# 1. Determine the script's directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 2. Execute Python using the venv inside that directory
echo "[EXEC] Running sender.py with arguments: $@"
sudo "${SCRIPT_DIR}/.venv/bin/python" "${SCRIPT_DIR}/sender.py" "$@"
