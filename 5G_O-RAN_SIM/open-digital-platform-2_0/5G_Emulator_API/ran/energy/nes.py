#!/usr/bin/env python3
"""Network Energy Savings Service (NES).

Spec: O-RAN.WG1.Network-Energy-Savings-Technical-Report-R003-v02.00
      (Network Energy Savings Use Cases Technical Report),
      O-RAN.WG1.mMIMO-Use-Cases-TR-v01.00 (massive MIMO use cases).

This service models RAN Network Energy Savings (NES) for the 5G emulator:

  - Per-cell energy state and instantaneous power consumption (Watts).
  - Sleep modes spanning the standard NES granularity ladder:
        ACTIVE -> MICRO_SLEEP (symbol-level / advanced sleep)
               -> CARRIER_OFF (carrier / RF-chain shutdown, antenna muting)
               -> CELL_OFF    (full cell switch-off).
  - Energy KPIs: total power (W), energy efficiency (bits/Joule), PUE-style
    overhead, and aggregate savings versus an all-active baseline.
  - ES policies enabled / disabled by an rApp through the Non-RT RIC A1 hook
    (the policy carries the activation condition and target sleep depth).
  - Wake-up triggers (traffic load, scheduled, or A1 policy) that restore a cell
    to ACTIVE.

The service registers with the NRF as nf_type "NES".

Port: 8130
"""
import argparse, logging, uuid, random
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from enum import Enum, IntEnum
from typing import Any, Dict, List, Optional
import requests, uvicorn
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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("svc")

SERVICE_PORT = 8130
NRF_URL = "http://127.0.0.1:8000"


def _now() -> datetime:
    return datetime.now(timezone.utc)


# =============================================================================
# Enumerations (per O-RAN.WG1 Network Energy Savings TR)
# =============================================================================

class SleepMode(str, Enum):
    """NES sleep-mode ladder by increasing depth and wake-up latency.

    The NES TR distinguishes time-domain (symbol/slot/subframe-level "advanced"
    sleep), frequency-domain (carrier shutdown), spatial-domain (RF-chain /
    antenna muting), and full cell switch-off techniques.
    """
    ACTIVE = "ACTIVE"             # no energy saving, all resources on
    MICRO_SLEEP = "MICRO_SLEEP"   # symbol/slot-level advanced sleep (time domain)
    CARRIER_OFF = "CARRIER_OFF"   # carrier shutdown / RF-chain muting (freq+spatial)
    CELL_OFF = "CELL_OFF"         # full cell switch-off (deepest sleep)


class WakeTrigger(str, Enum):
    """Source that returned a cell to ACTIVE (NES wake-up triggers)."""
    TRAFFIC_LOAD = "TRAFFIC_LOAD"     # offered load crossed the wake threshold
    SCHEDULED = "SCHEDULED"           # time-of-day schedule
    A1_POLICY = "A1_POLICY"           # rApp / Non-RT RIC A1 policy decision
    MANUAL = "MANUAL"                 # operator / API request


class EsPolicyTrigger(str, Enum):
    """Condition that activates an energy-savings policy."""
    LOW_PRB_UTILIZATION = "LOW_PRB_UTILIZATION"
    LOW_RRC_CONNECTIONS = "LOW_RRC_CONNECTIONS"
    TIME_OF_DAY = "TIME_OF_DAY"
    AIML_FORECAST = "AIML_FORECAST"


# Per-mode power scaling factor vs the cell's active (max) power draw, and the
# wake-up latency cost of leaving that mode. Drawn from typical NES TR profiles.
_MODE_POWER_FACTOR: Dict[SleepMode, float] = {
    SleepMode.ACTIVE: 1.00,
    SleepMode.MICRO_SLEEP: 0.70,
    SleepMode.CARRIER_OFF: 0.35,
    SleepMode.CELL_OFF: 0.08,   # residual M-plane / housekeeping power
}
_MODE_WAKEUP_MS: Dict[SleepMode, float] = {
    SleepMode.ACTIVE: 0.0,
    SleepMode.MICRO_SLEEP: 1.0,
    SleepMode.CARRIER_OFF: 50.0,
    SleepMode.CELL_OFF: 5000.0,
}


# =============================================================================
# Data Models (Pydantic)
# =============================================================================

