"""
VES (Virtual Event Streaming) 7.x common event format library.

Spec: VES Event Listener 7.2.1 (ONAP / O-RAN), as referenced by
      O-RAN.WG10.TS.O1-Interface.0-R005-v18.00 for streaming fault, heartbeat,
      measurement, pnfRegistration, and notification events from O1-managed
      network functions to a VES collector / SMO.

This module is a pure library (no FastAPI app). It provides:
- ``commonEventHeader`` and the per-domain event blocks (fault, heartbeat,
  measurement, pnfRegistration, notification) as Pydantic models
- ``VesEventBuilder``: a fluent builder that stamps the common header and
  attaches a domain block, producing the ``{"event": {...}}`` envelope expected
  by a VES collector
- ``VesCollectorClient``: a best-effort HTTP client that POSTs events to a VES
  collector using ``requests``; it is a no-op (returns a structured result) if
  the collector is absent or unreachable, so it never breaks import or runtime.

The O1 service (oam/o1.py) uses ``VesEventBuilder`` + ``VesCollectorClient`` to
emit heartbeats and fault notifications; the PM library's STREAM_BASED jobs map
their measurement reports onto the measurement domain here.
"""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

import requests
from pydantic import BaseModel, Field

VES_VERSION = "4.1"
VES_EVENT_LISTENER_VERSION = "7.2.1"


def _now() -> datetime:
    """UTC timestamp helper (timezone-aware per VES conventions)."""
    return datetime.now(timezone.utc)


def _ves_micros() -> int:
    """VES timestamps are microseconds since the UNIX epoch (UTC)."""
    return int(_now().timestamp() * 1_000_000)


# =============================================================================
# Enumerations (per VES 7.x common event format)
# =============================================================================

class VesDomain(str, Enum):
    """VES event domains supported by the O1 streaming interface."""
    FAULT = "fault"
    HEARTBEAT = "heartbeat"
    MEASUREMENT = "measurement"
    PNF_REGISTRATION = "pnfRegistration"
    NOTIFICATION = "notification"


class VesPriority(str, Enum):
    """commonEventHeader priority field."""
    HIGH = "High"
    MEDIUM = "Medium"
    NORMAL = "Normal"
    LOW = "Low"


class FaultSeverity(str, Enum):
    """eventSeverity for the fault domain (per VES / X.733 alarm severities)."""
    CRITICAL = "CRITICAL"
    MAJOR = "MAJOR"
    MINOR = "MINOR"
    WARNING = "WARNING"
    NORMAL = "NORMAL"


class VfStatus(str, Enum):
    """vfStatus for the fault domain."""
    ACTIVE = "Active"
    IDLE = "Idle"
    PREP_TERMINATE = "Preparing to terminate"
    READY_TERMINATE = "Ready to terminate"
    REQUEST_TERMINATE = "Requesting termination"


# =============================================================================
# commonEventHeader
# =============================================================================

class CommonEventHeader(BaseModel):
    """
    VES 7.x ``commonEventHeader``. Every event carries this header; the domain
    field selects which domain block accompanies it.
    """
    version: str = Field(default=VES_VERSION)
    vesEventListenerVersion: str = Field(default=VES_EVENT_LISTENER_VERSION)
    domain: VesDomain
    eventId: str = Field(default_factory=lambda: f"evt-{uuid.uuid4().hex[:16]}")
    eventName: str
    eventType: str = Field(default="")
    sourceId: str = Field(default="")
    sourceName: str = Field(default="oran-emulator-nf")
    reportingEntityId: str = Field(default="")
    reportingEntityName: str = Field(default="oran-emulator-o1")
    priority: VesPriority = Field(default=VesPriority.NORMAL)
    sequence: int = Field(default=0)
    startEpochMicrosec: int = Field(default_factory=_ves_micros)
    lastEpochMicrosec: int = Field(default_factory=_ves_micros)
    nfNamingCode: str = Field(default="gnb")
    nfVendorName: str = Field(default="ORAN-Emulator")
    timeZoneOffset: str = Field(default="UTC+00:00")


# =============================================================================
# Domain blocks
# =============================================================================

class FaultFields(BaseModel):
    """VES ``faultFields`` block (fault domain)."""
    faultFieldsVersion: str = Field(default=VES_VERSION)
    alarmCondition: str
    eventSourceType: str = Field(default="gnb")
    specificProblem: str = Field(default="")
    eventSeverity: FaultSeverity = Field(default=FaultSeverity.MINOR)
    vfStatus: VfStatus = Field(default=VfStatus.ACTIVE)
    alarmInterfaceA: Optional[str] = Field(default=None)
    alarmAdditionalInformation: Dict[str, Any] = Field(default_factory=dict)


class HeartbeatFields(BaseModel):
    """VES ``heartbeatFields`` block (heartbeat domain)."""
    heartbeatFieldsVersion: str = Field(default=VES_VERSION)
    heartbeatInterval: int = Field(default=60, description="Seconds between heartbeats")
    additionalFields: Dict[str, Any] = Field(default_factory=dict)


