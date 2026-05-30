#!/usr/bin/env python3
"""O-RU (O-RAN Radio Unit) - O-RAN WG4 Open Fronthaul service exposing CUS-Plane + M-Plane.

Spec: O-RAN.WG4.TS.CUS.0-R005-v20.00 (Control/User/Synchronization Plane),
      O-RAN.WG4.TS.MP.0-R005-v20.00 (Management Plane).
Conformance: O-RAN.WG4.TS.CONF.0-R005-v15.00.
Timing:      O-RAN.WG4.CTI-TMP.0-R003-v04.00 (CTI timing).

Runnable FastAPI service on port 8120. It wraps the cus_plane and m_plane libraries: M-Plane NETCONF
style get/edit-config over the in-memory datastore (uplane-conf, module-cap, supervision watchdog,
software management, performance management, fault management, hardware inventory) and the
CUS-Plane statistics / S-Plane PTP sync / beamforming views.
"""
import argparse
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from enum import Enum, IntEnum
from typing import Any, Dict, List, Optional

import requests
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

try:
    from opentelemetry import trace
    _tracer = trace.get_tracer(__name__)
except Exception:
    class _NoopSpan:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def set_attribute(self, *a, **k): pass
    class _NoopTracer:
        def start_as_current_span(self, *a, **k): return _NoopSpan()
    _tracer = _NoopTracer()

# Import the sibling CUS/M-Plane libraries. Works as a package (relative) and when the file is
# executed directly (absolute fallback after adding the package parents to sys.path).
try:
    from .cus_plane import CusPlaneStats, SyncConfig, default_beamforming
    from .m_plane import MPlaneDatastore, MPlaneArchitecture, Alarm, hardware_inventory
except ImportError:  # pragma: no cover - direct execution path
    import os
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from cus_plane import CusPlaneStats, SyncConfig, default_beamforming
    from m_plane import MPlaneDatastore, MPlaneArchitecture, Alarm, hardware_inventory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("o-ru")

SERVICE_PORT = 8120
NRF_URL = "http://127.0.0.1:8000"

