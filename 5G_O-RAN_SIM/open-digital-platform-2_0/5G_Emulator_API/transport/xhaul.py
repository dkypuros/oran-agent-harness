#!/usr/bin/env python3
"""xHaul Transport & Synchronization Service (XHAUL).

Spec: O-RAN.WG9.XTRP-MGT.0-R004-v10.00 (Xhaul Transport Management),
      O-RAN.WG9.XTRP-SYN.0-R004-v07.00 (Xhaul Synchronization Architecture),
      O-RAN.WG9.XPSAAS.0-R005-v10.00 (Packet Switched Architecture & As-a-Service).

This service models the O-RAN WG9 transport (xHaul) and timing/synchronization
plane for the 5G emulator:

  - Transport nodes (cell-site routers, aggregation switches, PTP-aware nodes).
  - Fronthaul / midhaul / backhaul links with bandwidth and one-way latency.
  - PTP (IEEE 1588 / ITU-T G.8275.1 full timing support) and SyncE timing
    distribution across the packet network.
  - Clock node types per G.827x: T-GM (telecom grandmaster), T-BC (boundary
    clock), T-TSC (slave clock), with clock class / quality (G.8273.2 accuracy
    class), lock state, and holdover.
  - A sync topology (the timing distribution tree from the T-GM down to T-TSCs).
  - Network sync health and time-error budget against the C-plane/fronthaul
    Category-A/B network limits (G.8271.1 / O-RAN.WG4 sync requirements).

The service registers with the NRF as nf_type "XHAUL".

Port: 8131
"""
import argparse, logging, uuid
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

SERVICE_PORT = 8131
NRF_URL = "http://127.0.0.1:8000"


def _now() -> datetime:
    return datetime.now(timezone.utc)


# =============================================================================
# Enumerations (per O-RAN.WG9 XTRP-MGT / XTRP-SYN, ITU-T G.827x)
# =============================================================================

class XhaulSegment(str, Enum):
    """xHaul transport segment per O-RAN WG9 (split-aware transport)."""
    FRONTHAUL = "FRONTHAUL"   # O-RU <-> O-DU (eCPRI / IEEE 1914.3 RoE), tight budget
    MIDHAUL = "MIDHAUL"       # O-DU <-> O-CU (F1)
    BACKHAUL = "BACKHAUL"     # O-CU <-> 5GC (N2/N3)


class TransportNodeType(str, Enum):
    """Transport node role in the packet network."""
    CELL_SITE_ROUTER = "CELL_SITE_ROUTER"
    AGGREGATION_SWITCH = "AGGREGATION_SWITCH"
    PROVIDER_EDGE = "PROVIDER_EDGE"
    HUB_ROUTER = "HUB_ROUTER"


class ClockNodeType(str, Enum):
    """PTP timing clock node type per ITU-T G.8275.1 / G.8273.2."""
    T_GM = "T-GM"     # Telecom Grandmaster (PRTC/ePRTC source)
    T_BC = "T-BC"     # Telecom Boundary Clock
    T_TSC = "T-TSC"   # Telecom Time Slave Clock (at the O-RU/O-DU)


class ClockClass(IntEnum):
    """PTP clockClass values (IEEE 1588 / G.8275.1 profile)."""
    PRTC_LOCKED = 6          # locked to a PRC/PRTC traceable reference
    GM_HOLDOVER_IN_SPEC = 7  # grandmaster in holdover, within spec
    GM_HOLDOVER_OUT_SPEC = 140
    DEGRADED = 248           # default/degraded, not traceable
    SLAVE_ONLY = 255         # slave-only / not a clock source


class LockState(str, Enum):
    """Clock servo lock state."""
    LOCKED = "LOCKED"
    HOLDOVER = "HOLDOVER"
    FREERUN = "FREERUN"
    ACQUIRING = "ACQUIRING"


class SyncSource(str, Enum):
    """Frequency/phase synchronization source technology."""
    PTP = "PTP"           # IEEE 1588 packet timing (phase + frequency)
    SYNCE = "SyncE"       # physical-layer frequency (ITU-T G.8262)
    GNSS = "GNSS"         # satellite (PRTC at the T-GM)
    PTP_SYNCE = "PTP+SyncE"


# =============================================================================
# Data Models (Pydantic)
# =============================================================================

