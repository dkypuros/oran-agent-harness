#!/usr/bin/env python3
"""
E2SM-LLC: E2 Service Model - Lower Layer Control

Spec: O-RAN.WG3.TS.E2SM-LLC-R004-v01.00
OID:  1.3.6.1.4.1.53148.1.2.2.5

The Lower Layer Control (LLC) Service Model enables the Near-RT RIC to monitor
and control the MAC and PHY lower layers of an O-DU at slot granularity. It
exposes lower-layer measurements (scheduling, HARQ, CSI, MCS, beamforming) and
supports:

  - RIC REPORT service (Lower Layer Info Type 1: scheduling/HARQ/CSI/MCS report)
    to deliver slot-level lower-layer KPIs to the Near-RT RIC.
  - RIC CONTROL service (Style 1: Slot Level PRB Quota, Style 2: DL/UL scheduling
    & beamforming control) to steer MAC/PHY behaviour per slot.

This module is consumed by the E2SM registry in e2ap.py via
build_ran_function_definition().
"""

from enum import Enum, IntEnum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# =============================================================================
# Service Model Identity (O-RAN.WG3.TS.E2SM-LLC-R004-v01.00 Section 6)
# =============================================================================

E2SM_LLC_OID = "1.3.6.1.4.1.53148.1.2.2.5"
E2SM_LLC_NAME = "E2SM-LLC"
E2SM_LLC_VERSION = "1.00"


# =============================================================================
# RIC Service Styles (E2SM-LLC-R004-v01.00 Section 7.4 / 7.6)
# =============================================================================

class LlcReportStyle(IntEnum):
    """RIC REPORT Service Styles per E2SM-LLC Section 7.4.1."""
    LOWER_LAYER_INFO = 1   # Lower Layer Information REPORT (slot-level KPIs)


class LlcControlStyle(IntEnum):
    """RIC CONTROL Service Styles per E2SM-LLC Section 7.6.1."""
    SLOT_LEVEL_PRB_QUOTA = 1   # Slot-level PRB quota control
    SCHEDULING_CONTROL = 2     # DL/UL scheduling, HARQ, MCS, beamforming control


class LlcEventTriggerType(str, Enum):
    """Event Trigger types per E2SM-LLC Section 8.2.1."""
    PERIODIC = "periodic"             # Periodic at a slot/symbol period
    UPON_RECEPTION = "uponReception"  # On lower-layer event reception


class LlcLowerLayerInfoType(IntEnum):
    """Lower Layer Information Type per E2SM-LLC Section 8.3 (REPORT payload)."""
    SCHEDULING = 1   # PRB allocation / scheduling decisions
    HARQ = 2         # HARQ process state and (n)ack statistics
    CSI = 3          # Channel State Information reports
    MCS = 4          # Modulation and Coding Scheme selection
    BEAMFORMING = 5  # Beam / CSI-RS / SSB beam info


# =============================================================================
# Slot / Cell scope (E2SM-LLC-R004-v01.00 Section 8.2 / 9.2)
# =============================================================================

class SlotInfo(BaseModel):
    """Slot identification per E2SM-LLC Section 9.2 (numerology + SFN + slot)."""
    sfn: int = Field(..., ge=0, le=1023, description="System Frame Number (0..1023)")
    slot: int = Field(..., ge=0, le=319, description="Slot index within frame")
    subCarrierSpacing: int = Field(default=30, description="SCS in kHz (15/30/60/120/240)")


class CellGlobalScope(BaseModel):
    """Cell scope per E2SM-LLC Section 8.2."""
    nrCellId: str = Field(..., description="NR Cell Identity (NCI)")
    physCellId: Optional[int] = Field(default=None, ge=0, le=1007, description="PCI")


# =============================================================================
# Lower Layer KPIs (E2SM-LLC-R004-v01.00 Section 8.3 - slot-level measurements)
# =============================================================================

class SchedulingKpi(BaseModel):
    """Scheduling KPIs per E2SM-LLC Section 8.3 (PRB usage / grants)."""
    prbUsedDl: Optional[int] = Field(default=None, ge=0, description="DL PRBs allocated this slot")
    prbUsedUl: Optional[int] = Field(default=None, ge=0, description="UL PRBs allocated this slot")
    prbAvailable: Optional[int] = Field(default=None, ge=0, description="Total PRBs in BWP")
    activeUeDl: Optional[int] = Field(default=None, ge=0, description="UEs scheduled in DL")
    activeUeUl: Optional[int] = Field(default=None, ge=0, description="UEs scheduled in UL")


