#!/usr/bin/env bash
# Walk both walkthrough scenarios end-to-end and print each pipeline stage.
# Exit non-zero if any walker run fails.
# See scenarios/README.md for the walkthrough narrative.

set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

for scenario in scenarios/A_fw_lldp_agent scenarios/A_prime_ice_driver; do
  printf '\n==================================================================\n'
  printf '  %s\n' "$scenario"
  printf '==================================================================\n'
  python3 -m harness.runtime.walker "$scenario/fault_payload.json" --verbose
done