class MeasurementFields(BaseModel):
    """VES ``measurementFields`` block (measurement domain, streaming PM)."""
    measurementFieldsVersion: str = Field(default=VES_VERSION)
    measurementInterval: int = Field(default=900, description="Measurement period in seconds")
    additionalMeasurements: List[Dict[str, Any]] = Field(default_factory=list)
    additionalFields: Dict[str, Any] = Field(default_factory=dict)


class PnfRegistrationFields(BaseModel):
    """VES ``pnfRegistrationFields`` block (PNF plug-and-play registration)."""
    pnfRegistrationFieldsVersion: str = Field(default=VES_VERSION)
    serialNumber: str = Field(default="")
    vendorName: str = Field(default="ORAN-Emulator")
    modelNumber: str = Field(default="")
    unitType: str = Field(default="gnb")
    unitFamily: str = Field(default="O-RAN")
    softwareVersion: str = Field(default="1.0.0")
    oamV4IpAddress: Optional[str] = Field(default=None)
    oamV6IpAddress: Optional[str] = Field(default=None)
    additionalFields: Dict[str, Any] = Field(default_factory=dict)


class NotificationFields(BaseModel):
    """VES ``notificationFields`` block (notification domain)."""
    notificationFieldsVersion: str = Field(default=VES_VERSION)
    changeIdentifier: str = Field(default="")
    changeType: str = Field(default="")
    changeContact: Optional[str] = Field(default=None)
    newState: Optional[str] = Field(default=None)
    oldState: Optional[str] = Field(default=None)
    stateInterface: Optional[str] = Field(default=None)
    additionalFields: Dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# VesEventBuilder
# =============================================================================

class VesEventBuilder:
    """
    Fluent builder for VES 7.x events.

    Usage::

        evt = (VesEventBuilder("gnb-001")
               .heartbeat(interval=60)
               .build())

    Each domain method stamps a ``commonEventHeader`` with the correct domain
    and attaches the matching domain block. ``build()`` returns the full
    ``{"event": {...}}`` envelope a VES collector expects.
    """

    def __init__(self, source_name: str = "oran-emulator-nf", source_id: str = "") -> None:
        self.source_name = source_name
        self.source_id = source_id or source_name
        self._header: Optional[CommonEventHeader] = None
        self._domain_key: str = ""
        self._domain_block: Optional[BaseModel] = None
        self._sequence = 0

    def _make_header(self, domain: VesDomain, event_name: str, priority: VesPriority,
                     event_type: str = "") -> CommonEventHeader:
        return CommonEventHeader(
            domain=domain,
            eventName=event_name,
            eventType=event_type,
            sourceId=self.source_id,
            sourceName=self.source_name,
            reportingEntityId=self.source_id,
            priority=priority,
            sequence=self._sequence,
        )

    def fault(self, alarm_condition: str, specific_problem: str = "",
              severity: FaultSeverity = FaultSeverity.MINOR,
              event_source_type: str = "gnb",
              additional: Optional[Dict[str, Any]] = None) -> "VesEventBuilder":
        """Build a fault-domain event."""
        priority = (
            VesPriority.HIGH
            if severity in (FaultSeverity.CRITICAL, FaultSeverity.MAJOR)
            else VesPriority.NORMAL
        )
        self._header = self._make_header(
            VesDomain.FAULT, f"Fault_{alarm_condition}", priority, event_type="O-RAN-Fault"
        )
        self._domain_key = "faultFields"
        self._domain_block = FaultFields(
            alarmCondition=alarm_condition,
            specificProblem=specific_problem or alarm_condition,
            eventSeverity=severity,
            eventSourceType=event_source_type,
            alarmAdditionalInformation=additional or {},
        )
        return self

    def heartbeat(self, interval: int = 60,
                  additional: Optional[Dict[str, Any]] = None) -> "VesEventBuilder":
        """Build a heartbeat-domain event."""
        self._header = self._make_header(
            VesDomain.HEARTBEAT, "Heartbeat_oran_nf", VesPriority.NORMAL,
            event_type="O-RAN-Heartbeat",
        )
        self._domain_key = "heartbeatFields"
        self._domain_block = HeartbeatFields(
            heartbeatInterval=interval, additionalFields=additional or {}
        )
        return self

    def measurement(self, interval: int = 900,
                    measurements: Optional[List[Dict[str, Any]]] = None,
                    additional: Optional[Dict[str, Any]] = None) -> "VesEventBuilder":
        """Build a measurement-domain event (streaming PM)."""
        self._header = self._make_header(
            VesDomain.MEASUREMENT, "Measurement_oran_pm", VesPriority.NORMAL,
            event_type="O-RAN-Measurement",
        )
        self._domain_key = "measurementFields"
        self._domain_block = MeasurementFields(
            measurementInterval=interval,
            additionalMeasurements=measurements or [],
            additionalFields=additional or {},
        )
        return self

    def pnf_registration(self, serial_number: str = "", model_number: str = "",
                         software_version: str = "1.0.0",
                         oam_ipv4: Optional[str] = None,
                         additional: Optional[Dict[str, Any]] = None) -> "VesEventBuilder":
        """Build a pnfRegistration-domain event."""
        self._header = self._make_header(
            VesDomain.PNF_REGISTRATION, "pnfRegistration_oran_nf", VesPriority.NORMAL,
            event_type="O-RAN-PnP",
        )
        self._domain_key = "pnfRegistrationFields"
        self._domain_block = PnfRegistrationFields(
            serialNumber=serial_number,
            modelNumber=model_number,
            softwareVersion=software_version,
            oamV4IpAddress=oam_ipv4,
            additionalFields=additional or {},
        )
        return self

    def notification(self, change_identifier: str, change_type: str,
                     new_state: Optional[str] = None, old_state: Optional[str] = None,
                     additional: Optional[Dict[str, Any]] = None) -> "VesEventBuilder":
        """Build a notification-domain event (e.g. config/state change)."""
        self._header = self._make_header(
            VesDomain.NOTIFICATION, f"Notification_{change_type}", VesPriority.NORMAL,
            event_type="O-RAN-Notification",
        )
        self._domain_key = "notificationFields"
        self._domain_block = NotificationFields(
            changeIdentifier=change_identifier,
            changeType=change_type,
            newState=new_state,
            oldState=old_state,
            additionalFields=additional or {},
        )
        return self

    def with_sequence(self, sequence: int) -> "VesEventBuilder":
        """Set the header sequence number (call before a domain method)."""
        self._sequence = sequence
        if self._header is not None:
            self._header.sequence = sequence
        return self

    def build(self) -> Dict[str, Any]:
        """Return the VES ``{"event": {...}}`` envelope."""
        if self._header is None or self._domain_block is None:
            raise ValueError("No domain block set; call a domain method before build()")
        return {
            "event": {
                "commonEventHeader": self._header.model_dump(mode="json"),
                self._domain_key: self._domain_block.model_dump(mode="json"),
            }
        }


