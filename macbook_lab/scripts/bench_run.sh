#!/usr/bin/env bash
# Run the research bench inside the harness-walker container.
# Produces shared_trace/*.jsonl in the container; mounted volume reflects to host.
set -euo pipefail
docker compose exec harness-walker python /app/5G_O-RAN_SIM/bench/runner.py all
