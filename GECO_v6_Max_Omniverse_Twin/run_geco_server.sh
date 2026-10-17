#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="/home/axion/twin/omniverse/venvs/tools/bin/python"

if [ ! -x "$PYTHON" ]; then
    PYTHON="python3"
fi

export PYTHONPATH="${SCRIPT_DIR}:${SCRIPT_DIR}/../GECOv6/02_IMPLEMENTATION:${PYTHONPATH:-}"
echo "[GECO v6.1+ Max] Starting 12-Bay Ward Telemetry Server on ws://127.0.0.1:8766..."
exec "$PYTHON" -m geco_v6_max.ward_telemetry_server --host 127.0.0.1 --port 8766 "$@"
