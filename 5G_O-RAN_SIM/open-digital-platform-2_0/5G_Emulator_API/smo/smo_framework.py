#!/usr/bin/env python3
"""SMO Framework Coordinator.

Spec: O-RAN.WG1.TS.OAD-R005-v16.00 (O-RAN Architecture Description),
      O-RAN.WG2.TS.Non-RT-RIC-ARCH-R004-v07.00 (Non-RT RIC architecture).

The SMO (Service Management & Orchestration) framework is the top-level
coordinator of the O-RAN management plane. It maintains a registry of the managed
O-RAN functions and their standardized interfaces (A1, O1, O2, R1) and exposes a
unified inventory/topology plus a framework-service catalog.

Managed functions and interfaces:
  - Non-RT RIC  :8096  (A1 policy / EI toward Near-RT RIC)
  - O1          :8125  (O1 OAM / NETCONF-style management)
  - O2-IMS      :8098  (O-Cloud infrastructure management)
  - O2-DMS      :8099  (O-Cloud deployment management)
  - R1          :8124  (rApp <-> SMO/Non-RT RIC framework)

Port: 8122
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

SERVICE_PORT = 8122
NRF_URL = "http://127.0.0.1:8000"


def _now() -> datetime:
    return datetime.now(timezone.utc)


# =============================================================================
# Enumerations (per O-RAN.WG1.TS.OAD)
# =============================================================================

class FunctionStatus(str, Enum):
    """Managed-function reachability status."""
    UP = "UP"
    DOWN = "DOWN"
    UNKNOWN = "UNKNOWN"


class OranInterface(str, Enum):
    """Standardized O-RAN interfaces per O-RAN.WG1.TS.OAD."""
    A1 = "A1"
    O1 = "O1"
    O2 = "O2"
    R1 = "R1"
    E2 = "E2"


# =============================================================================
# Data Models (Pydantic)
# =============================================================================

class ManagedFunction(BaseModel):
    """
    A managed O-RAN function registered with the SMO framework.

    Per O-RAN.WG1.TS.OAD, the SMO manages O-RAN functions over A1/O1/O2/R1.
    """
    functionId: str = Field(..., description="Stable function identifier")
    name: str = Field(..., description="Human-readable function name")
    interfaces: List[OranInterface] = Field(default_factory=list, description="Exposed interfaces")
    host: str = Field(default="127.0.0.1")
    port: int = Field(..., description="Service port")
    healthPath: str = Field(default="/health", description="Health endpoint path")
    description: str = Field(default="")
    registeredAt: datetime = Field(default_factory=_now)


class FunctionStatusReport(BaseModel):
    """Reachability report for a managed function (inventory entry)."""
    functionId: str
    name: str
    interfaces: List[OranInterface]
    url: str
    status: FunctionStatus
    detail: Optional[Dict[str, Any]] = None
    lastChecked: datetime = Field(default_factory=_now)


class FrameworkService(BaseModel):
    """An R1/A1/O1/O2 framework-service catalog entry."""
    serviceGroup: str = Field(..., description="Interface group: R1, A1, O1, O2")
    name: str = Field(..., description="Service name")
    interface: OranInterface
    spec: str = Field(..., description="Governing O-RAN spec")
    description: str = Field(default="")
    providedBy: str = Field(..., description="functionId providing the service")


# =============================================================================
# Managed-function registry (default O-RAN management plane)
# =============================================================================

managed_functions: Dict[str, ManagedFunction] = {}


def _seed_managed_functions() -> None:
    """Register the default O-RAN management-plane functions."""
    defaults = [
        ManagedFunction(
            functionId="non-rt-ric",
            name="Non-RT RIC",
            interfaces=[OranInterface.A1, OranInterface.O1],
            port=8096,
            description="Non-Real-Time RAN Intelligent Controller (A1 policy / EI)",
        ),
        ManagedFunction(
            functionId="o1",
            name="O1 OAM",
            interfaces=[OranInterface.O1],
            port=8125,
            description="O1 OAM / NETCONF-style management interface",
        ),
        ManagedFunction(
            functionId="o2-ims",
            name="O2-IMS",
            interfaces=[OranInterface.O2],
            port=8098,
            description="O-Cloud Infrastructure Management Service",
        ),
        ManagedFunction(
            functionId="o2-dms",
            name="O2-DMS",
            interfaces=[OranInterface.O2],
            port=8099,
            description="O-Cloud Deployment Management Service",
        ),
        ManagedFunction(
            functionId="r1",
            name="R1 Interface",
            interfaces=[OranInterface.R1],
            port=8124,
            description="R1 interface between rApps and the SMO / Non-RT RIC framework",
        ),
    ]
    for fn in defaults:
        managed_functions[fn.functionId] = fn


def _framework_service_catalog() -> List[FrameworkService]:
    """Static R1/A1/O1/O2 framework-service catalog."""
    return [
        FrameworkService(serviceGroup="R1", name="Service Management & Exposure (SME)",
                         interface=OranInterface.R1, spec="O-RAN.WG2.TS.R1AP-R005-v10.00",
                         description="rApp service registration & discovery", providedBy="r1"),
        FrameworkService(serviceGroup="R1", name="Data Management & Exposure (DME)",
                         interface=OranInterface.R1, spec="O-RAN.WG2.TS.R1AP-R005-v10.00",
                         description="Data types, producers, consumers, data jobs", providedBy="r1"),
        FrameworkService(serviceGroup="R1", name="AI/ML-related R1 services",
                         interface=OranInterface.R1, spec="O-RAN.WG2.AIML-v01.03",
                         description="AI/ML model registry exposure to rApps", providedBy="r1"),
        FrameworkService(serviceGroup="A1", name="A1 Policy Management",
                         interface=OranInterface.A1, spec="O-RAN.WG2.TS.Non-RT-RIC-ARCH-R004-v07.00",
                         description="A1-P policy types & instances toward Near-RT RIC", providedBy="non-rt-ric"),
        FrameworkService(serviceGroup="A1", name="A1 Enrichment Information",
                         interface=OranInterface.A1, spec="O-RAN.WG2.TS.Non-RT-RIC-ARCH-R004-v07.00",
                         description="A1-EI enrichment information jobs", providedBy="non-rt-ric"),
        FrameworkService(serviceGroup="O1", name="O1 OAM Management",
                         interface=OranInterface.O1, spec="O-RAN.WG1.TS.OAD-R005-v16.00",
                         description="Provisioning, fault, performance management", providedBy="o1"),
        FrameworkService(serviceGroup="O2", name="O2-IMS Infrastructure Management",
                         interface=OranInterface.O2, spec="O-RAN.WG1.TS.OAD-R005-v16.00",
                         description="O-Cloud infrastructure inventory", providedBy="o2-ims"),
        FrameworkService(serviceGroup="O2", name="O2-DMS Deployment Management",
                         interface=OranInterface.O2, spec="O-RAN.WG1.TS.OAD-R005-v16.00",
                         description="O-Cloud workload deployment lifecycle", providedBy="o2-dms"),
    ]


def _check_function_health(fn: ManagedFunction) -> FunctionStatusReport:
    """Best-effort health poll of a managed function."""
    url = f"http://{fn.host}:{fn.port}"
    status = FunctionStatus.DOWN
    detail: Optional[Dict[str, Any]] = None
    try:
        resp = requests.get(f"{url}{fn.healthPath}", timeout=2)
        if resp.status_code == 200:
            status = FunctionStatus.UP
            try:
                detail = resp.json()
            except ValueError:
                detail = None
    except requests.RequestException:
        status = FunctionStatus.DOWN
    return FunctionStatusReport(
        functionId=fn.functionId,
        name=fn.name,
        interfaces=fn.interfaces,
        url=url,
        status=status,
        detail=detail,
    )


# =============================================================================
# FastAPI application
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    _seed_managed_functions()
    try:
        requests.post(f"{NRF_URL}/register", json={"nf_type": "SMO_FW", "ip": "127.0.0.1", "port": SERVICE_PORT}, timeout=3)
    except requests.RequestException:
        pass
    logger.info("SMO framework coordinator ready on port %s", SERVICE_PORT)
    yield


app = FastAPI(
    title="SMO Framework Coordinator",
    description="O-RAN SMO coordinator: inventory, topology, and framework-service catalog",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# =============================================================================
# Inventory & Topology
# =============================================================================

@app.get("/smo/inventory", response_model=List[FunctionStatusReport])
async def get_inventory():
    """List managed O-RAN functions with best-effort up/down health."""
    with _tracer.start_as_current_span("smo_inventory"):
        if not managed_functions:
            _seed_managed_functions()
        return [_check_function_health(fn) for fn in managed_functions.values()]


@app.get("/smo/topology")
async def get_topology():
    """Return nodes + edges of the O-RAN management plane."""
    with _tracer.start_as_current_span("smo_topology"):
        if not managed_functions:
            _seed_managed_functions()
        nodes = [{"id": "smo", "name": "SMO Framework", "type": "SMO", "port": SERVICE_PORT}]
        for fn in managed_functions.values():
            nodes.append({
                "id": fn.functionId,
                "name": fn.name,
                "type": "managed-function",
                "port": fn.port,
                "interfaces": [i.value for i in fn.interfaces],
            })
        # SMO manages each function over its primary interface.
        edges = []
        for fn in managed_functions.values():
            iface = fn.interfaces[0].value if fn.interfaces else "MGMT"
            edges.append({"from": "smo", "to": fn.functionId, "interface": iface})
        # The R1 framework fronts the Non-RT RIC for rApps.
        if "r1" in managed_functions and "non-rt-ric" in managed_functions:
            edges.append({"from": "r1", "to": "non-rt-ric", "interface": "A1"})
        return {"nodes": nodes, "edges": edges}


# =============================================================================
# Framework-service catalog
# =============================================================================

@app.get("/smo/framework-services", response_model=List[FrameworkService])
async def get_framework_services(serviceGroup: Optional[str] = None):
    """Return the R1/A1/O1/O2 framework-service catalog."""
    catalog = _framework_service_catalog()
    if serviceGroup is not None:
        catalog = [s for s in catalog if s.serviceGroup.upper() == serviceGroup.upper()]
    return catalog


# =============================================================================
# Self-registration
# =============================================================================

@app.post("/smo/register", response_model=ManagedFunction, status_code=201)
async def register_function(function: ManagedFunction):
    """Allow an O-RAN function to self-register with the SMO framework."""
    managed_functions[function.functionId] = function
    logger.info("Registered managed function: %s (%s)", function.name, function.functionId)
    return function


# =============================================================================
# Health
# =============================================================================

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "smo_framework", "spec": "O-RAN.WG1.TS.OAD-R005-v16.00"}


if __name__ == "__main__":
    p = argparse.ArgumentParser(); p.add_argument("--host", default="0.0.0.0"); p.add_argument("--port", type=int, default=SERVICE_PORT)
    a = p.parse_args(); uvicorn.run(app, host=a.host, port=a.port)