class HarqKpi(BaseModel):
    """HARQ KPIs per E2SM-LLC Section 8.3."""
    harqProcessId: Optional[int] = Field(default=None, ge=0, le=31, description="HARQ process (0..31)")
    dlAckCount: Optional[int] = Field(default=None, ge=0)
    dlNackCount: Optional[int] = Field(default=None, ge=0)
    ulAckCount: Optional[int] = Field(default=None, ge=0)
    ulNackCount: Optional[int] = Field(default=None, ge=0)
    maxRetransmissions: Optional[int] = Field(default=None, ge=0)


class CsiKpi(BaseModel):
    """CSI report KPIs per E2SM-LLC Section 8.3."""
    cqi: Optional[int] = Field(default=None, ge=0, le=15, description="Channel Quality Indicator (0..15)")
    ri: Optional[int] = Field(default=None, ge=1, le=8, description="Rank Indicator")
    pmi: Optional[int] = Field(default=None, ge=0, description="Precoding Matrix Indicator")
    csiRsrp: Optional[int] = Field(default=None, description="CSI-RSRP (dBm)")


class McsKpi(BaseModel):
    """MCS KPIs per E2SM-LLC Section 8.3."""
    mcsIndexDl: Optional[int] = Field(default=None, ge=0, le=31, description="DL MCS index")
    mcsIndexUl: Optional[int] = Field(default=None, ge=0, le=31, description="UL MCS index")
    mcsTable: Optional[str] = Field(default=None, description="qam64/qam256/qam64LowSE")


class BeamformingKpi(BaseModel):
    """Beamforming KPIs per E2SM-LLC Section 8.3."""
    ssbBeamId: Optional[int] = Field(default=None, ge=0, description="Selected SSB beam index")
    csiRsBeamId: Optional[int] = Field(default=None, ge=0, description="Selected CSI-RS beam index")
    numActiveBeams: Optional[int] = Field(default=None, ge=0)
    beamRsrp: Optional[int] = Field(default=None, description="Selected beam RSRP (dBm)")


# =============================================================================
# RIC Event Trigger Definition (E2SM-LLC-R004-v01.00 Section 8.2.1)
# =============================================================================

class LlcEventTriggerDefinition(BaseModel):
    """RIC Event Trigger Definition per E2SM-LLC Section 8.2.1."""
    eventTriggerType: LlcEventTriggerType = Field(default=LlcEventTriggerType.PERIODIC)
    reportingPeriodSlots: Optional[int] = Field(default=None, ge=1, description="Period in slots")
    cellScope: Optional[CellGlobalScope] = Field(default=None)


# =============================================================================
# RIC ACTION Definition (E2SM-LLC-R004-v01.00 Section 8.2.2)
# =============================================================================

class LlcActionDefinition(BaseModel):
    """RIC Action Definition per E2SM-LLC Section 8.2.2."""
    ricStyleType: LlcReportStyle = Field(default=LlcReportStyle.LOWER_LAYER_INFO)
    lowerLayerInfoTypes: List[LlcLowerLayerInfoType] = Field(
        default_factory=list, description="Which lower-layer info types to report"
    )


# =============================================================================
# RIC Indication Header / Message - REPORT (E2SM-LLC Section 8.3)
# =============================================================================

class LlcIndicationHeader(BaseModel):
    """RIC Indication Header (REPORT) per E2SM-LLC Section 8.3.1."""
    cellScope: CellGlobalScope
    slotInfo: SlotInfo
    eventTime: Optional[str] = Field(default=None, description="ISO-8601 event timestamp")


class LlcReportMessage(BaseModel):
    """
    RIC Indication Message (REPORT) per E2SM-LLC Section 8.3.2.

    Slot-level lower-layer KPI snapshot. Only the fields for the requested
    lowerLayerInfoTypes are populated.
    """
    slotInfo: SlotInfo
    scheduling: Optional[SchedulingKpi] = Field(default=None)
    harq: Optional[HarqKpi] = Field(default=None)
    csi: Optional[CsiKpi] = Field(default=None)
    mcs: Optional[McsKpi] = Field(default=None)
    beamforming: Optional[BeamformingKpi] = Field(default=None)


# =============================================================================
# RIC CONTROL Header / Message / Outcome (E2SM-LLC Section 8.4 / 8.5)
# =============================================================================

