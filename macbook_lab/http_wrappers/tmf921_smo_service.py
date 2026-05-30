"""HTTP wrapper for the TMF921 SMO companion intent emitter.

Conforms to:
  TMF921 Intent Management API (ref 19)
Wraps 5G_O-RAN_SIM/smo/tmf921_intent_emitter.emit_intent() over HTTP.

Endpoints:
  GET  /health   -> 200 with service info
  GET  /state    -> latest emitted intents
  GET  /history  -> all emitted intents with optional ?limit=N
  POST /emit     -> emit a fresh intent, return the envelope
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

from smo.tmf921_intent_emitter import emit_intent


app = FastAPI(
    title="MacBook lab TMF921 SMO stub",
    description="HTTP wrapper for the TMF921 SMO companion intent emitter",
    version="0.1.0",
)

_HISTORY: list[dict[str, Any]] = []


@app.get("/health")
def health() -> dict[str, Any]:
    return {"service": "tmf921-smo-stub", "intents_emitted": len(_HISTORY)}


@app.get("/state")
def state() -> dict[str, Any]:
    return {"emitted_count": len(_HISTORY), "latest": _HISTORY[-1] if _HISTORY else None}


@app.get("/history")
def history(limit: int = 50) -> dict[str, Any]:
    return {"count": len(_HISTORY), "intents": _HISTORY[-limit:]}


@app.post("/emit")
def emit(
    scenario_id: str = "E_nic_firmware_update",
    intent_type: str = "MaintenanceWindowNotification",
    affected_resources: list[str] | None = None,
    window_start: str = "2026-05-30T11:30:00Z",
    window_end: str = "2026-05-30T11:38:00Z",
    service_impact_hint: str = "reduced_capacity",
    expected_handover_count: int = 47,
) -> dict[str, Any]:
    if affected_resources is None:
        affected_resources = ["worker-ran-02.dallas.example.com"]
    envelope = emit_intent(
        scenario_id=scenario_id,
        intent_type=intent_type,
        affected_resources=affected_resources,
        window_start=window_start,
        window_end=window_end,
        service_impact_hint=service_impact_hint,
        expected_handover_count=expected_handover_count,
    )
    _HISTORY.append(envelope)
    return envelope


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8094))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
