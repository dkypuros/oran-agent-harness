"""HTTP wrapper for the harness walker and the research bench.

Wraps:
  harness.runtime.walker.walk()           (single scenario walk-through)
  5G_O-RAN_SIM/bench/runner.run_scenario() and run_all() (bench)
  5G_O-RAN_SIM/shared_trace                (trace files)

Endpoints:
  GET  /health             -> 200 with service info
  GET  /scenarios          -> list of known scenario ids
  GET  /run/{scenario_id}  -> walk one scenario, return AuditEvent
  GET  /bench/all          -> run all 5 scenarios via the bench, return summary
  GET  /traces             -> list available trace files
  GET  /traces/{scenario_id}  -> return the per-scenario JSONL trace contents
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException

_REPO_ROOT = Path("/app")
_SIM_ROOT = _REPO_ROOT / "5G_O-RAN_SIM"
_SCENARIOS_DIR = _REPO_ROOT / "scenarios"
_TRACE_DIR = _SIM_ROOT / "shared_trace"

for p in (str(_REPO_ROOT), str(_SIM_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

from harness.runtime import walker
from bench import runner as bench_runner


app = FastAPI(
    title="MacBook lab harness walker",
    description="HTTP wrapper for the harness walker and research bench",
    version="0.1.0",
)


@app.get("/health")
def health() -> dict[str, Any]:
    return {"service": "harness-walker", "scenarios_dir": str(_SCENARIOS_DIR)}


@app.get("/scenarios")
def list_scenarios() -> dict[str, Any]:
    return {"scenarios": bench_runner.SCENARIO_IDS}


@app.get("/run/{scenario_id}")
def run_scenario(scenario_id: str) -> dict[str, Any]:
    fault_payload_path = _SCENARIOS_DIR / scenario_id / "fault_payload.json"
    if not fault_payload_path.exists():
        raise HTTPException(status_code=404, detail=f"unknown scenario {scenario_id}")
    audit_event = walker.walk(str(fault_payload_path), verbose=False)
    return audit_event


@app.get("/bench/all")
def bench_all() -> dict[str, Any]:
    return bench_runner.run_all()


@app.get("/traces")
def list_traces() -> dict[str, Any]:
    available = []
    if _TRACE_DIR.exists():
        for p in sorted(_TRACE_DIR.glob("*.jsonl")):
            available.append(
                {
                    "scenario_id": p.stem.replace(".example", ""),
                    "name": p.name,
                    "size_bytes": p.stat().st_size,
                    "example": p.suffix == ".jsonl" and ".example." in p.name,
                }
            )
    return {"count": len(available), "traces": available}


@app.get("/traces/{scenario_id}")
def get_trace(scenario_id: str, limit: int = 200) -> dict[str, Any]:
    runtime_path = _TRACE_DIR / f"{scenario_id}.jsonl"
    example_path = _TRACE_DIR / f"{scenario_id}.example.jsonl"
    target = runtime_path if runtime_path.exists() else example_path
    if not target.exists():
        raise HTTPException(status_code=404, detail=f"no trace for {scenario_id}")
    records: list[dict[str, Any]] = []
    with target.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return {
        "scenario_id": scenario_id,
        "source": target.name,
        "count": len(records),
        "records": records[-limit:],
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8096))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