class CellEnergyState(BaseModel):
    """Per-cell energy state, power draw, and current sleep mode."""
    cell_id: str
    name: str = Field(default="")
    max_power_watts: float = Field(default=350.0, ge=0, description="active (full-load) power draw (W)")
    static_power_watts: float = Field(default=60.0, ge=0, description="fixed overhead power (W)")
    num_tx_antennas: int = Field(default=64, ge=0, description="mMIMO Tx antenna count")
    active_carriers: int = Field(default=1, ge=0)
    sleep_mode: SleepMode = Field(default=SleepMode.ACTIVE)
    es_enabled: bool = Field(default=True, description="energy-savings eligible")
    load_factor: float = Field(default=0.5, ge=0, le=1, description="offered traffic load (0..1)")
    last_wake_trigger: Optional[WakeTrigger] = Field(default=None)
    updated_at: datetime = Field(default_factory=_now)

    def current_power_watts(self) -> float:
        """Instantaneous power: static overhead + load-scaled dynamic power, then mode factor."""
        factor = _MODE_POWER_FACTOR[self.sleep_mode]
        dynamic = (self.max_power_watts - self.static_power_watts) * self.load_factor
        power = self.static_power_watts + dynamic
        return round(power * factor, 2)

    def wakeup_latency_ms(self) -> float:
        return _MODE_WAKEUP_MS[self.sleep_mode]


class SleepRequest(BaseModel):
    """Request body to place a cell into a sleep mode."""
    sleep_mode: SleepMode = Field(..., description="target sleep depth")
    reason: str = Field(default="", description="why the cell is being put to sleep")


class WakeRequest(BaseModel):
    """Request body to wake a cell."""
    trigger: WakeTrigger = Field(default=WakeTrigger.MANUAL)
    reason: str = Field(default="")


class EsPolicy(BaseModel):
    """Energy-savings policy (rApp/A1-driven) governing automated sleep decisions."""
    policy_id: str = Field(default_factory=lambda: f"es-{uuid.uuid4().hex[:8]}")
    name: str = Field(..., description="policy name")
    trigger: EsPolicyTrigger = Field(default=EsPolicyTrigger.LOW_PRB_UTILIZATION)
    target_sleep_mode: SleepMode = Field(default=SleepMode.CARRIER_OFF)
    threshold: float = Field(default=15.0, description="trigger threshold (% PRB, count, or hour)")
    target_cells: List[str] = Field(default_factory=list, description="cells governed (empty = all)")
    enabled: bool = Field(default=True)
    a1_policy_type_id: Optional[int] = Field(default=20008, description="A1 ES policy type id")
    created_at: datetime = Field(default_factory=_now)


# =============================================================================
# In-memory NES state
# =============================================================================

cells: Dict[str, CellEnergyState] = {}
es_policies: Dict[str, EsPolicy] = {}


def _seed_cells() -> None:
    """Seed a small cell grid with a mix of energy states (one already sleeping)."""
    seed = [
        ("cell-001", "Macro-Downtown", 420.0, 70.0, 64, 0.62, SleepMode.ACTIVE),
        ("cell-002", "Macro-Suburb", 380.0, 65.0, 32, 0.31, SleepMode.ACTIVE),
        ("cell-003", "SmallCell-Mall", 120.0, 25.0, 8, 0.08, SleepMode.CARRIER_OFF),
        ("cell-004", "Macro-Industrial", 400.0, 68.0, 64, 0.74, SleepMode.ACTIVE),
        ("cell-005", "SmallCell-Residential", 110.0, 22.0, 8, 0.04, SleepMode.CELL_OFF),
    ]
    for cid, name, mp, sp, ant, load, mode in seed:
        cells[cid] = CellEnergyState(
            cell_id=cid, name=name, max_power_watts=mp, static_power_watts=sp,
            num_tx_antennas=ant, active_carriers=(0 if mode == SleepMode.CELL_OFF else 1),
            load_factor=load, sleep_mode=mode,
        )


def _seed_policies() -> None:
    """Seed a default low-load energy-savings policy."""
    pol = EsPolicy(
        policy_id="es-default-lowload",
        name="Off-peak Carrier Shutdown",
        trigger=EsPolicyTrigger.LOW_PRB_UTILIZATION,
        target_sleep_mode=SleepMode.CARRIER_OFF,
        threshold=15.0,
        target_cells=[],
        enabled=True,
    )
    es_policies[pol.policy_id] = pol


