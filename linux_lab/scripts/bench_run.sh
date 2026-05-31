#!/usr/bin/env bash
# Run the full bench (all 5 scenarios) against the running Linux lab via podman exec.
# Equivalent to macbook_lab/scripts/bench_run.sh but podman-flavored.
set -euo pipefail

if ! podman ps --filter name=oran-harness-walker --format "{{.Names}}" | grep -q oran-harness-walker; then
  echo "harness-walker container is not running. Start the lab first:"
  echo "  cd $(dirname "$0")/.. && ./run.sh"
  exit 1
fi

echo "Running full bench against http://localhost:8096/bench/all ..."
curl -sS http://localhost:8096/bench/all | jq '.summary'
