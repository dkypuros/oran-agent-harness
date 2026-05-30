#!/usr/bin/env bash
# Tail the JSONL trace files inside the harness-walker container.
set -euo pipefail
docker compose exec harness-walker sh -c \
    "tail -F /app/5G_O-RAN_SIM/shared_trace/*.jsonl 2>/dev/null || echo 'no trace files yet; run the bench first'"
