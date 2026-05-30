#!/usr/bin/env python3
"""RAN Slicing Service (NSSMF).

Spec: O-RAN.WG1.TS.Slicing-Architecture-R004-v14.01 (Slicing Architecture),
      O-RAN.WG1.Study-on-O-RAN-Slicing-v02.00 (Study on O-RAN Slicing).

This service plays the role of the RAN Network Slice Subnet Management Function
(NSSMF) within the O-RAN slicing architecture. It manages:

  - S-NSSAI identification (SST + optional SD) per TS 23.003 / 23.501.
  - Network Slice Instance (NSI) lifecycle: create / inspect / terminate.
  - Network Slice Subnet Instance (NSSI) lifecycle (RAN / CN / TN subnets that
    compose an NSI).
  - Per-slice SLA targets (guaranteed/max throughput, latency budget, reliability).
  - Per-slice RRM policy: PRB allocation ratios (dedicated / prioritized / shared)
    consumed by the O-DU scheduler per O-RAN.WG1 slicing RRM.
  - Slice-level KPIs (achieved throughput, latency, reliability, PRB utilization)
    and an SLA conformance report comparing achieved KPIs against targets.

Standardized 5QI / GST-style slice types are modeled via SST (eMBB / URLLC / mMTC
/ V2X). The service registers with the NRF as nf_type "NSSMF".

Port: 8129
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

SERVICE_PORT = 8129
NRF_URL = "http://127.0.0.1:8000"


def _now() -> datetime:
    return datetime.now(timezone.utc)


# =============================================================================
# Enumerations (per 3GPP TS 23.501 / O-RAN.WG1.TS.Slicing-Architecture)
# =============================================================================

class SliceServiceType(IntEnum):
    """Standardized Slice/Service Type (SST) values per 3GPP TS 23.501 Table 5.15.2.2-1."""
    EMBB = 1        # enhanced Mobile Broadband
    URLLC = 2       # ultra-Reliable Low-Latency Communications
    MMTC = 3        # massive Machine-Type Communications (mIoT)
    V2X = 4         # Vehicle-to-Everything
    HMTC = 5        # High-performance Machine-Type Communications


class NsiState(str, Enum):
    """Network Slice Instance lifecycle state (O-RAN.WG1 slicing, TM Forum-aligned)."""
    PREPARING = "PREPARING"
    INSTANTIATING = "INSTANTIATING"
    ACTIVE = "ACTIVE"
    DEGRADED = "DEGRADED"
    DEACTIVATING = "DEACTIVATING"
    TERMINATED = "TERMINATED"


class NssiState(str, Enum):
    """Network Slice Subnet Instance lifecycle state."""
    PREPARING = "PREPARING"
    ACTIVE = "ACTIVE"
    DEGRADED = "DEGRADED"
    TERMINATED = "TERMINATED"


class SubnetDomain(str, Enum):
    """Slice subnet domain managed by the corresponding NSSMF."""
    RAN = "RAN"
    CN = "CN"
    TN = "TN"


class RrmPolicyType(str, Enum):
    """O-RAN RRM resource isolation type per slice (Slicing-Architecture RRM)."""
    DEDICATED = "DEDICATED"        # PRBs reserved exclusively for the slice
    PRIORITIZED = "PRIORITIZED"    # min guaranteed share, may borrow when idle
    SHARED = "SHARED"              # best-effort, no reservation


# =============================================================================
# Data Models (Pydantic)
# =============================================================================

class SNSSAI(BaseModel):
    """Single Network Slice Selection Assistance Information (S-NSSAI).

    SST is the 8-bit Slice/Service Type; SD (Slice Differentiator) is an optional
    24-bit value distinguishing slices of the same SST (per 3GPP TS 23.003 28.4).
    """
    sst: SliceServiceType = Field(..., description="Slice/Service Type (8-bit)")
    sd: Optional[str] = Field(default=None, description="Slice Differentiator, 6 hex digits (24-bit)")

    def key(self) -> str:
        return f"{int(self.sst):03d}-{self.sd or 'FFFFFF'}"


class SliceSLA(BaseModel):
    """Per-slice Service Level Agreement targets (GST-style attributes).

    Throughput in Mbps, latency as a one-way user-plane budget in ms, reliability
    as a percentage (e.g. 99.999 for URLLC). availability mirrors the GST
    'Availability' attribute.
    """
    guaranteed_dl_throughput_mbps: float = Field(50.0, ge=0, description="guaranteed DL rate (Mbps)")
    max_dl_throughput_mbps: float = Field(1000.0, ge=0, description="max DL rate (Mbps)")
    guaranteed_ul_throughput_mbps: float = Field(25.0, ge=0, description="guaranteed UL rate (Mbps)")
    max_ul_throughput_mbps: float = Field(500.0, ge=0, description="max UL rate (Mbps)")
    max_latency_ms: float = Field(20.0, ge=0, description="one-way user-plane latency budget (ms)")
    reliability_percent: float = Field(99.9, ge=0, le=100, description="reliability target (%)")
    availability_percent: float = Field(99.99, ge=0, le=100, description="service availability (%)")
    max_number_of_ues: int = Field(10000, ge=0, description="max simultaneous UEs (GST)")


class RrmPolicy(BaseModel):
    """Per-slice RAN RRM policy controlling PRB allocation at the O-DU scheduler.

    The three ratios mirror the 3GPP RRMPolicyRatio IOC (rRMPolicyDedicatedRatio /
    rRMPolicyMinRatio / rRMPolicyMaxRatio) expressed here as PRB percentages.
    """
    policy_type: RrmPolicyType = Field(default=RrmPolicyType.PRIORITIZED)
    dedicated_prb_ratio: int = Field(10, ge=0, le=100, description="PRBs reserved exclusively (%)")
    min_prb_ratio: int = Field(20, ge=0, le=100, description="minimum guaranteed PRB share (%)")
    max_prb_ratio: int = Field(60, ge=0, le=100, description="maximum PRB share allowed (%)")
    priority_level: int = Field(5, ge=1, le=15, description="scheduler priority (1=highest)")
    updated_at: datetime = Field(default_factory=_now)


class SliceKPI(BaseModel):
    """Instantaneous slice-level KPIs measured at the RAN (O-RAN slicing KPI set)."""
    achieved_dl_throughput_mbps: float = 0.0
    achieved_ul_throughput_mbps: float = 0.0
    measured_latency_ms: float = 0.0
    measured_reliability_percent: float = 0.0
    prb_utilization_percent: float = 0.0
    active_ues: int = 0
    rrc_connection_success_rate: float = 99.0
    measured_at: datetime = Field(default_factory=_now)


class NSSICreate(BaseModel):
    """Request body to create a Network Slice Subnet Instance (NSSI)."""
    name: str = Field(..., description="human-readable NSSI name")
    domain: SubnetDomain = Field(default=SubnetDomain.RAN, description="subnet domain (RAN/CN/TN)")
    snssai: SNSSAI = Field(..., description="S-NSSAI served by this subnet")
    managed_cells: List[str] = Field(default_factory=list, description="cell IDs in this RAN subnet")
    description: str = Field(default="")


class NSSI(BaseModel):
    """Network Slice Subnet Instance (NSSI) - a per-domain slice subnet of an NSI."""
    nssi_id: str = Field(default_factory=lambda: f"nssi-{uuid.uuid4().hex[:8]}")
    name: str
    domain: SubnetDomain = Field(default=SubnetDomain.RAN)
    snssai: SNSSAI
    managed_cells: List[str] = Field(default_factory=list)
    state: NssiState = Field(default=NssiState.PREPARING)
    parent_nsi_id: Optional[str] = Field(default=None, description="NSI this NSSI composes")
    description: str = Field(default="")
    created_at: datetime = Field(default_factory=_now)


class NSICreate(BaseModel):
    """Request body to create a Network Slice Instance (NSI)."""
    name: str = Field(..., description="human-readable NSI name")
    snssai: SNSSAI = Field(..., description="S-NSSAI identifying the slice")
    plmn_id: str = Field(default="00101", description="serving PLMN (MCC+MNC)")
    sla: SliceSLA = Field(default_factory=SliceSLA, description="slice SLA targets")
    rrm_policy: RrmPolicy = Field(default_factory=RrmPolicy, description="initial RRM PRB policy")
    nssi_ids: List[str] = Field(default_factory=list, description="composing NSSI identifiers")
    description: str = Field(default="")


class NSI(BaseModel):
    """Network Slice Instance (NSI) managed by the NSSMF."""
    nsi_id: str = Field(default_factory=lambda: f"nsi-{uuid.uuid4().hex[:8]}")
    name: str
    snssai: SNSSAI
    plmn_id: str = Field(default="00101")
    sla: SliceSLA = Field(default_factory=SliceSLA)
    rrm_policy: RrmPolicy = Field(default_factory=RrmPolicy)
    nssi_ids: List[str] = Field(default_factory=list)
    state: NsiState = Field(default=NsiState.PREPARING)
    description: str = Field(default="")
    created_at: datetime = Field(default_factory=_now)
    activated_at: Optional[datetime] = Field(default=None)


# =============================================================================
# In-memory slicing state
# =============================================================================

nsi_store: Dict[str, NSI] = {}
nssi_store: Dict[str, NSSI] = {}


def _measure_kpi(nsi: NSI) -> SliceKPI:
    """Synthesize a plausible KPI sample shaped by the slice SST and RRM policy.

    URLLC slices report low latency / very high reliability; eMBB slices report
    high throughput; mMTC slices report many UEs at modest rates. The achieved
    throughput tracks the dedicated/min PRB ratio so RRM changes are observable.
    """
    sla = nsi.sla
    prb = nsi.rrm_policy
    share = max(prb.min_prb_ratio, prb.dedicated_prb_ratio) / 100.0
    sst = nsi.snssai.sst

    if sst == SliceServiceType.URLLC:
        latency = round(min(sla.max_latency_ms, 1.0 + random.uniform(0, 1.5)), 2)
        reliability = round(min(99.9999, sla.reliability_percent + random.uniform(0, 0.05)), 4)
        ues = random.randint(5, 60)
    elif sst == SliceServiceType.MMTC:
        latency = round(random.uniform(20, 80), 2)
        reliability = round(min(99.99, sla.reliability_percent - random.uniform(0, 0.2)), 4)
        ues = random.randint(2000, 9000)
    elif sst == SliceServiceType.V2X:
        latency = round(min(sla.max_latency_ms, 3.0 + random.uniform(0, 3)), 2)
        reliability = round(min(99.999, sla.reliability_percent + random.uniform(0, 0.02)), 4)
        ues = random.randint(50, 400)
    else:  # EMBB / HMTC
        latency = round(random.uniform(8, sla.max_latency_ms), 2)
        reliability = round(min(99.99, sla.reliability_percent + random.uniform(-0.1, 0.05)), 4)
        ues = random.randint(100, 1500)

    dl = round(min(sla.max_dl_throughput_mbps,
                   sla.guaranteed_dl_throughput_mbps + share * sla.max_dl_throughput_mbps), 1)
    ul = round(min(sla.max_ul_throughput_mbps,
                   sla.guaranteed_ul_throughput_mbps + share * sla.max_ul_throughput_mbps), 1)
    util = round(min(100.0, 30.0 + share * 70.0 + random.uniform(-5, 5)), 1)
    return SliceKPI(
        achieved_dl_throughput_mbps=dl,
        achieved_ul_throughput_mbps=ul,
        measured_latency_ms=latency,
        measured_reliability_percent=reliability,
        prb_utilization_percent=util,
        active_ues=ues,
        rrc_connection_success_rate=round(random.uniform(98.5, 99.99), 3),
    )


def _sla_conformance(nsi: NSI, kpi: SliceKPI) -> Dict[str, Any]:
    """Compare measured KPIs against SLA targets and classify conformance."""
    sla = nsi.sla
    dl_ok = kpi.achieved_dl_throughput_mbps >= sla.guaranteed_dl_throughput_mbps
    ul_ok = kpi.achieved_ul_throughput_mbps >= sla.guaranteed_ul_throughput_mbps
    lat_ok = kpi.measured_latency_ms <= sla.max_latency_ms
    rel_ok = kpi.measured_reliability_percent >= sla.reliability_percent
    breaches = []
    if not dl_ok:
        breaches.append("guaranteed_dl_throughput")
    if not ul_ok:
        breaches.append("guaranteed_ul_throughput")
    if not lat_ok:
        breaches.append("max_latency")
    if not rel_ok:
        breaches.append("reliability")
    return {
        "nsi_id": nsi.nsi_id,
        "snssai": nsi.snssai.key(),
        "conformant": len(breaches) == 0,
        "breaches": breaches,
        "checks": {
            "dl_throughput": {"target": sla.guaranteed_dl_throughput_mbps,
                              "achieved": kpi.achieved_dl_throughput_mbps, "ok": dl_ok},
            "ul_throughput": {"target": sla.guaranteed_ul_throughput_mbps,
                              "achieved": kpi.achieved_ul_throughput_mbps, "ok": ul_ok},
            "latency_ms": {"target": sla.max_latency_ms,
                           "achieved": kpi.measured_latency_ms, "ok": lat_ok},
            "reliability_percent": {"target": sla.reliability_percent,
                                    "achieved": kpi.measured_reliability_percent, "ok": rel_ok},
        },
    }


def _seed_slices() -> None:
    """Seed two representative slices: an eMBB and a URLLC NSI with RAN NSSIs."""
    # eMBB slice (SST=1, no SD).
    embb_nssi = NSSI(
        nssi_id="nssi-embb-ran",
        name="eMBB RAN Subnet",
        domain=SubnetDomain.RAN,
        snssai=SNSSAI(sst=SliceServiceType.EMBB),
        managed_cells=["cell-001", "cell-002", "cell-003"],
        state=NssiState.ACTIVE,
        description="RAN slice subnet for enhanced mobile broadband",
    )
    embb_nsi = NSI(
        nsi_id="nsi-embb-001",
        name="eMBB Consumer Broadband",
        snssai=SNSSAI(sst=SliceServiceType.EMBB),
        plmn_id="00101",
        sla=SliceSLA(guaranteed_dl_throughput_mbps=100.0, max_dl_throughput_mbps=2000.0,
                     guaranteed_ul_throughput_mbps=50.0, max_ul_throughput_mbps=800.0,
                     max_latency_ms=20.0, reliability_percent=99.9, availability_percent=99.95,
                     max_number_of_ues=20000),
        rrm_policy=RrmPolicy(policy_type=RrmPolicyType.PRIORITIZED, dedicated_prb_ratio=10,
                             min_prb_ratio=30, max_prb_ratio=70, priority_level=6),
        nssi_ids=["nssi-embb-ran"],
        state=NsiState.ACTIVE,
        description="Default eMBB slice",
    )
    embb_nssi.parent_nsi_id = embb_nsi.nsi_id
    embb_nsi.activated_at = _now()

    # URLLC slice (SST=2, SD=000001).
    urllc_nssi = NSSI(
        nssi_id="nssi-urllc-ran",
        name="URLLC RAN Subnet",
        domain=SubnetDomain.RAN,
        snssai=SNSSAI(sst=SliceServiceType.URLLC, sd="000001"),
        managed_cells=["cell-001", "cell-004"],
        state=NssiState.ACTIVE,
        description="RAN slice subnet for ultra-reliable low-latency",
    )
    urllc_nsi = NSI(
        nsi_id="nsi-urllc-001",
        name="URLLC Industrial Automation",
        snssai=SNSSAI(sst=SliceServiceType.URLLC, sd="000001"),
        plmn_id="00101",
        sla=SliceSLA(guaranteed_dl_throughput_mbps=20.0, max_dl_throughput_mbps=200.0,
                     guaranteed_ul_throughput_mbps=20.0, max_ul_throughput_mbps=200.0,
                     max_latency_ms=5.0, reliability_percent=99.999, availability_percent=99.999,
                     max_number_of_ues=500),
        rrm_policy=RrmPolicy(policy_type=RrmPolicyType.DEDICATED, dedicated_prb_ratio=25,
                             min_prb_ratio=25, max_prb_ratio=40, priority_level=1),
        nssi_ids=["nssi-urllc-ran"],
        state=NsiState.ACTIVE,
        description="Default URLLC slice",
    )
    urllc_nssi.parent_nsi_id = urllc_nsi.nsi_id
    urllc_nsi.activated_at = _now()

    nssi_store[embb_nssi.nssi_id] = embb_nssi
    nssi_store[urllc_nssi.nssi_id] = urllc_nssi
    nsi_store[embb_nsi.nsi_id] = embb_nsi
    nsi_store[urllc_nsi.nsi_id] = urllc_nsi


# =============================================================================
# FastAPI application
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    _seed_slices()
    try:
        requests.post(f"{NRF_URL}/register", json={"nf_type": "NSSMF", "ip": "127.0.0.1", "port": SERVICE_PORT}, timeout=3)
    except requests.RequestException:
        pass
    logger.info("RAN slicing (NSSMF) service ready on port %s", SERVICE_PORT)
    yield


app = FastAPI(
    title="RAN Slicing Service (NSSMF)",
    description="O-RAN WG1 RAN slicing: S-NSSAI / NSI / NSSI lifecycle, SLA, per-slice RRM PRB policy, slice KPIs",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# =============================================================================
# NSI : Network Slice Instance lifecycle
# =============================================================================

@app.get("/slicing/nsi", response_model=List[NSI])
async def list_nsi(state: Optional[NsiState] = None, sst: Optional[int] = None):
    """List Network Slice Instances, optionally filtered by state or SST."""
    result = list(nsi_store.values())
    if state is not None:
        result = [n for n in result if n.state == state]
    if sst is not None:
        result = [n for n in result if int(n.snssai.sst) == sst]
    return result


@app.post("/slicing/nsi", response_model=NSI, status_code=201)
async def create_nsi(req: NSICreate):
    """Create (instantiate) a Network Slice Instance with its S-NSSAI and SLA."""
    with _tracer.start_as_current_span("slicing_create_nsi") as span:
        span.set_attribute("nsi.name", req.name)
        span.set_attribute("nsi.sst", int(req.snssai.sst))
        # Validate any referenced NSSIs exist.
        for nssi_id in req.nssi_ids:
            if nssi_id not in nssi_store:
                raise HTTPException(status_code=400, detail=f"Unknown NSSI: {nssi_id}")
        nsi = NSI(
            name=req.name,
            snssai=req.snssai,
            plmn_id=req.plmn_id,
            sla=req.sla,
            rrm_policy=req.rrm_policy,
            nssi_ids=req.nssi_ids,
            state=NsiState.ACTIVE,
            description=req.description,
            activated_at=_now(),
        )
        nsi_store[nsi.nsi_id] = nsi
        # Bind composing NSSIs to this NSI.
        for nssi_id in req.nssi_ids:
            nssi_store[nssi_id].parent_nsi_id = nsi.nsi_id
        logger.info("Created NSI %s (S-NSSAI %s)", nsi.nsi_id, nsi.snssai.key())
        return nsi


@app.get("/slicing/nsi/{nsi_id}", response_model=NSI)
async def get_nsi(nsi_id: str):
    """Retrieve a single Network Slice Instance."""
    if nsi_id not in nsi_store:
        raise HTTPException(status_code=404, detail="NSI not found")
    return nsi_store[nsi_id]


@app.delete("/slicing/nsi/{nsi_id}")
async def delete_nsi(nsi_id: str):
    """Terminate (decommission) a Network Slice Instance."""
    if nsi_id not in nsi_store:
        raise HTTPException(status_code=404, detail="NSI not found")
    nsi = nsi_store[nsi_id]
    nsi.state = NsiState.TERMINATED
    # Detach composing NSSIs.
    for nssi_id in nsi.nssi_ids:
        if nssi_id in nssi_store:
            nssi_store[nssi_id].parent_nsi_id = None
    del nsi_store[nsi_id]
    logger.info("Terminated NSI %s", nsi_id)
    return {"status": "terminated", "nsi_id": nsi_id}


# =============================================================================
# NSSI : Network Slice Subnet Instance lifecycle
# =============================================================================

@app.get("/slicing/nssi", response_model=List[NSSI])
async def list_nssi(domain: Optional[SubnetDomain] = None, nsi_id: Optional[str] = None):
    """List Network Slice Subnet Instances, optionally filtered by domain or parent NSI."""
    result = list(nssi_store.values())
    if domain is not None:
        result = [s for s in result if s.domain == domain]
    if nsi_id is not None:
        result = [s for s in result if s.parent_nsi_id == nsi_id]
    return result


@app.post("/slicing/nssi", response_model=NSSI, status_code=201)
async def create_nssi(req: NSSICreate):
    """Create a Network Slice Subnet Instance (RAN / CN / TN subnet)."""
    nssi = NSSI(
        name=req.name,
        domain=req.domain,
        snssai=req.snssai,
        managed_cells=req.managed_cells,
        state=NssiState.ACTIVE,
        description=req.description,
    )
    nssi_store[nssi.nssi_id] = nssi
    logger.info("Created NSSI %s (domain %s)", nssi.nssi_id, nssi.domain.value)
    return nssi


# =============================================================================
# Per-slice RRM policy (PRB allocation)
# =============================================================================

@app.put("/slicing/nsi/{nsi_id}/rrm-policy", response_model=NSI)
async def set_rrm_policy(nsi_id: str, policy: RrmPolicy):
    """Set the per-slice RRM PRB-allocation policy enforced at the O-DU scheduler."""
    if nsi_id not in nsi_store:
        raise HTTPException(status_code=404, detail="NSI not found")
    # Sanity: dedicated <= min <= max keeps the RRMPolicyRatio consistent.
    if not (policy.dedicated_prb_ratio <= policy.min_prb_ratio <= policy.max_prb_ratio):
        raise HTTPException(
            status_code=400,
            detail="Require dedicated_prb_ratio <= min_prb_ratio <= max_prb_ratio",
        )
    policy.updated_at = _now()
    nsi = nsi_store[nsi_id]
    nsi.rrm_policy = policy
    logger.info("Updated RRM policy for NSI %s (%s, ded=%d min=%d max=%d)",
                nsi_id, policy.policy_type.value, policy.dedicated_prb_ratio,
                policy.min_prb_ratio, policy.max_prb_ratio)
    return nsi


# =============================================================================
# Slice KPIs and SLA report
# =============================================================================

@app.get("/slicing/nsi/{nsi_id}/kpi")
async def get_nsi_kpi(nsi_id: str):
    """Return current slice-level KPIs for a Network Slice Instance."""
    if nsi_id not in nsi_store:
        raise HTTPException(status_code=404, detail="NSI not found")
    nsi = nsi_store[nsi_id]
    kpi = _measure_kpi(nsi)
    return {
        "spec": "O-RAN.WG1.TS.Slicing-Architecture-R004-v14.01",
        "nsi_id": nsi.nsi_id,
        "snssai": nsi.snssai.key(),
        "state": nsi.state.value,
        "kpi": kpi.model_dump(),
    }


@app.get("/slicing/sla-report")
async def sla_report():
    """SLA conformance report across all active slices (achieved KPI vs SLA target)."""
    reports = []
    conformant = 0
    for nsi in nsi_store.values():
        if nsi.state in (NsiState.TERMINATED, NsiState.DEACTIVATING):
            continue
        kpi = _measure_kpi(nsi)
        rep = _sla_conformance(nsi, kpi)
        rep["kpi"] = kpi.model_dump()
        reports.append(rep)
        if rep["conformant"]:
            conformant += 1
    return {
        "spec": "O-RAN.WG1.TS.Slicing-Architecture-R004-v14.01",
        "generated_at": _now().isoformat(),
        "total_slices": len(reports),
        "conformant_slices": conformant,
        "breaching_slices": len(reports) - conformant,
        "reports": reports,
    }


# =============================================================================
# Health
# =============================================================================

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "slicing", "spec": "O-RAN.WG1.TS.Slicing-Architecture-R004-v14.01"}


if __name__ == "__main__":
    p = argparse.ArgumentParser(); p.add_argument("--host", default="0.0.0.0"); p.add_argument("--port", type=int, default=SERVICE_PORT)
    a = p.parse_args(); uvicorn.run(app, host=a.host, port=a.port)
