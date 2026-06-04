#!/usr/bin/env bash
# Linux lab one-command launcher for Fedora + podman.
# Brings up the same containers as macbook_lab/run.sh but via podman compose.
# Treat linux_lab/ as the Fedora runtime overlay; macbook_lab/ owns the Dockerfiles
# and the docker-compose.yml.

set -euo pipefail

LINUX_LAB_DIR="$(cd "$(dirname "$0")" && pwd)"
COMPOSE_DIR="$(cd "$LINUX_LAB_DIR/../macbook_lab" && pwd)"

if ! command -v podman > /dev/null; then
  echo "podman not found. Run ./setup_fedora.sh to install it."
  exit 1
fi

# Prefer 'podman compose' (built-in, newer) over 'podman-compose' (pip-installed).
if podman compose version > /dev/null 2>&1; then
  COMPOSE_CMD=(podman compose)
elif command -v podman-compose > /dev/null; then
  COMPOSE_CMD=(podman-compose)
else
  echo "Neither 'podman compose' nor 'podman-compose' is available. Run ./setup_fedora.sh."
  exit 1
fi

cd "$COMPOSE_DIR"

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created macbook_lab/.env from .env.example."
  echo ""
  echo "Set ANTHROPIC_API_KEY for the dashboard chat service."
  echo "For the Router LLM seam, choose LLM_PROVIDER=anthropic, openai, or vllm."
  echo "For on-prem vLLM, set VLLM_BASE_URL to your OpenShift AI route."
  echo ""
  echo "Re-run linux_lab/run.sh when ready."
  exit 0
fi

INCLUDE_DASHBOARD=0
if [ -d "dashboard" ] && [ -f "dashboard/package.json" ]; then
  INCLUDE_DASHBOARD=1
fi

echo "Building and starting Linux lab containers via ${COMPOSE_CMD[*]}..."
if [ "$INCLUDE_DASHBOARD" -eq 1 ]; then
  "${COMPOSE_CMD[@]}" --profile dashboard up --build -d
else
  "${COMPOSE_CMD[@]}" up --build -d
  echo ""
  echo "(Dashboard not built; re-run after the dashboard subdirectory is present.)"
fi

echo ""
echo "Lab is running. Open these in a browser:"
echo "  Trace viewer       http://localhost:8095/dashboard/trace_view/index.html"
echo "  Harness walker     http://localhost:8096/health"
echo "  PTP operator stub  http://localhost:8091/health"
echo "  Metal3 BMO stub    http://localhost:8092/health"
echo "  Redfish BMC stub   http://localhost:8093/health"
echo "  TMF921 SMO stub    http://localhost:8094/health"
if [ "$INCLUDE_DASHBOARD" -eq 1 ]; then
  echo "  Dashboard          http://localhost:8097"
  echo "  oh-my-tiny-oran    http://localhost:8097/#chat (requires ANTHROPIC_API_KEY in .env)"
fi
echo ""
echo "Useful one-liners:"
echo "  Run the bench         curl http://localhost:8096/bench/all | jq"
echo "  Walk one scenario     curl http://localhost:8096/run/E_nic_firmware_update | jq"
echo "  Stop everything       ./stop.sh"
echo ""
echo "If something looks off, see linux_lab/troubleshooting.md."
