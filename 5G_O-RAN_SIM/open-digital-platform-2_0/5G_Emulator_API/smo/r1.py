#!/usr/bin/env python3
"""R1 Interface Service.

Spec: O-RAN.WG2.TS.R1AP-R005-v10.00 (R1 Application Protocol),
      O-RAN.WG2.TS.R1GAP-R005-v13.00 (R1 General Aspects & Principles),
      O-RAN.WG2.TS.R1TD-R005-v04.02 (R1 use cases & requirements).

The R1 interface sits between rApps and the SMO / Non-RT RIC framework. This
service implements the R1 service groups:
  - SME : Service Management & Exposure (service registration/discovery)
  - DME : Data Management & Exposure (data types, producers, consumers, jobs)
  - A1-related R1 services (rApps drive A1 policy via the Non-RT RIC at :8096)
  - AI/ML-related R1 services (proxy the AimlModelRegistry from smo/aiml.py)

Port: 8124
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

try:
    # AI/ML-related R1 services proxy the WG2 AI/ML registry.
    from .aiml import AimlModelRegistry
except Exception:  # pragma: no cover - allow running as a loose script
    try:
        from aiml import AimlModelRegistry  # type: ignore
    except Exception:
        AimlModelRegistry = None  # type: ignore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("svc")

SERVICE_PORT = 8124
NRF_URL = "http://127.0.0.1:8000"
NON_RT_RIC_URL = "http://127.0.0.1:8096"


def _now() -> datetime:
    return datetime.now(timezone.utc)


# =============================================================================
# Enumerations (per O-RAN.WG2.TS.R1GAP-R005-v13.00)
# =============================================================================

class R1ServiceGroup(str, Enum):
    """R1 service groups per O-RAN.WG2.TS.R1GAP Section 5."""
    SME = "SME"          # Service Management & Exposure
    DME = "DME"          # Data Management & Exposure
    A1 = "A1_RELATED"    # A1-related services
    AIML = "AIML_RELATED"  # AI/ML-related services


class ServiceStatus(str, Enum):
    """rApp service registration status (SME)."""
    REGISTERED = "REGISTERED"
    DISCOVERABLE = "DISCOVERABLE"
    DEREGISTERED = "DEREGISTERED"


class DataJobStatus(str, Enum):
    """DME data job status per R1AP data delivery."""
    CREATED = "CREATED"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    STOPPED = "STOPPED"


class DmeRole(str, Enum):
    """DME participant role."""
    PRODUCER = "PRODUCER"
    CONSUMER = "CONSUMER"


# =============================================================================
# Data Models (Pydantic)
# =============================================================================

# --- SME : Service Management & Exposure -------------------------------------

class ServiceRegistration(BaseModel):
    """
    rApp service registration per O-RAN.WG2.TS.R1AP Service Management & Exposure.

    An rApp registers the service(s) it produces so other rApps can discover them.
    """
    serviceId: str = Field(default_factory=lambda: str(uuid.uuid4()))
    serviceName: str = Field(..., description="Service name")
    rappId: str = Field(..., description="Owning rApp identifier")
    version: str = Field(default="1.0.0")
    serviceGroup: R1ServiceGroup = Field(default=R1ServiceGroup.SME)
    endpoint: Optional[str] = Field(default=None, description="Service callback endpoint")
    description: str = Field(default="")
    capabilities: List[str] = Field(default_factory=list, description="Advertised capabilities")
    status: ServiceStatus = Field(default=ServiceStatus.REGISTERED)
    registeredAt: datetime = Field(default_factory=_now)


# --- DME : Data Management & Exposure ----------------------------------------

class DataType(BaseModel):
    """
    DME data type registration per O-RAN.WG2.TS.R1AP Data Management & Exposure.

    Declares a schema for data that producers expose and consumers subscribe to.
    """
    dataTypeId: str = Field(..., description="Data type identifier")
    name: str = Field(..., description="Human-readable name")
    description: str = Field(default="")
    schemaRef: Optional[str] = Field(default=None, description="JSON-schema reference")
    dataSchema: Dict[str, Any] = Field(default_factory=dict, description="Inline data schema")
    keywords: List[str] = Field(default_factory=list)
    registeredAt: datetime = Field(default_factory=_now)


class DmeParticipant(BaseModel):
    """A registered DME data producer or consumer."""
    participantId: str = Field(default_factory=lambda: str(uuid.uuid4()))
    role: DmeRole = Field(..., description="PRODUCER or CONSUMER")
    rappId: str = Field(..., description="Owning rApp identifier")
    dataTypeId: str = Field(..., description="Data type this participant handles")
    endpoint: Optional[str] = Field(default=None, description="Delivery / source endpoint")
    description: str = Field(default="")
    registeredAt: datetime = Field(default_factory=_now)


class DataJob(BaseModel):
    """
    DME data job per O-RAN.WG2.TS.R1AP.

    A consumer creates a data job to receive data of a given type from producers.
    """
    dataJobId: str = Field(default_factory=lambda: str(uuid.uuid4()))
    dataTypeId: str = Field(..., description="Data type to deliver")
    consumerId: str = Field(..., description="Consumer participant / rApp ID")
    targetUri: Optional[str] = Field(default=None, description="Delivery endpoint")
    jobDefinition: Dict[str, Any] = Field(default_factory=dict, description="Filter / job parameters")
    status: DataJobStatus = Field(default=DataJobStatus.CREATED)
    createdAt: datetime = Field(default_factory=_now)


# =============================================================================
# In-memory R1 state
# =============================================================================

services: Dict[str, ServiceRegistration] = {}
data_types: Dict[str, DataType] = {}
producers: Dict[str, DmeParticipant] = {}
consumers: Dict[str, DmeParticipant] = {}
data_jobs: Dict[str, DataJob] = {}

aiml_registry = AimlModelRegistry() if AimlModelRegistry is not None else None


def _seed_r1_state() -> None:
    """Seed representative SME services and DME data types."""
    svc = ServiceRegistration(
        serviceId="svc-traffic-steering",
        serviceName="Traffic Steering rApp Service",
        rappId="rapp-ts-001",
        serviceGroup=R1ServiceGroup.A1,
        capabilities=["a1-policy", "traffic-steering"],
        description="Produces A1 traffic-steering policy guidance",
        status=ServiceStatus.DISCOVERABLE,
    )
    services[svc.serviceId] = svc

    pm = DataType(
        dataTypeId="dme.pm.cell-kpi",
        name="Cell PM KPI",
        description="Per-cell performance management counters",
        keywords=["pm", "kpi", "cell"],
        dataSchema={"type": "object", "properties": {"cellId": {"type": "string"},
                                                      "prbUsage": {"type": "number"}}},
    )
    data_types[pm.dataTypeId] = pm


# =============================================================================
# FastAPI application
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    _seed_r1_state()
    try:
        requests.post(f"{NRF_URL}/register", json={"nf_type": "R1", "ip": "127.0.0.1", "port": SERVICE_PORT}, timeout=3)
    except requests.RequestException:
        pass
    logger.info("R1 interface service ready on port %s", SERVICE_PORT)
    yield


app = FastAPI(
    title="R1 Interface Service",
    description="O-RAN R1 interface between rApps and the SMO / Non-RT RIC framework",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# =============================================================================
# SME : Service Management & Exposure
# =============================================================================

@app.post("/r1/sme/services", response_model=ServiceRegistration, status_code=201)
async def register_service(registration: ServiceRegistration):
    """Register an rApp-produced service (SME)."""
    with _tracer.start_as_current_span("r1_sme_register") as span:
        span.set_attribute("service.name", registration.serviceName)
        registration.status = ServiceStatus.REGISTERED
        services[registration.serviceId] = registration
        logger.info("Registered R1 service: %s (%s)", registration.serviceName, registration.serviceId)
        return registration


@app.get("/r1/sme/services", response_model=List[ServiceRegistration])
async def discover_services(serviceGroup: Optional[R1ServiceGroup] = None, capability: Optional[str] = None):
    """Discover registered services (SME), optionally filtered by group/capability."""
    result = list(services.values())
    if serviceGroup is not None:
        result = [s for s in result if s.serviceGroup == serviceGroup]
    if capability is not None:
        result = [s for s in result if capability in s.capabilities]
    return result


@app.delete("/r1/sme/services/{service_id}")
async def deregister_service(service_id: str):
    """Deregister an rApp service (SME)."""
    if service_id not in services:
        raise HTTPException(status_code=404, detail="Service not found")
    del services[service_id]
    return {"status": "deregistered", "serviceId": service_id}


# =============================================================================
# DME : Data Management & Exposure
# =============================================================================

@app.post("/r1/dme/data-types", response_model=DataType, status_code=201)
async def register_data_type(data_type: DataType):
    """Register a DME data type."""
    data_types[data_type.dataTypeId] = data_type
    logger.info("Registered DME data type: %s", data_type.dataTypeId)
    return data_type


@app.get("/r1/dme/data-types", response_model=List[DataType])
async def list_data_types():
    """List DME data types."""
    return list(data_types.values())


@app.post("/r1/dme/producers", response_model=DmeParticipant, status_code=201)
async def register_producer(participant: DmeParticipant):
    """Register a DME data producer."""
    participant.role = DmeRole.PRODUCER
    if participant.dataTypeId not in data_types:
        raise HTTPException(status_code=400, detail="Unknown data type")
    producers[participant.participantId] = participant
    logger.info("Registered DME producer: %s", participant.participantId)
    return participant


@app.post("/r1/dme/consumers", response_model=DmeParticipant, status_code=201)
async def register_consumer(participant: DmeParticipant):
    """Register a DME data consumer."""
    participant.role = DmeRole.CONSUMER
    if participant.dataTypeId not in data_types:
        raise HTTPException(status_code=400, detail="Unknown data type")
    consumers[participant.participantId] = participant
    logger.info("Registered DME consumer: %s", participant.participantId)
    return participant


@app.post("/r1/dme/data-jobs", response_model=DataJob, status_code=201)
async def create_data_job(job: DataJob):
    """Create a DME data job (data delivery subscription)."""
    if job.dataTypeId not in data_types:
        raise HTTPException(status_code=400, detail="Unknown data type")
    job.status = DataJobStatus.ACTIVE
    data_jobs[job.dataJobId] = job
    logger.info("Created DME data job: %s for type %s", job.dataJobId, job.dataTypeId)
    return job


@app.get("/r1/dme/data-jobs", response_model=List[DataJob])
async def list_data_jobs():
    """List DME data jobs."""
    return list(data_jobs.values())


# =============================================================================
# A1-related R1 services (rApps drive A1 via the Non-RT RIC)
# =============================================================================

@app.get("/r1/a1/policy-types")
async def list_a1_policy_types():
    """Proxy A1 policy types from the Non-RT RIC for rApp consumption."""
    try:
        resp = requests.get(f"{NON_RT_RIC_URL}/a1-p/policytypes", timeout=3)
        if resp.status_code == 200:
            return {"source": NON_RT_RIC_URL, "policyTypes": resp.json()}
    except requests.RequestException as e:
        logger.warning("Non-RT RIC unreachable: %s", e)
    return {"source": NON_RT_RIC_URL, "policyTypes": [], "status": "unavailable"}


# =============================================================================
# AI/ML-related R1 services (proxy the AimlModelRegistry)
# =============================================================================

@app.get("/r1/aiml/models")
async def list_aiml_models(state: Optional[str] = None, useCase: Optional[str] = None):
    """Expose the WG2 AI/ML model registry to rApps via R1."""
    if aiml_registry is None:
        return {"spec": "O-RAN.WG2.AIML-v01.03", "models": [], "status": "registry-unavailable"}
    from .aiml import ModelLifecycleState  # local import to keep module import-safe
    state_enum = None
    if state is not None:
        try:
            state_enum = ModelLifecycleState(state)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid model state: {state}")
    models = aiml_registry.list_models(state=state_enum, use_case=useCase)
    return {
        "spec": "O-RAN.WG2.AIML-v01.03",
        "summary": aiml_registry.summary(),
        "models": [m.model_dump() for m in models],
    }


# =============================================================================
# Health
# =============================================================================

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "r1", "spec": "O-RAN.WG2.TS.R1AP-R005-v10.00"}


if __name__ == "__main__":
    p = argparse.ArgumentParser(); p.add_argument("--host", default="0.0.0.0"); p.add_argument("--port", type=int, default=SERVICE_PORT)
    a = p.parse_args(); uvicorn.run(app, host=a.host, port=a.port)
