#!/bin/bash
set -euo pipefail
source "$(dirname "$0")/env.sh"
exec /Users/donnybystrom/.nvm/versions/node/v22.21.1/bin/node "$SRE_ROOT/rea/scripts/rea.mjs" "$@"

