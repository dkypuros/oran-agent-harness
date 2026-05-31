#!/usr/bin/env bash
# Stop the Linux lab containers (podman compose).
set -euo pipefail

LINUX_LAB_DIR="$(cd "$(dirname "$0")" && pwd)"
COMPOSE_DIR="$(cd "$LINUX_LAB_DIR/../macbook_lab" && pwd)"

if podman compose version > /dev/null 2>&1; then
  COMPOSE_CMD=(podman compose)
elif command -v podman-compose > /dev/null; then
  COMPOSE_CMD=(podman-compose)
else
  echo "Neither 'podman compose' nor 'podman-compose' is available."
  exit 1
fi

cd "$COMPOSE_DIR"
"${COMPOSE_CMD[@]}" --profile dashboard down 2>/dev/null || "${COMPOSE_CMD[@]}" down
echo "Lab stopped."
