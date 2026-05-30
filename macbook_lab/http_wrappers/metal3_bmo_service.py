"""HTTP wrapper for the Metal3 Baremetal Operator firmware push stub.

Conforms to:
  Metal3 project, Baremetal Operator CRDs (refs 7, 8)
Wraps 5G_O-RAN_SIM/oam/metal3_bmo_stub.apply_firmware() over HTTP.

Endpoints:
  GET  /health   -> 200 with service info
  GET  /state    -> last firmware phase per scenario_id
  GET  /history  -> all phase records with optional ?limit=N
  POST /apply    -> run apply_firmware(scenario_id, component); returns phase records
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

from oam.metal3_bmo_stub import apply_firmware


app = FastAPI(
    title="MacBook lab Metal3 BMO stub",
    description="HTTP wrapper for Metal3 firmware push phases",
    version="0.1.0",
)

_HISTORY: list[dict[str, Any]] = []
_LATEST_BY_SCENARIO: dict[str, dict[str, Any]] = {}


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "service": "metal3-bmo-stub",
        "phases_recorded": len(_HISTORY),
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
    return {"count": len(_HISTORY), "phases": _HISTORY[-limit:]}


@app.post("/apply")
def apply(
    scenario_id: str = "E_nic_firmware_update",
    component: str = "intel-e810-nic",
) -> dict[str, Any]:
    records = apply_firmware(scenario_id=scenario_id, component=component)
    _HISTORY.extend(records)
    if records:
        _LATEST_BY_SCENARIO[scenario_id] = records[-1]
    return {"applied": len(records), "records": records}


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8092))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
