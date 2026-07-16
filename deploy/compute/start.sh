#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -d "$SCRIPT_DIR/analysis_module" ]]; then
  ROOT_DIR="$SCRIPT_DIR"
else
  ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
fi
cd "$ROOT_DIR"

JULIA_DIR="${GUIDELAB_JULIA_DIR:-$ROOT_DIR/pysr_module/julia-1.11.6}"
if [[ -x "$JULIA_DIR/bin/julia" ]]; then
  export PATH="$JULIA_DIR/bin:$PATH"
fi

# The application reads .env with pydantic. Do not `source` it: JSON list values
# such as CORS_ORIGINS must reach pydantic unchanged.
exec python -m analysis_module.main
