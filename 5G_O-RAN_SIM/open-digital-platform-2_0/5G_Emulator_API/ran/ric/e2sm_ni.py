#!/usr/bin/env python3
"""
E2SM-NI: E2 Service Model - Network Interface

Spec: ORAN-WG3.E2SM-NI-v01.00
OID:  1.3.6.1.4.1.53148.1.2.2.1

The Network Interface (NI) Service Model enables the Near-RT RIC to trace and
monitor the network interface protocol messages exchanged by an E2 Node on its
3GPP interfaces (NGAP, XnAP, F1AP, E1AP, S1AP). It supports:

  - RIC REPORT service: report a copy of a network-interface message (the
    raw interface PDU plus metadata: interface type, direction, message type).
  - RIC INSERT / POLICY / CONTROL services (Section 7): influence or suspend the
    procedure associated with a traced interface message.

This module is consumed by the E2SM registry in e2ap.py via
build_ran_function_definition().
"""

from enum import Enum, IntEnum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# =============================================================================
# Service Model Identity (ORAN-WG3.E2SM-NI-v01.00 Section 6)
# =============================================================================

E2SM_NI_OID = "1.3.6.1.4.1.53148.1.2.2.1"
E2SM_NI_NAME = "E2SM-NI"
E2SM_NI_VERSION = "1.00"


# =============================================================================
# Network Interface Types (E2SM-NI-v01.00 Section 8.3.1, NI-Type)
# =============================================================================

class NiInterfaceType(IntEnum):
    """
    Network Interface protocol type per E2SM-NI Section 8.3.1.

    The 3GPP interfaces whose messages can be traced over the E2 NI model.
    """
    NG = 0    # NGAP  - gNB <-> 5GC AMF (TS 38.413)
    XN = 1    # XnAP  - gNB <-> gNB     (TS 38.423)
    F1 = 2    # F1AP  - O-CU <-> O-DU   (TS 38.473)
    E1 = 3    # E1AP  - O-CU-CP <-> O-CU-UP (TS 38.463)
    S1 = 4    # S1AP  - eNB <-> EPC MME (TS 36.413)
    X2 = 5    # X2AP  - eNB <-> eNB / en-gNB (TS 36.423)


class NiMessageDirection(IntEnum):
    """Message direction per E2SM-NI Section 8.3.2 (NI-Message-Direction)."""
    INCOMING = 0   # received by the E2 Node on the interface
    OUTGOING = 1   # sent by the E2 Node on the interface


class NiTimeStampType(str, Enum):
    """Timestamp granularity per E2SM-NI Section 8.3."""
    NONE = "none"
    SECONDS = "seconds"
    MICROSECONDS = "microseconds"


# =============================================================================
# RIC Service Styles (E2SM-NI-v01.00 Section 7.4 / 7.5)
# =============================================================================

class NiReportStyle(IntEnum):
    """RIC REPORT Service Styles per E2SM-NI Section 7.4.1."""
    NI_MESSAGE_COPY = 1          # Report a copy of a network interface message
    NI_MESSAGE_PROTOCOL_IE = 2   # Report selected protocol IEs of a NI message


class NiInsertStyle(IntEnum):
    """RIC INSERT Service Styles per E2SM-NI Section 7.5.1."""
    NI_MESSAGE_SUSPEND = 1       # Insert: suspend the associated NI procedure


# =============================================================================
# Network Interface Protocol IE (E2SM-NI-v01.00 Section 8.2.4)
# =============================================================================

class NiProtocolIE(BaseModel):
    """
    Network Interface Protocol IE per E2SM-NI Section 8.2.4.

    Identifies a single protocol IE within a traced interface message, used to
    filter (event trigger / action) or to convey extracted IE values (report).
    """
    interfaceProtocolIeId: int = Field(..., ge=0, description="3GPP IE id within the NI PDU")
    interfaceProtocolIeTest: Optional[str] = Field(
        default=None, description="equal/greaterthan/lessthan/contains/present"
    )
    interfaceProtocolIeValue: Optional[Any] = Field(default=None, description="IE value for match/report")


# =============================================================================
# RIC Event Trigger Definition (E2SM-NI-v01.00 Section 8.2.1)
# =============================================================================

class NiEventTriggerDefinition(BaseModel):
    """
    RIC Event Trigger Definition per E2SM-NI Section 8.2.1.

    Triggers a REPORT/INSERT when a matching interface message is observed.
    """
    interfaceType: NiInterfaceType = Field(..., description="NI type (NG/Xn/F1/E1/S1/X2)")
    interfaceDirection: NiMessageDirection = Field(default=NiMessageDirection.INCOMING)
    interfaceMessageType: Optional[Dict[str, Any]] = Field(
        default=None, description="procedureCode + typeOfMessage (init/successful/unsuccessful)"
    )
    interfaceProtocolIeList: List[NiProtocolIE] = Field(
        default_factory=list, description="Optional IE-level match conditions"
    )


# =============================================================================
# RIC ACTION Definition (E2SM-NI-v01.00 Section 8.2.2)
# =============================================================================

