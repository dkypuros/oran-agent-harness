"""HTTP wrapper for the Redfish BMC SimpleUpdate stub.

Conforms to:
  DMTF Redfish DSP0266 (ref 46)
Wraps 5G_O-RAN_SIM/oam/redfish_bmc_stub.simple_update() and get_task_status() over HTTP.

Endpoints:
  GET  /health   -> 200 with service info
  GET  /state    -> latest task per scenario
  GET  /history  -> all task lifecycle records with optional ?limit=N
  POST /update   -> invokes SimpleUpdate, runs the task lifecycle, returns records
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI

_REPO_ROOT = Path("/app")
_SIM_ROOT = _REPO_ROOT / "5G_O-RAN_SIM"
for p in (str(_REPO_ROOT), str(_SIM_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

from oam.redfish_bmc_stub import simple_update, get_task_status


app = FastAPI(
    title="MacBook lab Redfish BMC stub",
    description="HTTP wrapper for Redfish UpdateService.SimpleUpdate task lifecycle",
    version="0.1.0",
)

_HISTORY: list[dict[str, Any]] = []
_LATEST_BY_SCENARIO: dict[str, dict[str, Any]] = {}


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "service": "redfish-bmc-stub",
        "task_records": len(_HISTORY),
        "scenarios_tracked": list(_LATEST_BY_SCENARIO.keys()),
    }


@app.get("/state")
def state() -> dict[str, Any]:
    return {
        "scenarios_tracked": list(_LATEST_BY_SCENARIO.keys()),
        "latest_per_scenario": _LATEST_BY_SCENARIO,
    }


@app.get("/history")
def history(limit: int = 50) -> dict[str, Any]:
    return {"count": len(_HISTORY), "tasks": _HISTORY[-limit:]}


@app.post("/update")
def update(
    scenario_id: str = "E_nic_firmware_update",
    image_uri: str = "registry.redhat.io/firmware/intel-e810:1.13.7",
) -> dict[str, Any]:
    task_uri = simple_update(scenario_id=scenario_id, image_uri=image_uri)
    lifecycle = get_task_status(scenario_id=scenario_id, task_uri=task_uri)
    records = [{"task_uri": task_uri, **rec} for rec in lifecycle]
    _HISTORY.extend(records)
    if records:
        _LATEST_BY_SCENARIO[scenario_id] = records[-1]
    return {"task_uri": task_uri, "lifecycle": lifecycle}


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8093))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
