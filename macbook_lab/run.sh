#!/usr/bin/env bash
# MacBook lab one-command launcher.
# Brings up the platform stubs, the harness walker, the trace viewer, the fake vLLM,
# and (if Issue #57 has landed) the React dashboard.
#
# Prereqs: macOS with Docker Desktop running. Nothing else.

set -euo pipefail
cd "$(dirname "$0")"

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created macbook_lab/.env from .env.example."
  echo ""
  echo "If you have an Anthropic or OpenAI API key you want to use, edit it now."
  echo "Otherwise the local fake vLLM mock serves canned responses (no internet needed)."
  echo ""
  echo "Re-run ./run.sh when ready."
  exit 0
fi

INCLUDE_DASHBOARD=0
if [ -d "dashboard" ] && [ -f "dashboard/package.json" ]; then
  INCLUDE_DASHBOARD=1
fi

echo "Building and starting MacBook lab containers..."
if [ "$INCLUDE_DASHBOARD" -eq 1 ]; then
  docker compose --profile dashboard up --build -d
else
  docker compose up --build -d
  echo ""
  echo "(Dashboard not built yet, run without --profile dashboard until Issue #57 lands.)"
fi

echo ""
echo "Lab is running. Open these in a browser:"
echo "  Trace viewer       http://localhost:8095/dashboard/trace_view/index.html"
echo "  Harness walker     http://localhost:8096/health"
echo "  PTP operator stub  http://localhost:8091/health"
echo "  Metal3 BMO stub    http://localhost:8092/health"
echo "  Redfish BMC stub   http://localhost:8093/health"
echo "  TMF921 SMO stub    http://localhost:8094/health"
echo "  Fake vLLM          http://localhost:8090/"
if [ "$INCLUDE_DASHBOARD" -eq 1 ]; then
  echo "  Dashboard          http://localhost:8097"
fi
echo ""
echo "Useful one-liners:"
echo "  Run the bench         curl http://localhost:8096/bench/all | jq"
echo "  Walk one scenario     curl http://localhost:8096/run/E_nic_firmware_update | jq"
echo "  Stop everything       ./stop.sh"