class TransportNode(BaseModel):
    """An xHaul transport node (router / switch) in the packet network."""
    node_id: str = Field(default_factory=lambda: f"tn-{uuid.uuid4().hex[:8]}")
    name: str
    node_type: TransportNodeType = Field(default=TransportNodeType.CELL_SITE_ROUTER)
    management_ip: str = Field(default="10.0.0.1")
    ptp_aware: bool = Field(default=True, description="participates in PTP timing")
    synce_capable: bool = Field(default=True, description="supports SyncE frequency")
    site: str = Field(default="", description="physical site / location label")
    created_at: datetime = Field(default_factory=_now)


class TransportLinkCreate(BaseModel):
    """Request body to create an xHaul transport link."""
    name: str
    segment: XhaulSegment = Field(default=XhaulSegment.FRONTHAUL)
    endpoint_a: str = Field(..., description="node_id or logical endpoint A")
    endpoint_b: str = Field(..., description="node_id or logical endpoint B")
    bandwidth_gbps: float = Field(default=25.0, ge=0, description="link capacity (Gbps)")
    one_way_latency_us: float = Field(default=50.0, ge=0, description="one-way latency (microseconds)")
    description: str = Field(default="")


class TransportLink(BaseModel):
    """An xHaul transport link with bandwidth and latency attributes."""
    link_id: str = Field(default_factory=lambda: f"ln-{uuid.uuid4().hex[:8]}")
    name: str
    segment: XhaulSegment = Field(default=XhaulSegment.FRONTHAUL)
    endpoint_a: str
    endpoint_b: str
    bandwidth_gbps: float = Field(default=25.0)
    utilization_percent: float = Field(default=0.0, ge=0, le=100)
    one_way_latency_us: float = Field(default=50.0)
    operational: bool = Field(default=True)
    description: str = Field(default="")
    created_at: datetime = Field(default_factory=_now)


class ClockNode(BaseModel):
    """A PTP/SyncE clock node (T-GM / T-BC / T-TSC) in the sync network."""
    clock_id: str = Field(default_factory=lambda: f"clk-{uuid.uuid4().hex[:8]}")
    name: str
    clock_type: ClockNodeType = Field(default=ClockNodeType.T_BC)
    clock_class: ClockClass = Field(default=ClockClass.PRTC_LOCKED)
    accuracy_class: str = Field(default="Class C", description="G.8273.2 accuracy class (A/B/C/D)")
    sync_source: SyncSource = Field(default=SyncSource.PTP_SYNCE)
    lock_state: LockState = Field(default=LockState.LOCKED)
    holdover: bool = Field(default=False, description="currently in holdover")
    parent_clock_id: Optional[str] = Field(default=None, description="upstream clock in the tree")
    time_error_ns: int = Field(default=10, description="measured time error vs reference (ns)")
    domain_number: int = Field(default=24, description="PTP domain (G.8275.1 default 24)")
    priority2: int = Field(default=128, description="BMCA priority2")
    node_id: Optional[str] = Field(default=None, description="hosting transport node_id")


# =============================================================================
# In-memory transport + sync state
# =============================================================================

nodes: Dict[str, TransportNode] = {}
links: Dict[str, TransportLink] = {}
clocks: Dict[str, ClockNode] = {}

# Time-error budget (nanoseconds) for the fronthaul network limit. G.8271.1
# Category-A/B network limit is 1100 ns at the end application (max|TE|).
TE_BUDGET_NS = 1100


