#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -d "$SCRIPT_DIR/access_service" ]]; then
  ROOT_DIR="$SCRIPT_DIR"
else
  ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
fi
cd "$ROOT_DIR"

# Pydantic reads JSON-list values directly from .env; do not source the file.
exec python -m access_service.main
