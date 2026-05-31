#!/usr/bin/env python3
"""Micro harness test for the LIVE LLM path (Anthropic Claude via 5G_O-RAN_SIM/llm/inference_client.py).

Proves the harness can actually reach the configured LLM provider with the real API key.
Distinct from scripts/test_oran_discover_skills.py, which tests the read-only discovery surface.

What this test asks:
  1. Is LLM_PROVIDER configured (not the default stub)?
  2. Is the API key set and not the stub sentinel?
  3. Does inference_client.completion() return a real model response, NOT the canned fallback?
  4. (Optional) Does the Router-level ambiguous_path gate fire when ORAN_LLM_MODE=live?

Usage:
    # On the host with the right env loaded:
    python scripts/test_llm_live_path.py

    # Or inside the running lab container (recommended; matches the lab's actual config):
    docker exec oran-harness-walker python scripts/test_llm_live_path.py

Exit code 0 on PASS, 1 on FAIL.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SIM_ROOT = REPO_ROOT / "5G_O-RAN_SIM"
if str(SIM_ROOT) not in sys.path:
    sys.path.insert(0, str(SIM_ROOT))

# Match the lab's inference_client behavior: detect canned fallback by sentinel prefix.
CANNED_PREFIX = "stub disambiguation:"


def section(title: str) -> None:
    print(f"\n--- {title} ---")


def check_env() -> tuple[bool, dict]:
    section("Environment")
    provider = os.environ.get("LLM_PROVIDER", "").strip().lower()
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    mode = os.environ.get("ORAN_LLM_MODE", "").strip().lower()

    print(f"  LLM_PROVIDER     = {provider or '<unset>'}")
    print(f"  ANTHROPIC_API_KEY= {'<set, length ' + str(len(key)) + '>' if key and key != 'stub-replace-with-real-key' else '<stub or unset>'}")
    print(f"  ORAN_LLM_MODE    = {mode or '<unset>'} (note: gates Router, not inference_client)")

    ok = True
    if provider != "anthropic":
        print(f"  FAIL: LLM_PROVIDER is {provider!r}; this test exercises anthropic specifically")
        ok = False
    if not key or key == "stub-replace-with-real-key":
        print("  FAIL: ANTHROPIC_API_KEY missing or is the stub sentinel")
        ok = False
    return ok, {"provider": provider, "key_set": bool(key and key != 'stub-replace-with-real-key'), "mode": mode}


def check_live_completion() -> tuple[bool, dict]:
    section("Live inference call")
    try:
        from llm import inference_client  # type: ignore
    except ImportError as e:
        print(f"  FAIL: could not import 5G_O-RAN_SIM/llm/inference_client.py ({e})")
        return False, {}

    prompt = (
        "Classify the following Cloud RAN day-2 fault under one of: host_driver, "
        "cell_param, node_firmware, phc_hw_drift, ptp_host_stack. "
        "Fault: linuxptp reports SYNCHRONIZED while NIC tx_hwtstamp_timeouts climb. "
        "Answer with just the taxonomy id."
    )
    print(f"  prompt length    = {len(prompt)} chars")
    print(f"  prompt preview   = {prompt[:80]}...")

    start = time.monotonic()
    try:
        response = inference_client.completion(prompt, tier="low")
    except Exception as e:
        print(f"  FAIL: completion() raised: {type(e).__name__}: {e}")
        return False, {}
    elapsed = time.monotonic() - start

    print(f"  latency          = {elapsed:.2f}s")
    print(f"  response length  = {len(response)} chars")
    print(f"  response preview = {response[:160]}{'...' if len(response) > 160 else ''}")

    fell_back = response.startswith(CANNED_PREFIX) or CANNED_PREFIX in response
    if fell_back:
        print("  FAIL: response starts with the canned-fallback sentinel; the call did NOT reach Anthropic")
        return False, {"latency_s": elapsed, "fallback": True, "response": response}

    print("  PASS: response is non-canned; the call reached the live LLM provider")
    return True, {"latency_s": elapsed, "fallback": False, "response": response}


def main() -> int:
    print("=" * 72)
    print("LLM live-path micro harness test")
    print("=" * 72)

    env_ok, env_info = check_env()
    live_ok, live_info = check_live_completion()

    print("\n" + "=" * 72)
    if env_ok and live_ok:
        print(f"SUMMARY: PASS (provider={env_info['provider']}, latency={live_info.get('latency_s', 0):.2f}s)")
        print("OVERALL: PASS")
        print("=" * 72)
        return 0

    print("SUMMARY: FAIL")
    if not env_ok:
        print("  env config: provider/key not aligned with anthropic")
    if not live_ok:
        if live_info.get("fallback"):
            print("  live call: fell back to canned response (provider unreachable or key invalid)")
        else:
            print("  live call: exception or import failure")
    print("OVERALL: FAIL")
    print("=" * 72)
    return 1


if __name__ == "__main__":
    sys.exit(main())