class NiActionDefinition(BaseModel):
    """RIC Action Definition per E2SM-NI Section 8.2.2."""
    ricStyleType: NiReportStyle = Field(default=NiReportStyle.NI_MESSAGE_COPY)
    interfaceProtocolIeList: List[NiProtocolIE] = Field(
        default_factory=list, description="IEs to extract (Style 2 protocol-IE report)"
    )


# =============================================================================
# RIC Indication Header / Message - REPORT (E2SM-NI-v01.00 Section 8.2.3)
# =============================================================================

class NiIndicationHeader(BaseModel):
    """RIC Indication Header per E2SM-NI Section 8.2.3.1."""
    interfaceType: NiInterfaceType
    interfaceId: Optional[str] = Field(default=None, description="Global interface identifier")
    interfaceDirection: NiMessageDirection = Field(default=NiMessageDirection.INCOMING)
    timestamp: Optional[str] = Field(default=None, description="ISO-8601 capture time")


class NiReportMessage(BaseModel):
    """
    RIC Indication Message (REPORT) per E2SM-NI Section 8.2.3.2.

    Carries the traced network-interface PDU (Style 1) or the extracted
    protocol IEs (Style 2).
    """
    ricStyleType: NiReportStyle = Field(default=NiReportStyle.NI_MESSAGE_COPY)
    interfaceMessage: Optional[bytes] = Field(default=None, description="Raw NI PDU (Style 1)")
    interfaceProtocolIeList: List[NiProtocolIE] = Field(
        default_factory=list, description="Extracted IEs (Style 2)"
    )


# =============================================================================
# RIC CONTROL / INSERT Header / Message (E2SM-NI-v01.00 Section 8.2.5)
# =============================================================================

class NiControlHeader(BaseModel):
    """RIC Control/Insert Header per E2SM-NI Section 8.2.5.1."""
    interfaceType: NiInterfaceType
    interfaceId: Optional[str] = Field(default=None)
    interfaceDirection: NiMessageDirection = Field(default=NiMessageDirection.OUTGOING)
    ricControlActionId: Optional[int] = Field(default=None, ge=0)


class NiControlMessage(BaseModel):
    """
    RIC Control/Insert Message per E2SM-NI Section 8.2.5.2.

    Carries the (possibly modified) interface PDU to inject, or an indication to
    suspend the associated NI procedure (INSERT style).
    """
    interfaceMessage: Optional[bytes] = Field(default=None, description="NI PDU to inject")
    suspendProcedure: bool = Field(default=False, description="INSERT: suspend associated procedure")


# =============================================================================
# RAN Function Definition (E2SM-NI-v01.00 Section 8.1)
# =============================================================================

class NiRanFunctionDefinition(BaseModel):
    """
    E2SM-NI RAN Function Definition per E2SM-NI Section 8.1.

    Advertised by the E2 Node in E2 Setup: declares which 3GPP interfaces the
    node can trace and the supported REPORT/INSERT styles.
    """
    ranFunctionShortName: str = Field(default=E2SM_NI_NAME)
    ranFunctionE2smOid: str = Field(default=E2SM_NI_OID)
    ranFunctionDescription: str = Field(default="Network Interface Service Model")
    ranFunctionInstance: int = Field(default=0, ge=0)
    supportedInterfaces: List[str] = Field(default_factory=list)
    reportStyles: List[Dict[str, Any]] = Field(default_factory=list)
    insertStyles: List[Dict[str, Any]] = Field(default_factory=list)


def build_ran_function_definition() -> Dict[str, Any]:
    """
    Build the E2SM-NI RAN Function Definition dict for the e2ap E2SM registry.

    Returns a dict shaped for E2smRegistry.service_models consumption:
    {oid, name, version, description, supportedActions, ranFunctionDefinition}.
    """
    report_styles = [
        {
            "ricStyleType": int(NiReportStyle.NI_MESSAGE_COPY),
            "ricStyleName": "Network Interface Message Copy",
            "ricActionFormat": "interface message copy",
        },
        {
            "ricStyleType": int(NiReportStyle.NI_MESSAGE_PROTOCOL_IE),
            "ricStyleName": "Network Interface Protocol IE",
            "ricActionFormat": "selected protocol IEs",
        },
    ]
    insert_styles = [
        {
            "ricStyleType": int(NiInsertStyle.NI_MESSAGE_SUSPEND),
            "ricStyleName": "Network Interface Procedure Suspend",
            "ricControlAction": "suspend associated NI procedure",
        },
    ]

    definition = NiRanFunctionDefinition(
        supportedInterfaces=[t.name for t in NiInterfaceType],
        reportStyles=report_styles,
        insertStyles=insert_styles,
    )

    return {
        "oid": E2SM_NI_OID,
        "name": E2SM_NI_NAME,
        "version": E2SM_NI_VERSION,
        "description": "Network Interface Service Model (NGAP/XnAP/F1AP/E1AP/S1AP tracing)",
        "supportedActions": ["REPORT", "INSERT", "POLICY"],
        "ranFunctionDefinition": definition.model_dump(),
    }