def _seed_topology() -> None:
    """Seed a small xHaul topology: hub + cell-site + O-RU with a PTP timing tree."""
    hub = TransportNode(node_id="tn-hub", name="Aggregation Hub", site="Central Office",
                        node_type=TransportNodeType.HUB_ROUTER, management_ip="10.0.0.1")
    csr = TransportNode(node_id="tn-csr-1", name="Cell-Site Router 1", site="Site-A",
                        node_type=TransportNodeType.CELL_SITE_ROUTER, management_ip="10.0.1.1")
    agg = TransportNode(node_id="tn-agg-1", name="Aggregation Switch 1", site="Metro-1",
                        node_type=TransportNodeType.AGGREGATION_SWITCH, management_ip="10.0.2.1")
    for n in (hub, csr, agg):
        nodes[n.node_id] = n

    bh = TransportLink(link_id="ln-backhaul-1", name="Backhaul Hub<->5GC",
                       segment=XhaulSegment.BACKHAUL, endpoint_a="tn-hub", endpoint_b="5gc-core",
                       bandwidth_gbps=100.0, utilization_percent=42.0, one_way_latency_us=500.0,
                       description="O-CU to 5GC (N2/N3)")
    mh = TransportLink(link_id="ln-midhaul-1", name="Midhaul Agg<->Hub",
                       segment=XhaulSegment.MIDHAUL, endpoint_a="tn-agg-1", endpoint_b="tn-hub",
                       bandwidth_gbps=50.0, utilization_percent=33.0, one_way_latency_us=120.0,
                       description="O-DU to O-CU (F1)")
    fh = TransportLink(link_id="ln-fronthaul-1", name="Fronthaul CSR<->O-RU",
                       segment=XhaulSegment.FRONTHAUL, endpoint_a="tn-csr-1", endpoint_b="o-ru-1",
                       bandwidth_gbps=25.0, utilization_percent=58.0, one_way_latency_us=40.0,
                       description="O-DU to O-RU (eCPRI), tight latency budget")
    for ln in (bh, mh, fh):
        links[ln.link_id] = ln

    # Timing tree: T-GM (GNSS-locked) -> T-BC (boundary at agg) -> T-TSC (at O-RU).
    tgm = ClockNode(clock_id="clk-tgm", name="Telecom Grandmaster",
                    clock_type=ClockNodeType.T_GM, clock_class=ClockClass.PRTC_LOCKED,
                    accuracy_class="Class B", sync_source=SyncSource.GNSS,
                    lock_state=LockState.LOCKED, holdover=False, parent_clock_id=None,
                    time_error_ns=5, node_id="tn-hub")
    tbc = ClockNode(clock_id="clk-tbc-1", name="Boundary Clock Agg-1",
                    clock_type=ClockNodeType.T_BC, clock_class=ClockClass.PRTC_LOCKED,
                    accuracy_class="Class C", sync_source=SyncSource.PTP_SYNCE,
                    lock_state=LockState.LOCKED, holdover=False, parent_clock_id="clk-tgm",
                    time_error_ns=30, node_id="tn-agg-1")
    ttsc = ClockNode(clock_id="clk-ttsc-1", name="Slave Clock O-RU-1",
                     clock_type=ClockNodeType.T_TSC, clock_class=ClockClass.PRTC_LOCKED,
                     accuracy_class="Class C", sync_source=SyncSource.PTP_SYNCE,
                     lock_state=LockState.LOCKED, holdover=False, parent_clock_id="clk-tbc-1",
                     time_error_ns=70, node_id="tn-csr-1")
    for c in (tgm, tbc, ttsc):
        clocks[c.clock_id] = c


# =============================================================================
# FastAPI application
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    _seed_topology()
    try:
        requests.post(f"{NRF_URL}/register", json={"nf_type": "XHAUL", "ip": "127.0.0.1", "port": SERVICE_PORT}, timeout=3)
    except requests.RequestException:
        pass
    logger.info("xHaul transport & sync service ready on port %s", SERVICE_PORT)
    yield


