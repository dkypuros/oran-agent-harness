#!/usr/bin/env python3
"""O1 Interface termination (O-RAN WG10 OAM).

Spec: O-RAN.WG10.TS.O1-Interface.0-R005-v18.00 (O1 interface),
      O-RAN.WG10.TS.O1NRM.0-R004-v04.00 (O1 Network Resource Model),
      O-RAN.WG10.TS.OAM-Architecture-R005-v17.00 (OAM architecture).

The O1 interface terminates FCAPS management for O-RAN managed elements. This
service models a NETCONF/YANG-style Network Resource Model (NRM) tree:

  ManagedElement
    -> GNBDUFunction   -> NRCellDU
    -> GNBCUCPFunction -> NRCellCU
    -> GNBCUUPFunction

and exposes FCAPS:
  - C (Configuration): GET/PUT NRM, edit-config, managed-element listing
  - F (Fault): alarm list + raise (mapped onto VES fault events)
  - P (Performance): PM jobs via PmJobManager, PM data read-back
  - (Accounting/Security are stubbed via health + spec metadata)

Heartbeats are emitted as VES heartbeat events via VesEventBuilder /
VesCollectorClient (best-effort; no-op if no collector is present).

Port: 8125
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
    # PM job backend + VES event emission for the O1 P and F services.
    from .pm import PmJobManager, PmMeasurementJob, GranularityPeriod, ReportingMethod
    from .ves import VesEventBuilder, VesCollectorClient, FaultSeverity
except Exception:  # pragma: no cover - allow running as a loose script
    from pm import PmJobManager, PmMeasurementJob, GranularityPeriod, ReportingMethod  # type: ignore
    from ves import VesEventBuilder, VesCollectorClient, FaultSeverity  # type: ignore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("o1")

SERVICE_PORT = 8125
NRF_URL = "http://127.0.0.1:8000"


def _now() -> datetime:
    return datetime.now(timezone.utc)


# =============================================================================
# Enumerations (per O-RAN.WG10.TS.O1NRM / OAM-Architecture)
# =============================================================================

class AdministrativeState(str, Enum):
    """3GPP TS 28.625 administrativeState attribute (CM)."""
    LOCKED = "LOCKED"
    UNLOCKED = "UNLOCKED"
    SHUTTING_DOWN = "SHUTTING_DOWN"


class OperationalState(str, Enum):
    """3GPP operationalState attribute (CM)."""
    ENABLED = "ENABLED"
    DISABLED = "DISABLED"


class AlarmSeverity(IntEnum):
    """Alarm perceived severity per ITU-T X.733 (ordered for FM filtering)."""
    CRITICAL = 1
    MAJOR = 2
    MINOR = 3
    WARNING = 4
    CLEARED = 5


class AlarmState(str, Enum):
    """Alarm lifecycle state (FM)."""
    ACTIVE = "ACTIVE"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    CLEARED = "CLEARED"


# =============================================================================
# NRM data models (O-RAN.WG10.TS.O1NRM Network Resource Model)
# =============================================================================

class NrCellDU(BaseModel):
    """NRCellDU managed object (DU-side NR cell)."""
    nrCellDuId: str
    cellLocalId: int = Field(..., ge=0)
    nrPci: int = Field(default=0, description="Physical cell ID")
    nrTac: int = Field(default=1, description="Tracking area code")
    arfcnDl: int = Field(default=632628, description="DL NR-ARFCN")
    arfcnUl: int = Field(default=632628, description="UL NR-ARFCN")
    bSChannelBwDl: int = Field(default=100, description="DL channel bandwidth (MHz)")
    administrativeState: AdministrativeState = Field(default=AdministrativeState.UNLOCKED)
    operationalState: OperationalState = Field(default=OperationalState.ENABLED)


class NrCellCU(BaseModel):
    """NRCellCU managed object (CU-side NR cell)."""
    nrCellCuId: str
    cellLocalId: int = Field(..., ge=0)
    plmnId: str = Field(default="00101", description="PLMN identifier (MCC+MNC)")
    administrativeState: AdministrativeState = Field(default=AdministrativeState.UNLOCKED)
    operationalState: OperationalState = Field(default=OperationalState.ENABLED)


class GNBDUFunction(BaseModel):
    """GNBDUFunction managed object."""
    gnbDuId: int = Field(..., description="gNB-DU ID")
    gnbId: int = Field(..., description="gNB ID")
    gnbIdLength: int = Field(default=32)
    duName: str = Field(default="")
    administrativeState: AdministrativeState = Field(default=AdministrativeState.UNLOCKED)
    operationalState: OperationalState = Field(default=OperationalState.ENABLED)
    nrCellDus: List[NrCellDU] = Field(default_factory=list)


class GNBCUCPFunction(BaseModel):
    """GNBCUCPFunction managed object (CU control plane)."""
    gnbCuCpId: int = Field(..., description="gNB-CU-CP ID")
    gnbId: int = Field(..., description="gNB ID")
    cuCpName: str = Field(default="")
    administrativeState: AdministrativeState = Field(default=AdministrativeState.UNLOCKED)
    operationalState: OperationalState = Field(default=OperationalState.ENABLED)
    nrCellCus: List[NrCellCU] = Field(default_factory=list)


class GNBCUUPFunction(BaseModel):
    """GNBCUUPFunction managed object (CU user plane)."""
    gnbCuUpId: int = Field(..., description="gNB-CU-UP ID")
    gnbId: int = Field(..., description="gNB ID")
    cuUpName: str = Field(default="")
    administrativeState: AdministrativeState = Field(default=AdministrativeState.UNLOCKED)
    operationalState: OperationalState = Field(default=OperationalState.ENABLED)


class ManagedElement(BaseModel):
    """
    ManagedElement: root managed object of the O1 NRM tree per
    O-RAN.WG10.TS.O1NRM. Contains the gNB DU/CU functions and identifies the
    network function by distinguished name.
    """
    managedElementId: str
    dnPrefix: str = Field(default="DC=oran-emulator")
    userLabel: str = Field(default="")
    vendorName: str = Field(default="ORAN-Emulator")
    swVersion: str = Field(default="1.0.0")
    administrativeState: AdministrativeState = Field(default=AdministrativeState.UNLOCKED)
    operationalState: OperationalState = Field(default=OperationalState.ENABLED)
    gnbDuFunctions: List[GNBDUFunction] = Field(default_factory=list)
    gnbCuCpFunctions: List[GNBCUCPFunction] = Field(default_factory=list)
    gnbCuUpFunctions: List[GNBCUUPFunction] = Field(default_factory=list)

    def dn(self) -> str:
        """Distinguished name of this managed element."""
        return f"{self.dnPrefix},ManagedElement={self.managedElementId}"


# =============================================================================
# Fault management models
# =============================================================================

class Alarm(BaseModel):
    """An FM alarm record per O-RAN.WG10 fault management / 3GPP TS 28.532."""
    alarmId: str = Field(default_factory=lambda: f"alarm-{uuid.uuid4().hex[:12]}")
    objectInstance: str = Field(..., description="DN of the faulted managed object")
    alarmType: str = Field(default="EquipmentAlarm")
    probableCause: str = Field(..., description="X.733 probable cause")
    specificProblem: str = Field(default="")
    perceivedSeverity: AlarmSeverity = Field(default=AlarmSeverity.MINOR)
    state: AlarmState = Field(default=AlarmState.ACTIVE)
    additionalText: str = Field(default="")
    raisedTime: datetime = Field(default_factory=_now)


class ConfigEdit(BaseModel):
    """An edit-config request body (NETCONF-style attribute merge)."""
    targetDn: Optional[str] = Field(
        default=None, description="DN of the object to edit (default: the ME root)"
    )
    attributes: Dict[str, Any] = Field(
        default_factory=dict, description="Attribute name -> new value to merge"
    )


# =============================================================================
# In-memory O1 state
# =============================================================================

managed_elements: Dict[str, ManagedElement] = {}
alarms: Dict[str, Alarm] = {}

pm_manager = PmJobManager()
ves_builder = VesEventBuilder(source_name="oran-emulator-o1")
ves_client = VesCollectorClient()


def _seed_nrm() -> None:
    """Seed a representative ManagedElement -> DU/CU -> cell NRM tree."""
    cell_du = NrCellDU(nrCellDuId="NRCellDU=cell-1", cellLocalId=1, nrPci=1, nrTac=7)
    du = GNBDUFunction(gnbDuId=1, gnbId=1001, duName="gnb-du-1", nrCellDus=[cell_du])
    cell_cu = NrCellCU(nrCellCuId="NRCellCU=cell-1", cellLocalId=1, plmnId="00101")
    cucp = GNBCUCPFunction(gnbCuCpId=1, gnbId=1001, cuCpName="gnb-cucp-1", nrCellCus=[cell_cu])
    cuup = GNBCUUPFunction(gnbCuUpId=1, gnbId=1001, cuUpName="gnb-cuup-1")
    me = ManagedElement(
        managedElementId="gnb-001",
        userLabel="O-RAN gNB 001",
        gnbDuFunctions=[du],
        gnbCuCpFunctions=[cucp],
        gnbCuUpFunctions=[cuup],
    )
    managed_elements[me.managedElementId] = me

    alarm = Alarm(
        objectInstance=f"{me.dn()},GNBDUFunction=1,NRCellDU=cell-1",
        alarmType="CommunicationsAlarm",
        probableCause="LossOfSignal",
        specificProblem="Fronthaul link degraded",
        perceivedSeverity=AlarmSeverity.MAJOR,
        additionalText="Seeded demonstration alarm",
    )
    alarms[alarm.alarmId] = alarm


def _find_object(me: ManagedElement, target_dn: str) -> Optional[BaseModel]:
    """
    Resolve a (sub)object within a managed element by DN.

    Leaf cells carry DN-style string IDs (e.g. ``NRCellDU=cell-1``) and are
    matched by exact token containment. Function objects carry numeric IDs and
    are matched only via their RDN form (e.g. ``GNBDUFunction=1``) so a stray
    digit in the DN never resolves to the wrong function. Cells are checked
    before their parent functions (most specific first).
    """
    # Leaf cells first (string DN-style IDs).
    for du in me.gnbDuFunctions:
        for cell in du.nrCellDus:
            if cell.nrCellDuId and cell.nrCellDuId in target_dn:
                return cell
    for cucp in me.gnbCuCpFunctions:
        for cell in cucp.nrCellCus:
            if cell.nrCellCuId and cell.nrCellCuId in target_dn:
                return cell
    # Function objects via explicit RDN (class=numericId).
    for du in me.gnbDuFunctions:
        if f"GNBDUFunction={du.gnbDuId}" in target_dn:
            return du
    for cucp in me.gnbCuCpFunctions:
        if f"GNBCUCPFunction={cucp.gnbCuCpId}" in target_dn:
            return cucp
    for cuup in me.gnbCuUpFunctions:
        if f"GNBCUUPFunction={cuup.gnbCuUpId}" in target_dn:
            return cuup
    # Fall back to the managed-element root.
    if target_dn.endswith(me.managedElementId) or target_dn == me.dn():
        return me
    return None


# =============================================================================
# FastAPI application
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    _seed_nrm()
    try:
        requests.post(f"{NRF_URL}/register", json={"nf_type": "O1", "ip": "127.0.0.1", "port": SERVICE_PORT}, timeout=3)
    except requests.RequestException:
        pass
    logger.info("O1 interface termination ready on port %s", SERVICE_PORT)
    yield


app = FastAPI(
    title="O1 Interface (O-RAN WG10)",
    description="O-RAN O1 interface termination: NRM (NETCONF/YANG-style) + FCAPS",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# =============================================================================
# CM / NRM : Configuration Management (NETCONF/YANG-style NRM tree)
# =============================================================================

@app.get("/o1/nrm")
async def get_nrm():
    """Return the full NRM tree (all managed elements)."""
    with _tracer.start_as_current_span("o1_get_nrm") as span:
        span.set_attribute("nrm.managedElements", len(managed_elements))
        return {
            "spec": "O-RAN.WG10.TS.O1NRM.0-R004-v04.00",
            "managedElements": [me.model_dump(mode="json") for me in managed_elements.values()],
        }


@app.get("/o1/nrm/{me_id}")
async def get_managed_element(me_id: str):
    """Return one managed element subtree by ID."""
    me = managed_elements.get(me_id)
    if me is None:
        raise HTTPException(status_code=404, detail="ManagedElement not found")
    return me.model_dump(mode="json")


@app.put("/o1/nrm/{me_id}/config")
async def edit_config(me_id: str, edit: ConfigEdit):
    """
    NETCONF-style edit-config: merge attribute values into a managed object
    within the named managed element.
    """
    me = managed_elements.get(me_id)
    if me is None:
        raise HTTPException(status_code=404, detail="ManagedElement not found")
    target_dn = edit.targetDn or me.dn()
    obj = _find_object(me, target_dn)
    if obj is None:
        raise HTTPException(status_code=404, detail="Target object not found in NRM")
    applied: Dict[str, Any] = {}
    for key, value in edit.attributes.items():
        if key not in obj.model_fields:
            raise HTTPException(status_code=400, detail=f"Unknown attribute: {key}")
        try:
            # Re-validate the whole object with the merged attribute so values are
            # coerced to their declared field types (e.g. enums stay enums).
            validated = obj.model_validate({**obj.model_dump(), key: value})
            setattr(obj, key, getattr(validated, key))
            coerced = getattr(obj, key)
            applied[key] = coerced.value if isinstance(coerced, Enum) else coerced
        except HTTPException:
            raise
        except Exception as exc:  # validation failure on the edited attribute
            raise HTTPException(status_code=400, detail=f"Invalid value for {key}: {exc}")
    logger.info("edit-config on %s applied %s", target_dn, list(applied.keys()))
    return {
        "status": "applied",
        "managedElementId": me_id,
        "targetDn": target_dn,
        "applied": applied,
    }


@app.get("/o1/cm/managed-elements")
async def list_managed_elements():
    """List managed-element identifiers and their high-level CM state."""
    return [
        {
            "managedElementId": me.managedElementId,
            "dn": me.dn(),
            "administrativeState": me.administrativeState.value,
            "operationalState": me.operationalState.value,
            "duFunctions": len(me.gnbDuFunctions),
            "cuCpFunctions": len(me.gnbCuCpFunctions),
            "cuUpFunctions": len(me.gnbCuUpFunctions),
        }
        for me in managed_elements.values()
    ]


# =============================================================================
# FM : Fault Management
# =============================================================================

@app.get("/o1/fm/alarms")
async def list_alarms(severity: Optional[str] = None, state: Optional[str] = None):
    """List FM alarms, optionally filtered by severity name or state."""
    result = list(alarms.values())
    if severity is not None:
        try:
            sev = AlarmSeverity[severity.upper()]
        except KeyError:
            raise HTTPException(status_code=400, detail=f"Invalid severity: {severity}")
        result = [a for a in result if a.perceivedSeverity == sev]
    if state is not None:
        try:
            st = AlarmState(state.upper())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid state: {state}")
        result = [a for a in result if a.state == st]
    return [a.model_dump(mode="json") for a in result]


@app.post("/o1/fm/alarms", status_code=201)
async def raise_alarm(alarm: Alarm):
    """
    Raise an FM alarm and emit a corresponding VES fault event (best-effort).
    """
    with _tracer.start_as_current_span("o1_raise_alarm") as span:
        span.set_attribute("alarm.probableCause", alarm.probableCause)
        alarms[alarm.alarmId] = alarm
        # Map X.733 severity to VES fault severity.
        ves_sev_map = {
            AlarmSeverity.CRITICAL: FaultSeverity.CRITICAL,
            AlarmSeverity.MAJOR: FaultSeverity.MAJOR,
            AlarmSeverity.MINOR: FaultSeverity.MINOR,
            AlarmSeverity.WARNING: FaultSeverity.WARNING,
            AlarmSeverity.CLEARED: FaultSeverity.NORMAL,
        }
        envelope = (
            ves_builder.fault(
                alarm_condition=alarm.probableCause,
                specific_problem=alarm.specificProblem or alarm.probableCause,
                severity=ves_sev_map.get(alarm.perceivedSeverity, FaultSeverity.MINOR),
                additional={"objectInstance": alarm.objectInstance, "alarmId": alarm.alarmId},
            ).build()
        )
        delivery = ves_client.send(envelope)
        logger.info("Raised alarm %s (%s); VES delivered=%s",
                    alarm.alarmId, alarm.probableCause, delivery.get("delivered"))
        return {"alarm": alarm.model_dump(mode="json"), "vesDelivery": delivery}


# =============================================================================
# PM : Performance Management (backed by PmJobManager)
# =============================================================================

@app.get("/o1/pm/jobs")
async def list_pm_jobs():
    """List PM measurement jobs."""
    return {
        "summary": pm_manager.summary(),
        "jobs": [j.model_dump(mode="json") for j in pm_manager.list_jobs()],
    }


@app.post("/o1/pm/jobs", status_code=201)
async def create_pm_job(job: PmMeasurementJob):
    """Create a PM measurement job via the PmJobManager."""
    created = pm_manager.create_job(job)
    # Prime one granularity period so data is immediately available.
    pm_manager.produce(created.jobId, periods=1)
    logger.info("Created PM job %s (%s)", created.jobId, created.reportingMethod.value)
    return created.model_dump(mode="json")


@app.get("/o1/pm/data/{job_id}")
async def get_pm_data(job_id: str, limit: int = 5):
    """Return simulated PM data (reports + file paths) for a PM job."""
    if pm_manager.get_job(job_id) is None:
        raise HTTPException(status_code=404, detail="PM job not found")
    return pm_manager.get_data(job_id, limit=limit)


# =============================================================================
# Heartbeat (VES heartbeat domain)
# =============================================================================

@app.post("/o1/heartbeat")
async def emit_heartbeat(interval: int = 60):
    """Emit a VES heartbeat event (best-effort delivery to a VES collector)."""
    envelope = ves_builder.heartbeat(
        interval=interval, additional={"nfType": "O1", "managedElements": len(managed_elements)}
    ).build()
    delivery = ves_client.send(envelope)
    return {"event": envelope["event"], "vesDelivery": delivery, "vesStats": ves_client.stats()}


# =============================================================================
# Health
# =============================================================================

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "o1", "spec": "O-RAN.WG10.TS.O1-Interface.0-R005-v18.00"}


if __name__ == "__main__":
    p = argparse.ArgumentParser(); p.add_argument("--host", default="0.0.0.0"); p.add_argument("--port", type=int, default=SERVICE_PORT)
    a = p.parse_args(); uvicorn.run(app, host=a.host, port=a.port)
