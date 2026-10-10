#!/bin/bash
set -euo pipefail
source "$(dirname "$0")/env.sh"
exec "$SRE_ROOT/ghidra-mcp/.venv/bin/python" "$SRE_ROOT/scripts/ghidra-server.py" "$@"

