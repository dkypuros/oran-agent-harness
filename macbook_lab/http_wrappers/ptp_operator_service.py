"""HTTP wrapper for the PTP operator stub publisher.

Conforms to:
  harness-unique lab plumbing, no upstream spec
  Underlying publisher conforms to O-RAN.WG6 O-Cloud Notification API + CloudEvents 1.0

Wraps 5G_O-RAN_SIM/oam/ptp_operator_stub.emit_alarm_sequence() in a small FastAPI service so
the macbook_lab dashboard can fetch its current state over HTTP. Exposes:

  GET  /health   -> 200 with service info
  GET  /state    -> last emitted sequence
  GET  /history  -> all history with optional ?limit=N
  POST /publish  -> trigger a fresh emit_alarm_sequence and return the events
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

from oam.ptp_operator_stub import emit_alarm_sequence


app = FastAPI(
    title="MacBook lab PTP operator stub",
    description="HTTP wrapper for the PTP operator alarm publisher",
    version="0.1.0",
)

_HISTORY: list[dict[str, Any]] = []


@app.get("/health")
def health() -> dict[str, Any]:
    return {"service": "ptp-operator-stub", "events_published": len(_HISTORY)}


@app.get("/state")
def state() -> dict[str, Any]:
    if not _HISTORY:
        return {"published_count": 0, "latest": None}
    return {"published_count": len(_HISTORY), "latest": _HISTORY[-1]}


@app.get("/history")
def history(limit: int = 50) -> dict[str, Any]:
    return {"count": len(_HISTORY), "events": _HISTORY[-limit:]}


@app.post("/publish")
def publish(
    node: str = "worker-ran-02.dallas.example.com",
    scenario_id: str = "D_phc_drift_hw_only",
) -> dict[str, Any]:
    events = emit_alarm_sequence(node=node, scenario_id=scenario_id)
    _HISTORY.extend(events)
    return {"emitted": len(events), "events": events}


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8091))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