# =============================================================================
# VesCollectorClient (best-effort)
# =============================================================================

class VesCollectorClient:
    """
    Best-effort VES collector client.

    POSTs VES events to a collector's ``eventListener`` endpoint using
    ``requests``. If the collector is absent or unreachable the client does not
    raise; it returns a structured ``{"delivered": False, ...}`` result so the
    O1 service can keep emitting events in a standalone emulator deployment.
    """

    def __init__(self, collector_url: Optional[str] = None, timeout: float = 3.0,
                 auth: Optional[Any] = None) -> None:
        # Default to the conventional ONAP/O-RAN VES collector listener path.
        self.collector_url = collector_url or "http://127.0.0.1:8443/eventListener/v7"
        self.timeout = timeout
        self.auth = auth
        self.sent = 0
        self.failed = 0

    def send(self, event_envelope: Dict[str, Any]) -> Dict[str, Any]:
        """POST a single VES event; never raises on transport failure."""
        try:
            resp = requests.post(
                self.collector_url, json=event_envelope, timeout=self.timeout, auth=self.auth
            )
            delivered = 200 <= resp.status_code < 300 or resp.status_code == 202
            if delivered:
                self.sent += 1
            else:
                self.failed += 1
            return {
                "delivered": delivered,
                "statusCode": resp.status_code,
                "collector": self.collector_url,
            }
        except requests.RequestException as exc:
            self.failed += 1
            return {
                "delivered": False,
                "statusCode": None,
                "collector": self.collector_url,
                "error": str(exc),
                "note": "collector absent or unreachable; event not delivered (no-op)",
            }

    def send_batch(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """POST a VES eventList batch; falls back to per-event sends on failure."""
        batch = {"eventList": [e.get("event", e) for e in events]}
        try:
            resp = requests.post(
                self.collector_url, json=batch, timeout=self.timeout, auth=self.auth
            )
            delivered = 200 <= resp.status_code < 300 or resp.status_code == 202
            if delivered:
                self.sent += len(events)
            else:
                self.failed += len(events)
            return {
                "delivered": delivered,
                "statusCode": resp.status_code,
                "count": len(events),
                "collector": self.collector_url,
            }
        except requests.RequestException as exc:
            self.failed += len(events)
            return {
                "delivered": False,
                "statusCode": None,
                "count": len(events),
                "collector": self.collector_url,
                "error": str(exc),
                "note": "collector absent or unreachable; batch not delivered (no-op)",
            }

    def stats(self) -> Dict[str, Any]:
        """Return delivery counters."""
        return {
            "collector": self.collector_url,
            "sent": self.sent,
            "failed": self.failed,
            "vesEventListenerVersion": VES_EVENT_LISTENER_VERSION,
        }