def _baseline_power() -> float:
    """All-cells-active baseline power for savings comparison (W)."""
    total = 0.0
    for c in cells.values():
        dynamic = (c.max_power_watts - c.static_power_watts) * c.load_factor
        total += c.static_power_watts + dynamic
    return round(total, 2)


def _network_throughput_mbps() -> float:
    """Estimated aggregate served throughput (Mbps) used for energy-efficiency KPI."""
    total = 0.0
    for c in cells.values():
        if c.sleep_mode == SleepMode.CELL_OFF:
            continue
        # crude capacity model: antennas * load * per-antenna spectral capacity
        cap_factor = _MODE_POWER_FACTOR[c.sleep_mode]  # reduced capacity when sleeping
        total += c.num_tx_antennas * 15.0 * c.load_factor * cap_factor
    return round(total, 1)


# =============================================================================
# FastAPI application
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    _seed_cells()
    _seed_policies()
    try:
        requests.post(f"{NRF_URL}/register", json={"nf_type": "NES", "ip": "127.0.0.1", "port": SERVICE_PORT}, timeout=3)
    except requests.RequestException:
        pass
    logger.info("Network Energy Savings (NES) service ready on port %s", SERVICE_PORT)
    yield


app = FastAPI(
    title="Network Energy Savings Service (NES)",
    description="O-RAN WG1 Network Energy Savings: sleep modes, energy KPIs, ES policies, wake-up triggers",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# =============================================================================
# Cell energy state + sleep / wake control
# =============================================================================

@app.get("/nes/cells")
async def list_cells(sleep_mode: Optional[SleepMode] = None):
    """List per-cell energy state, current sleep mode, and instantaneous power."""
    out = []
    for c in cells.values():
        if sleep_mode is not None and c.sleep_mode != sleep_mode:
            continue
        d = c.model_dump()
        d["current_power_watts"] = c.current_power_watts()
        d["wakeup_latency_ms"] = c.wakeup_latency_ms()
        out.append(d)
    return {
        "spec": "O-RAN.WG1.Network-Energy-Savings-Technical-Report-R003-v02.00",
        "count": len(out),
        "cells": out,
    }


@app.post("/nes/cells/{cell_id}/sleep")
async def set_sleep(cell_id: str, req: SleepRequest):
    """Place a cell into a sleep mode (cell switch-off, carrier/RF shutdown, or micro-sleep)."""
    with _tracer.start_as_current_span("nes_set_sleep") as span:
        if cell_id not in cells:
            raise HTTPException(status_code=404, detail="Cell not found")
        cell = cells[cell_id]
        if not cell.es_enabled and req.sleep_mode != SleepMode.ACTIVE:
            raise HTTPException(status_code=409, detail="Cell is not energy-savings eligible")
        span.set_attribute("cell.id", cell_id)
        span.set_attribute("sleep.mode", req.sleep_mode.value)
        prev = cell.sleep_mode
        cell.sleep_mode = req.sleep_mode
        cell.active_carriers = 0 if req.sleep_mode == SleepMode.CELL_OFF else max(1, cell.active_carriers)
        cell.last_wake_trigger = None
        cell.updated_at = _now()
        logger.info("Cell %s sleep mode %s -> %s (%s)", cell_id, prev.value, req.sleep_mode.value, req.reason)
        return {
            "cell_id": cell_id,
            "previous_mode": prev.value,
            "sleep_mode": cell.sleep_mode.value,
            "current_power_watts": cell.current_power_watts(),
            "wakeup_latency_ms": cell.wakeup_latency_ms(),
        }


@app.post("/nes/cells/{cell_id}/wake")
async def wake_cell(cell_id: str, req: WakeRequest):
    """Wake a cell back to ACTIVE in response to a wake-up trigger."""
    if cell_id not in cells:
        raise HTTPException(status_code=404, detail="Cell not found")
    cell = cells[cell_id]
    prev = cell.sleep_mode
    cell.sleep_mode = SleepMode.ACTIVE
    cell.active_carriers = max(1, cell.active_carriers)
    cell.last_wake_trigger = req.trigger
    cell.updated_at = _now()
    logger.info("Cell %s woke %s -> ACTIVE (trigger %s)", cell_id, prev.value, req.trigger.value)
    return {
        "cell_id": cell_id,
        "previous_mode": prev.value,
        "sleep_mode": cell.sleep_mode.value,
        "trigger": req.trigger.value,
        "current_power_watts": cell.current_power_watts(),
    }


# =============================================================================
# Energy-savings policies (rApp / A1 hook)
# =============================================================================

@app.get("/nes/policies", response_model=List[EsPolicy])
async def list_policies(enabled: Optional[bool] = None):
    """List energy-savings policies, optionally filtered by enabled state."""
    result = list(es_policies.values())
    if enabled is not None:
        result = [p for p in result if p.enabled == enabled]
    return result


@app.post("/nes/policies", response_model=EsPolicy, status_code=201)
async def create_policy(policy: EsPolicy):
    """Create an energy-savings policy (the rApp/A1-driven control of automated sleep)."""
    for cid in policy.target_cells:
        if cid not in cells:
            raise HTTPException(status_code=400, detail=f"Unknown target cell: {cid}")
    es_policies[policy.policy_id] = policy
    logger.info("Created ES policy %s (%s -> %s)", policy.policy_id,
                policy.trigger.value, policy.target_sleep_mode.value)
    return policy


# =============================================================================
# Energy KPIs and savings report
# =============================================================================

@app.get("/nes/kpi")
async def energy_kpi():
    """Network-wide energy KPIs: total power, energy efficiency (bits/Joule), per-cell breakdown."""
    total_power = round(sum(c.current_power_watts() for c in cells.values()), 2)
    throughput_mbps = _network_throughput_mbps()
    # bits/Joule = (Mbps * 1e6 bits/s) / Watts (Joule/s) when power > 0.
    if total_power > 0:
        bits_per_joule = round((throughput_mbps * 1_000_000.0) / total_power, 1)
    else:
        bits_per_joule = 0.0
    sleeping = sum(1 for c in cells.values() if c.sleep_mode != SleepMode.ACTIVE)
    return {
        "spec": "O-RAN.WG1.Network-Energy-Savings-Technical-Report-R003-v02.00",
        "generated_at": _now().isoformat(),
        "total_cells": len(cells),
        "sleeping_cells": sleeping,
        "total_power_watts": total_power,
        "aggregate_throughput_mbps": throughput_mbps,
        "energy_efficiency_bits_per_joule": bits_per_joule,
        "per_cell": [
            {
                "cell_id": c.cell_id,
                "sleep_mode": c.sleep_mode.value,
                "power_watts": c.current_power_watts(),
                "load_factor": c.load_factor,
            }
            for c in cells.values()
        ],
    }


@app.get("/nes/savings-report")
async def savings_report():
    """Energy savings versus an all-cells-active baseline (Watts and percent saved)."""
    baseline = _baseline_power()
    current = round(sum(c.current_power_watts() for c in cells.values()), 2)
    saved = round(baseline - current, 2)
    pct = round((saved / baseline) * 100.0, 2) if baseline > 0 else 0.0
    return {
        "spec": "O-RAN.WG1.Network-Energy-Savings-Technical-Report-R003-v02.00",
        "generated_at": _now().isoformat(),
        "baseline_power_watts": baseline,
        "current_power_watts": current,
        "power_saved_watts": saved,
        "energy_saved_percent": pct,
        "active_policies": sum(1 for p in es_policies.values() if p.enabled),
        "per_cell_savings": [
            {
                "cell_id": c.cell_id,
                "sleep_mode": c.sleep_mode.value,
                "power_saved_watts": round(
                    (c.static_power_watts + (c.max_power_watts - c.static_power_watts) * c.load_factor)
                    - c.current_power_watts(), 2),
            }
            for c in cells.values()
        ],
    }


# =============================================================================
# Health
# =============================================================================

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "nes", "spec": "O-RAN.WG1.Network-Energy-Savings-Technical-Report-R003-v02.00"}


if __name__ == "__main__":
    p = argparse.ArgumentParser(); p.add_argument("--host", default="0.0.0.0"); p.add_argument("--port", type=int, default=SERVICE_PORT)
    a = p.parse_args(); uvicorn.run(app, host=a.host, port=a.port)
