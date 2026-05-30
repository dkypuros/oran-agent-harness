#!/usr/bin/env bash
# Stop the MacBook lab containers.
set -euo pipefail
cd "$(dirname "$0")"
docker compose --profile dashboard down 2>/dev/null || docker compose down
echo "Lab stopped."