app = FastAPI(
    title="xHaul Transport & Synchronization Service (XHAUL)",
    description="O-RAN WG9 xHaul transport nodes/links + PTP/SyncE timing distribution (T-GM/T-BC/T-TSC)",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# =============================================================================
# Transport nodes + links
# =============================================================================

@app.get("/xhaul/nodes", response_model=List[TransportNode])
async def list_nodes(node_type: Optional[TransportNodeType] = None):
    """List xHaul transport nodes, optionally filtered by node type."""
    result = list(nodes.values())
    if node_type is not None:
        result = [n for n in result if n.node_type == node_type]
    return result


@app.get("/xhaul/links", response_model=List[TransportLink])
async def list_links(segment: Optional[XhaulSegment] = None):
    """List fronthaul / midhaul / backhaul links with bandwidth and latency."""
    result = list(links.values())
    if segment is not None:
        result = [ln for ln in result if ln.segment == segment]
    return result


@app.post("/xhaul/links", response_model=TransportLink, status_code=201)
async def create_link(req: TransportLinkCreate):
    """Create an xHaul transport link between two endpoints."""
    with _tracer.start_as_current_span("xhaul_create_link") as span:
        span.set_attribute("link.segment", req.segment.value)
        link = TransportLink(
            name=req.name,
            segment=req.segment,
            endpoint_a=req.endpoint_a,
            endpoint_b=req.endpoint_b,
            bandwidth_gbps=req.bandwidth_gbps,
            one_way_latency_us=req.one_way_latency_us,
            description=req.description,
        )
        links[link.link_id] = link
        logger.info("Created xHaul %s link %s (%s<->%s)", req.segment.value, link.link_id,
                    req.endpoint_a, req.endpoint_b)
        return link


# =============================================================================
# Synchronization: clocks, topology, status
# =============================================================================

@app.get("/xhaul/sync/clocks", response_model=List[ClockNode])
async def list_clocks(clock_type: Optional[ClockNodeType] = None):
    """List PTP/SyncE clock nodes (T-GM / T-BC / T-TSC) with clock class and lock state."""
    result = list(clocks.values())
    if clock_type is not None:
        result = [c for c in result if c.clock_type == clock_type]
    return result


@app.get("/xhaul/sync/topology")
async def sync_topology():
    """Return the timing distribution tree from the T-GM down to the T-TSCs."""
    def _children(parent_id: Optional[str]) -> List[Dict[str, Any]]:
        out = []
        for c in clocks.values():
            if c.parent_clock_id == parent_id:
                out.append({
                    "clock_id": c.clock_id,
                    "name": c.name,
                    "clock_type": c.clock_type.value,
                    "clock_class": int(c.clock_class),
                    "lock_state": c.lock_state.value,
                    "time_error_ns": c.time_error_ns,
                    "sync_source": c.sync_source.value,
                    "children": _children(c.clock_id),
                })
        return out

    roots = _children(None)
    return {
        "spec": "O-RAN.WG9.XTRP-SYN.0-R004-v07.00",
        "ptp_profile": "ITU-T G.8275.1 (full timing support from the network)",
        "domain_number": 24,
        "tree": roots,
        "clock_count": len(clocks),
    }


@app.get("/xhaul/sync/status")
async def sync_status():
    """Network sync health: aggregate time error vs the fronthaul time-error budget."""
    if not clocks:
        return {
            "spec": "O-RAN.WG9.XTRP-SYN.0-R004-v07.00",
            "status": "NO_CLOCKS",
            "te_budget_ns": TE_BUDGET_NS,
        }
    # Worst-case end-application time error is approximated by the deepest T-TSC.
    tscs = [c for c in clocks.values() if c.clock_type == ClockNodeType.T_TSC]
    max_te = max((c.time_error_ns for c in tscs), default=max(c.time_error_ns for c in clocks.values()))
    in_holdover = [c.clock_id for c in clocks.values() if c.holdover or c.lock_state == LockState.HOLDOVER]
    unlocked = [c.clock_id for c in clocks.values() if c.lock_state in (LockState.FREERUN, LockState.ACQUIRING)]
    within_budget = max_te <= TE_BUDGET_NS
    has_gm = any(c.clock_type == ClockNodeType.T_GM and c.lock_state == LockState.LOCKED
                 for c in clocks.values())
    if not has_gm or unlocked:
        health = "DEGRADED"
    elif in_holdover or not within_budget:
        health = "WARNING"
    else:
        health = "HEALTHY"
    return {
        "spec": "O-RAN.WG9.XTRP-SYN.0-R004-v07.00",
        "generated_at": _now().isoformat(),
        "sync_health": health,
        "grandmaster_locked": has_gm,
        "max_time_error_ns": max_te,
        "te_budget_ns": TE_BUDGET_NS,
        "te_budget_used_percent": round((max_te / TE_BUDGET_NS) * 100.0, 1),
        "within_budget": within_budget,
        "clocks_in_holdover": in_holdover,
        "clocks_unlocked": unlocked,
        "total_clocks": len(clocks),
    }


# =============================================================================
# Health
# =============================================================================

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "xhaul", "spec": "O-RAN.WG9.XTRP-MGT.0-R004-v10.00"}


if __name__ == "__main__":
    p = argparse.ArgumentParser(); p.add_argument("--host", default="0.0.0.0"); p.add_argument("--port", type=int, default=SERVICE_PORT)
    a = p.parse_args(); uvicorn.run(app, host=a.host, port=a.port)
