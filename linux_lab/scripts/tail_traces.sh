#!/usr/bin/env bash
# Tail the shared_trace JSONL files inside the harness-walker container via podman exec.
# Equivalent to macbook_lab/scripts/tail_traces.sh.
set -euo pipefail

if ! podman ps --filter name=oran-harness-walker --format "{{.Names}}" | grep -q oran-harness-walker; then
  echo "harness-walker container is not running. Start the lab first:"
  echo "  cd $(dirname "$0")/.. && ./run.sh"
  exit 1
fi

echo "Tailing /app/5G_O-RAN_SIM/shared_trace/*.jsonl inside oran-harness-walker..."
echo "Ctrl-C to stop."
podman exec -it oran-harness-walker sh -c 'tail -n 0 -f /app/5G_O-RAN_SIM/shared_trace/*.jsonl'
