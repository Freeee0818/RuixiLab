#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="${COMPOSE_FILE:-${SCRIPT_DIR}/compose.yaml}"
COMPOSE_ENV="${COMPOSE_ENV:-${SCRIPT_DIR}/.env}"
PUBLIC_ORIGIN="${PUBLIC_ORIGIN:-https://ruixi.tech}"

compose() {
  docker compose --env-file "$COMPOSE_ENV" -f "$COMPOSE_FILE" "$@"
}

echo "[1/4] Container state"
compose ps

echo "[2/4] Private health endpoints"
curl --fail --silent --show-error http://127.0.0.1:8000/health
echo
curl --fail --silent --show-error http://127.0.0.1:8001/health
echo
curl --fail --silent --show-error http://127.0.0.1:8002/health
echo

echo "[3/4] Public Nginx routes"
curl --fail --silent --show-error "${PUBLIC_ORIGIN}/api/health"
echo
curl --fail --silent --show-error "${PUBLIC_ORIGIN}/ai/health"
echo
curl --fail --silent --show-error "${PUBLIC_ORIGIN}/auth/session"
echo

echo "[4/4] Public backend ports must not be reachable through the firewall"
echo "Run from another machine: nc -vz <server-ip> 8000; nc -vz <server-ip> 8001; nc -vz <server-ip> 8002"
echo "GuideLab Docker smoke checks passed."