# In-memory M-Plane datastore and CUS-Plane stats helper (process-lifetime singletons).
_datastore = MPlaneDatastore(architecture=MPlaneArchitecture.HYBRID)
_cus_stats = CusPlaneStats(eaxc_id=0, num_prb=273)
# Seed one cleared informational alarm so the FM list is non-trivial in demos.
_datastore.tree.fault_management.active_alarm_list.append(
    Alarm(fault_id=1001, fault_source="rf-board-0", fault_severity="WARNING",
          is_cleared=True, fault_text="RF board temperature returned to normal",
          event_time=datetime.now(timezone.utc).isoformat())
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        requests.post(f"{NRF_URL}/register", json={"nf_type": "O_RU", "ip": "127.0.0.1", "port": SERVICE_PORT}, timeout=3)
    except requests.RequestException:
        pass
    yield


app = FastAPI(title="O-RU (O-RAN WG4 Open Fronthaul)", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------
class EditConfigRequest(BaseModel):
    """NETCONF edit-config (operation=merge) partial datastore patch."""
    patch: Dict[str, Any] = Field(default_factory=dict, description="partial M-Plane config tree")


class SwActivateRequest(BaseModel):
    """o-ran-software-management activate RPC input."""
    slot_name: str = Field(..., description="software-slot name to activate")


# ---------------------------------------------------------------------------
# M-Plane routes (o-ran-* YANG modules)
# ---------------------------------------------------------------------------
@app.get("/o-ran/hw")
async def get_hardware():
    """o-ran-hardware: component inventory (ietf-hardware)."""
    with _tracer.start_as_current_span("o-ru_get_hw"):
        return hardware_inventory()


@app.get("/o-ran/uplane-conf")
async def get_uplane_conf():
    """NETCONF <get> of o-ran-uplane-conf (endpoints, carriers, array-carriers)."""
    return _datastore.get("o-ran-uplane-conf")


@app.put("/o-ran/uplane-conf")
async def put_uplane_conf(req: EditConfigRequest):
    """NETCONF <edit-config> operation=merge against o-ran-uplane-conf."""
    with _tracer.start_as_current_span("o-ru_edit_uplane_conf"):
        try:
            _datastore.merge({"uplane_conf": req.patch})
        except Exception as exc:  # pydantic validation of merged tree
            raise HTTPException(status_code=400, detail=f"edit-config failed: {exc}")
        return {"result": "ok", "uplane_conf": _datastore.get("o-ran-uplane-conf")}


@app.get("/o-ran/module-cap")
async def get_module_cap():
    """NETCONF <get> of o-ran-module-cap (band/compression caps, supported section types)."""
    return _datastore.get("o-ran-module-cap")


@app.get("/o-ran/supervision")
async def get_supervision():
    """o-ran-supervision watchdog status (cu-plane monitoring + supervision interval)."""
    return _datastore.supervision_watchdog()


@app.post("/o-ran/supervision/reset")
async def reset_supervision():
    """Pet the supervision watchdog (supervision-notification keep-alive)."""
    _datastore.pet()
    return _datastore.supervision_watchdog()


@app.post("/o-ran/sw-management/activate")
async def sw_activate(req: SwActivateRequest):
    """o-ran-software-management: activate a software-slot (running flag toggles)."""
    slots = _datastore.tree.software_management.software_slots
    target = next((s for s in slots if s.name == req.slot_name), None)
    if target is None:
        raise HTTPException(status_code=404, detail=f"software-slot not found: {req.slot_name}")
    for slot in slots:
        slot.active = slot.name == req.slot_name
        slot.running = slot.name == req.slot_name
    return {
        "result": "ACTIVATED",
        "slot": req.slot_name,
        "software_management": _datastore.get("o-ran-software-management"),
    }


@app.get("/o-ran/performance")
async def get_performance():
    """NETCONF <get> of o-ran-performance-management (RSSI, RX-window measurements)."""
    return _datastore.get("o-ran-performance-management")


@app.get("/o-ran/fm/alarms")
async def get_alarms():
    """o-ran-fm active-alarm-list (fault management)."""
    return _datastore.get("o-ran-fm")


# ---------------------------------------------------------------------------
# CUS-Plane routes (eCPRI C/U/S planes + beamforming)
# ---------------------------------------------------------------------------
@app.get("/cus/c-plane/stats")
async def c_plane_stats():
    """Simulated C-Plane statistics (section transmit/receive counters)."""
    return _cus_stats.c_plane_stats()


@app.get("/cus/u-plane/stats")
async def u_plane_stats():
    """Simulated U-Plane statistics (IQ frames, throughput, RX-window)."""
    return _cus_stats.u_plane_stats()


@app.get("/cus/s-plane/sync")
async def s_plane_sync():
    """S-Plane PTP synchronization status: lock state, clock class, time error."""
    cfg = SyncConfig()
    stats = _cus_stats.s_plane_stats()
    return {
        "spec": "O-RAN.WG4.TS.CUS.0-R005-v20.00 / O-RAN.WG4.CTI-TMP.0-R003-v04.00",
        "sync_state": cfg.sync_state.value,          # LOCKED
        "ptp_profile": cfg.ptp_profile.value,
        "synce_mode": cfg.synce_mode.value,
        "lls_topology": cfg.lls_topology.value,
        "clock_class": cfg.clock_class,
        "clock_accuracy": cfg.clock_accuracy,
        "time_error_ns": cfg.measured_te_ns,
        "max_te_budget_ns": cfg.max_te_budget_ns,
        "stats": stats,
    }


@app.get("/cus/beamforming")
async def beamforming():
    """Beamforming configuration: beamId plus per-antenna weight vector."""
    bf = default_beamforming(num_weights=32)
    return {
        "spec": "O-RAN.WG4.TS.CUS.0-R005-v20.00",
        "beam_id": bf.beam_id,
        "bf_compression": bf.bf_compression.value,
        "bf_iq_width": bf.bf_iq_width,
        "num_bf_weights": bf.num_bf_weights,
        "weights": [w.model_dump() for w in bf.weights],
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "o-ru", "spec": "O-RAN.WG4.TS.CUS/MP.0-R005-v20.00"}


if __name__ == "__main__":
    p = argparse.ArgumentParser(); p.add_argument("--host", default="0.0.0.0"); p.add_argument("--port", type=int, default=SERVICE_PORT)
    a = p.parse_args(); uvicorn.run(app, host=a.host, port=a.port)
