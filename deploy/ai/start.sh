#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -d "$SCRIPT_DIR/ai_module" ]]; then
  ROOT_DIR="$SCRIPT_DIR"
else
  ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
fi
cd "$ROOT_DIR"

# The application reads .env with pydantic. Do not `source` it: JSON list values
# such as CORS_ORIGINS must reach pydantic unchanged.
exec python -m ai_module.main
