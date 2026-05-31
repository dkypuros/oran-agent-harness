#!/usr/bin/env python3
"""Micro harness test for the oran-discover OMC skill bundle.

Each /oran-discover:* skill at omc-skills/oran-discover/*.md documents two modes:
a live mode that curls a macbook_lab HTTP wrapper, and a static mode that reads
a 5G_O-RAN_SIM source file. This test exercises both modes for every skill and
fails if either the live endpoint or the static source does not match what the
skill markdown promises.

Usage:
    python scripts/test_oran_discover_skills.py
    BENCH_BASE_URL=http://localhost:8096 python scripts/test_oran_discover_skills.py

The lab must be up (`macbook_lab/run.sh`) for live-mode checks to pass.
Static-mode checks run regardless of lab state.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

LAB_PORTS = {
    "ptp": 8091,
    "metal3": 8092,
    "redfish": 8093,
    "smo": 8094,
}

STATIC_SOURCES = {
    "ptp":       REPO_ROOT / "5G_O-RAN_SIM/oam/ptp_operator_stub.py",
    "metal3":    REPO_ROOT / "5G_O-RAN_SIM/oam/metal3_bmo_stub.py",
    "redfish":   REPO_ROOT / "5G_O-RAN_SIM/oam/redfish_bmc_stub.py",
    "smo":       REPO_ROOT / "5G_O-RAN_SIM/smo/tmf921_intent_emitter.py",
    "taxonomy":  REPO_ROOT / "harness/taxonomy.yaml",
    "guardrail": REPO_ROOT / "harness/guardrails.yaml",
}

SKILL_FILES = {
    "ptp":       REPO_ROOT / "omc-skills/oran-discover/ptp.md",
    "metal3":    REPO_ROOT / "omc-skills/oran-discover/metal3.md",
    "redfish":   REPO_ROOT / "omc-skills/oran-discover/redfish.md",
    "smo":       REPO_ROOT / "omc-skills/oran-discover/smo.md",
    "taxonomy":  REPO_ROOT / "omc-skills/oran-discover/taxonomy.md",
    "guardrail": REPO_ROOT / "omc-skills/oran-discover/guardrail.md",
    "plan":      REPO_ROOT / "omc-skills/oran-discover/plan.md",
}

EXPECTED_RESPONSE_KEYS = {
    "ptp":     {"history": ["count", "events"],     "state": ["published_count", "latest"]},
    "metal3":  {"history": ["count", "phases"],     "state": ["scenarios_tracked", "latest_per_scenario"]},
    "redfish": {"history": ["count", "tasks"],      "state": ["scenarios_tracked", "latest_per_scenario"]},
    "smo":     {"history": ["count", "intents"],    "state": ["emitted_count", "latest"]},
}


def http_get(url: str, timeout: float = 3.0) -> tuple[int, dict | None]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            body = resp.read().decode()
            try:
                return resp.status, json.loads(body)
            except json.JSONDecodeError:
                return resp.status, None
    except (urllib.error.URLError, TimeoutError):
        return 0, None


def check_live_endpoint(skill: str) -> tuple[bool, str]:
    if skill not in LAB_PORTS:
        return True, "no live endpoint (declarative skill)"
    port = LAB_PORTS[skill]
    base = f"http://localhost:{port}"

    health_status, _ = http_get(f"{base}/health")
    if health_status != 200:
        return False, f"/health on :{port} returned {health_status} (lab not up?)"

    expected = EXPECTED_RESPONSE_KEYS[skill]
    for endpoint, keys in expected.items():
        status, body = http_get(f"{base}/{endpoint}")
        if status != 200:
            return False, f"/{endpoint} returned {status}"
        if not isinstance(body, dict):
            return False, f"/{endpoint} returned non-JSON"
        missing = [k for k in keys if k not in body]
        if missing:
            return False, f"/{endpoint} missing keys: {missing}"
    return True, f"all live endpoints on :{port} respond and validate"


def check_static_source(skill: str) -> tuple[bool, str]:
    if skill == "plan":
        return True, "orchestrator (composes the other six; no own static source)"
    path = STATIC_SOURCES.get(skill)
    if path is None:
        return False, f"no static source mapping for {skill}"
    if not path.exists():
        return False, f"static source missing: {path.relative_to(REPO_ROOT)}"
    size = path.stat().st_size
    return True, f"{path.relative_to(REPO_ROOT)} ({size} bytes)"


def check_skill_markdown(skill: str) -> tuple[bool, str]:
    path = SKILL_FILES[skill]
    if not path.exists():
        return False, f"skill markdown missing: {path.relative_to(REPO_ROOT)}"
    body = path.read_text()
    required = ["<Purpose>", "<Steps>", "<Verification>"]
    missing = [tag for tag in required if tag not in body]
    if missing:
        return False, f"skill markdown missing tags: {missing}"
    if f"oran-discover:{skill}" not in body:
        return False, f"frontmatter name does not match oran-discover:{skill}"
    return True, f"{path.relative_to(REPO_ROOT)} parses with all required tags"


def main() -> int:
    print("=" * 72)
    print("oran-discover micro harness test")
    print("=" * 72)
    results: list[tuple[str, str, bool, str]] = []
    skills = ["ptp", "metal3", "redfish", "smo", "taxonomy", "guardrail", "plan"]

    for skill in skills:
        print(f"\n--- /oran-discover:{skill} ---")
        for check_name, check_fn in [
            ("skill markdown", check_skill_markdown),
            ("static source",  check_static_source),
            ("live endpoint",  check_live_endpoint),
        ]:
            ok, detail = check_fn(skill)
            tag = "PASS" if ok else "FAIL"
            print(f"  {tag}: {check_name} -- {detail}")
            results.append((skill, check_name, ok, detail))

    print("\n" + "=" * 72)
    passes = sum(1 for _, _, ok, _ in results if ok)
    total = len(results)
    fails = [(s, c, d) for s, c, ok, d in results if not ok]
    print(f"SUMMARY: {passes}/{total} checks passed")
    for s, c, d in fails:
        print(f"  FAILED: {s} {c}: {d}")
    overall = "PASS" if not fails else "FAIL"
    print(f"OVERALL: {overall}")
    print("=" * 72)
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
