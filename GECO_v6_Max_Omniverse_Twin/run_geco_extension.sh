#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ISAAC_SIM="/home/axion/twin/omniverse/runtime/isaac-sim-6.1.0/isaac-sim.sh"
EXT_FOLDER="/home/axion/twin/omniverse/src/extensions"

echo "[GECO v6.1+ Max] Launching NVIDIA Isaac Sim 6.1.0 with geco.v6.omniverse.ward..."
exec "$ISAAC_SIM" \
    --ext-folder "$EXT_FOLDER" \
    --/persistent/isaac/asset_root/default="/home/axion/twin/omniverse/assets" \
    --enable omni.kit.debug.vscode \
    --enable geco.v6.omniverse.ward \
    "$@"