class LlcControlHeader(BaseModel):
    """RIC Control Header per E2SM-LLC Section 8.4.1."""
    ricStyleType: LlcControlStyle = Field(default=LlcControlStyle.SCHEDULING_CONTROL)
    cellScope: CellGlobalScope
    slotInfo: Optional[SlotInfo] = Field(default=None, description="Target slot (slot-level control)")
    ricControlActionId: Optional[int] = Field(default=None, ge=0)


class LlcControlMessage(BaseModel):
    """
    RIC Control Message per E2SM-LLC Section 8.4.2.

    Slot-level MAC/PHY control: PRB quota (Style 1), or scheduling / HARQ / MCS /
    beamforming control (Style 2).
    """
    ricStyleType: LlcControlStyle = Field(default=LlcControlStyle.SCHEDULING_CONTROL)
    prbQuotaDl: Optional[int] = Field(default=None, ge=0, description="DL PRB quota (Style 1)")
    prbQuotaUl: Optional[int] = Field(default=None, ge=0, description="UL PRB quota (Style 1)")
    targetMcsDl: Optional[int] = Field(default=None, ge=0, le=31, description="Override DL MCS")
    targetMcsUl: Optional[int] = Field(default=None, ge=0, le=31, description="Override UL MCS")
    maxHarqRetransmissions: Optional[int] = Field(default=None, ge=0, description="HARQ retx cap")
    forcedBeamId: Optional[int] = Field(default=None, ge=0, description="Force SSB/CSI-RS beam")


class LlcControlOutcome(BaseModel):
    """RIC Control Outcome per E2SM-LLC Section 8.5.2."""
    ricStyleType: LlcControlStyle = Field(default=LlcControlStyle.SCHEDULING_CONTROL)
    receivedTimestamp: Optional[str] = Field(default=None, description="ISO-8601")
    applied: bool = Field(default=True, description="Whether the control was applied at the target slot")
    appliedSlotInfo: Optional[SlotInfo] = Field(default=None)


# =============================================================================
# RAN Function Definition (E2SM-LLC-R004-v01.00 Section 8.1)
# =============================================================================

class LlcRanFunctionDefinition(BaseModel):
    """
    E2SM-LLC RAN Function Definition per E2SM-LLC Section 8.1.

    Advertised by the O-DU in E2 Setup: declares supported lower-layer info
    types and the REPORT/CONTROL styles available.
    """
    ranFunctionShortName: str = Field(default=E2SM_LLC_NAME)
    ranFunctionE2smOid: str = Field(default=E2SM_LLC_OID)
    ranFunctionDescription: str = Field(default="Lower Layer Control Service Model")
    ranFunctionInstance: int = Field(default=0, ge=0)
    supportedLowerLayerInfoTypes: List[str] = Field(default_factory=list)
    reportStyles: List[Dict[str, Any]] = Field(default_factory=list)
    controlStyles: List[Dict[str, Any]] = Field(default_factory=list)


def build_ran_function_definition() -> Dict[str, Any]:
    """
    Build the E2SM-LLC RAN Function Definition dict for the e2ap E2SM registry.

    Returns a dict shaped for E2smRegistry.service_models consumption:
    {oid, name, version, description, supportedActions, ranFunctionDefinition}.
    """
    report_styles = [
        {
            "ricStyleType": int(LlcReportStyle.LOWER_LAYER_INFO),
            "ricStyleName": "Lower Layer Information Report",
            "ricActionFormat": "slot-level scheduling/HARQ/CSI/MCS/beamforming KPIs",
        },
    ]
    control_styles = [
        {
            "ricStyleType": int(LlcControlStyle.SLOT_LEVEL_PRB_QUOTA),
            "ricStyleName": "Slot Level PRB Quota",
            "ricControlAction": "set per-slot DL/UL PRB quota",
        },
        {
            "ricStyleType": int(LlcControlStyle.SCHEDULING_CONTROL),
            "ricStyleName": "Scheduling / HARQ / MCS / Beamforming Control",
            "ricControlAction": "steer MAC/PHY scheduling per slot",
        },
    ]

    definition = LlcRanFunctionDefinition(
        supportedLowerLayerInfoTypes=[t.name for t in LlcLowerLayerInfoType],
        reportStyles=report_styles,
        controlStyles=control_styles,
    )

    return {
        "oid": E2SM_LLC_OID,
        "name": E2SM_LLC_NAME,
        "version": E2SM_LLC_VERSION,
        "description": "Lower Layer Control Service Model (MAC/PHY slot-level control & KPIs)",
        "supportedActions": ["REPORT", "CONTROL"],
        "ranFunctionDefinition": definition.model_dump(),
    }
