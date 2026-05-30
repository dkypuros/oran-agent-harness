#!/usr/bin/env python3
"""
E2SM-CCC: E2 Service Model - Cell Configuration and Control

Spec: O-RAN.WG3.TS.E2SM-CCC-R004-v06.00
OID:  1.3.6.1.4.1.53148.1.2.2.4

The Cell Configuration and Control (CCC) Service Model enables the Near-RT RIC
to retrieve and modify configuration of E2 Nodes (O-CU-CP, O-CU-UP, O-DU) at the
node level and cell level. It exposes RAN Configuration Structures (groups of
configuration attributes) and supports:

  - RIC REPORT service (Style 1: Node-level config change, Style 2: Cell-level
    config change) to notify the Near-RT RIC when a configuration attribute changes.
  - RIC CONTROL service (Style 1: Node-level config control, Style 2: Cell-level
    config control) to set a configuration attribute to a new value.

This module is consumed by the E2SM registry in e2ap.py via
build_ran_function_definition().
"""

from enum import Enum, IntEnum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# =============================================================================
# Service Model Identity (O-RAN.WG3.TS.E2SM-CCC-R004-v06.00 Section 6)
# =============================================================================

E2SM_CCC_OID = "1.3.6.1.4.1.53148.1.2.2.4"
E2SM_CCC_NAME = "E2SM-CCC"
E2SM_CCC_VERSION = "6.00"


# =============================================================================
# RIC Service Styles (E2SM-CCC-R004-v06.00 Section 7.4 / 7.5 / 7.6)
# =============================================================================

class CccReportStyle(IntEnum):
    """RIC REPORT Service Styles per E2SM-CCC Section 7.4.1"""
    NODE_LEVEL_CONFIG_CHANGE = 1   # Node-Level Configuration Structures REPORT
    CELL_LEVEL_CONFIG_CHANGE = 2   # Cell-Level Configuration Structures REPORT


class CccControlStyle(IntEnum):
    """RIC CONTROL Service Styles per E2SM-CCC Section 7.6.1"""
    NODE_LEVEL_CONFIG_CONTROL = 1  # Node-Level Configuration Structures CONTROL
    CELL_LEVEL_CONFIG_CONTROL = 2  # Cell-Level Configuration Structures CONTROL


class CccEventTriggerType(str, Enum):
    """Event Trigger types per E2SM-CCC Section 8.2.1"""
    PERIODIC = "periodic"                   # Periodic reporting at a given period
    UPON_CHANGE = "uponChange"             # On configuration structure change
    UPON_CHANGE_AND_PERIODIC = "uponChangeAndPeriodic"


class CccChangeType(str, Enum):
    """Configuration structure change type per E2SM-CCC Section 8.3.2"""
    NONE = "none"
    MODIFY = "modify"
    ADD = "add"
    DELETE = "delete"


class CccConfigLevel(str, Enum):
    """Configuration structure granularity per E2SM-CCC Section 8.4"""
    NODE = "O-RRMPolicyRatio"   # node-level RAN config structures
    NODE_GENERIC = "node"
    CELL = "cell"


# =============================================================================
# RAN Configuration Structures (E2SM-CCC-R004-v06.00 Section 8.4)
# =============================================================================

class OCuCpConfig(BaseModel):
    """
    O-CU-CP node-level configuration attributes per E2SM-CCC Section 8.4.1.

    Models a subset of the gNBCUCPFunction managed-object attributes that the
    Near-RT RIC may read (REPORT) or set (CONTROL) over the CCC service model.
    """
    gnbId: Optional[str] = Field(default=None, description="gNB Identifier")
    gnbCuName: Optional[str] = Field(default=None, description="O-CU-CP name")
    plmnId: Optional[str] = Field(default=None, description="PLMN Identity")
    numberOfDrbs: Optional[int] = Field(default=None, ge=0, description="Active DRB count")


class OCuUpConfig(BaseModel):
    """O-CU-UP node-level configuration attributes per E2SM-CCC Section 8.4.2."""
    gnbId: Optional[str] = Field(default=None, description="gNB Identifier")
    gnbCuUpId: Optional[int] = Field(default=None, ge=0, description="O-CU-UP ID")
    plmnId: Optional[str] = Field(default=None, description="PLMN Identity")


class ODuConfig(BaseModel):
    """O-DU node-level configuration attributes per E2SM-CCC Section 8.4.3."""
    gnbId: Optional[str] = Field(default=None, description="gNB Identifier")
    gnbDuId: Optional[int] = Field(default=None, ge=0, description="O-DU ID")
    gnbDuName: Optional[str] = Field(default=None, description="O-DU name")


class CellConfig(BaseModel):
    """
    Cell-level configuration attributes per E2SM-CCC Section 8.4.4
    (NRCellDU / NRCellCU managed-object attributes).
    """
    nrCellId: str = Field(..., description="NR Cell Identity (NCI)")
    physCellId: Optional[int] = Field(default=None, ge=0, le=1007, description="PCI (0..1007)")
    arfcnDl: Optional[int] = Field(default=None, ge=0, description="DL NR-ARFCN")
    arfcnUl: Optional[int] = Field(default=None, ge=0, description="UL NR-ARFCN")
    bSChannelBwDl: Optional[int] = Field(default=None, ge=0, description="DL bandwidth (MHz)")
    ssbFrequency: Optional[int] = Field(default=None, ge=0, description="SSB NR-ARFCN")
    administrativeState: Optional[str] = Field(default=None, description="locked/unlocked/shuttingDown")
    operationalState: Optional[str] = Field(default=None, description="enabled/disabled")


class RanConfigurationStructure(BaseModel):
    """
    RAN Configuration Structure per E2SM-CCC Section 8.4.

    A named group of configuration attributes (the unit reported/controlled by
    the CCC service model). 'valuesOfAttributes' carries the attribute payload
    (node-level: O-CU/O-DU config; cell-level: cell config).
    """
    ranConfigurationStructureName: str = Field(..., description="e.g. O-CellDU, O-RRMPolicyRatio")
    configLevel: CccConfigLevel = Field(default=CccConfigLevel.CELL)
    changeType: CccChangeType = Field(default=CccChangeType.NONE)
    valuesOfAttributes: Dict[str, Any] = Field(default_factory=dict, description="Attribute name/value map")
    oldValuesOfAttributes: Optional[Dict[str, Any]] = Field(default=None, description="Prior values (REPORT)")


# =============================================================================
# RIC Event Trigger Definition (E2SM-CCC-R004-v06.00 Section 8.2)
# =============================================================================

class CccEventTriggerDefinition(BaseModel):
    """RIC Event Trigger Definition per E2SM-CCC Section 8.2."""
    eventTriggerType: CccEventTriggerType = Field(default=CccEventTriggerType.UPON_CHANGE)
    reportingPeriodMs: Optional[int] = Field(default=None, ge=1, description="Period (ms) when periodic")
    listOfNodeLevelConfigStructures: List[str] = Field(default_factory=list)
    listOfCellLevelConfigStructures: List[str] = Field(default_factory=list)


# =============================================================================
# RIC ACTION Definition (E2SM-CCC-R004-v06.00 Section 8.3)
# =============================================================================

class CccActionDefinition(BaseModel):
    """
    RIC Action Definition per E2SM-CCC Section 8.3.

    Selects which RAN Configuration Structures the REPORT action targets.
    """
    ricStyleType: CccReportStyle = Field(default=CccReportStyle.CELL_LEVEL_CONFIG_CHANGE)
    listOfConfigurationStructures: List[str] = Field(
        default_factory=list, description="Names of RAN config structures to report"
    )


# =============================================================================
# RIC Indication Header / Message - REPORT (E2SM-CCC Section 8.3.1 / 8.3.2)
# =============================================================================

class CccIndicationHeader(BaseModel):
    """RIC Indication Header (REPORT) per E2SM-CCC Section 8.3.1."""
    indicationReason: CccEventTriggerType = Field(default=CccEventTriggerType.UPON_CHANGE)
    eventTime: Optional[str] = Field(default=None, description="ISO-8601 event timestamp")


class CccReportMessage(BaseModel):
    """
    RIC Indication Message (REPORT) per E2SM-CCC Section 8.3.2.

    Carries the changed configuration structures (node- and/or cell-level).
    """
    ricStyleType: CccReportStyle = Field(default=CccReportStyle.CELL_LEVEL_CONFIG_CHANGE)
    configurationStructuresReported: List[RanConfigurationStructure] = Field(default_factory=list)


# =============================================================================
# RIC CONTROL Header / Message / Outcome (E2SM-CCC Section 8.4 / 8.5)
# =============================================================================

class CccControlHeader(BaseModel):
    """RIC Control Header per E2SM-CCC Section 8.4.5."""
    ricStyleType: CccControlStyle = Field(default=CccControlStyle.CELL_LEVEL_CONFIG_CONTROL)
    ricControlActionId: Optional[int] = Field(default=None, ge=0)


class CccControlMessage(BaseModel):
    """
    RIC Control Message per E2SM-CCC Section 8.4.6.

    Sets one or more configuration attributes to new values. Each structure's
    'valuesOfAttributes' carries the target attribute/value pairs.
    """
    ricStyleType: CccControlStyle = Field(default=CccControlStyle.CELL_LEVEL_CONFIG_CONTROL)
    listOfConfigurationStructures: List[RanConfigurationStructure] = Field(default_factory=list)


class CccControlOutcome(BaseModel):
    """RIC Control Outcome per E2SM-CCC Section 8.5.2."""
    ricStyleType: CccControlStyle = Field(default=CccControlStyle.CELL_LEVEL_CONFIG_CONTROL)
    receivedTimestamp: Optional[str] = Field(default=None, description="ISO-8601")
    appliedConfigurationStructures: List[RanConfigurationStructure] = Field(default_factory=list)
    failedConfigurationStructures: List[Dict[str, Any]] = Field(default_factory=list)


# =============================================================================
# RAN Function Definition (E2SM-CCC-R004-v06.00 Section 8.1)
# =============================================================================

class CccRanFunctionDefinition(BaseModel):
    """
    E2SM-CCC RAN Function Definition per E2SM-CCC Section 8.1.

    Advertised by the E2 Node in E2 Setup to declare the CCC service model
    capabilities (supported REPORT and CONTROL styles, and the RAN config
    structures the node exposes).
    """
    ranFunctionShortName: str = Field(default=E2SM_CCC_NAME)
    ranFunctionE2smOid: str = Field(default=E2SM_CCC_OID)
    ranFunctionDescription: str = Field(default="Cell Configuration and Control Service Model")
    ranFunctionInstance: int = Field(default=0, ge=0)
    reportStyles: List[Dict[str, Any]] = Field(default_factory=list)
    controlStyles: List[Dict[str, Any]] = Field(default_factory=list)
    supportedNodeLevelConfigStructures: List[str] = Field(default_factory=list)
    supportedCellLevelConfigStructures: List[str] = Field(default_factory=list)


def build_ran_function_definition() -> Dict[str, Any]:
    """
    Build the E2SM-CCC RAN Function Definition dict for the e2ap E2SM registry.

    Returns a dict shaped for E2smRegistry.service_models consumption:
    {oid, name, version, description, supportedActions, ranFunctionDefinition}.
    """
    report_styles = [
        {
            "ricStyleType": int(CccReportStyle.NODE_LEVEL_CONFIG_CHANGE),
            "ricStyleName": "Node-Level Configuration and Control",
            "ricActionFormat": "node-level config structures",
        },
        {
            "ricStyleType": int(CccReportStyle.CELL_LEVEL_CONFIG_CHANGE),
            "ricStyleName": "Cell-Level Configuration and Control",
            "ricActionFormat": "cell-level config structures",
        },
    ]
    control_styles = [
        {
            "ricStyleType": int(CccControlStyle.NODE_LEVEL_CONFIG_CONTROL),
            "ricStyleName": "Node-Level Configuration and Control",
            "ricControlAction": "set node-level config attribute",
        },
        {
            "ricStyleType": int(CccControlStyle.CELL_LEVEL_CONFIG_CONTROL),
            "ricStyleName": "Cell-Level Configuration and Control",
            "ricControlAction": "set cell-level config attribute",
        },
    ]

    definition = CccRanFunctionDefinition(
        reportStyles=report_styles,
        controlStyles=control_styles,
        supportedNodeLevelConfigStructures=[
            "O-GnbCuCpFunction", "O-GnbCuUpFunction", "O-GnbDuFunction", "O-RRMPolicyRatio",
        ],
        supportedCellLevelConfigStructures=["O-NRCellDU", "O-NRCellCU", "O-CellDU"],
    )

    return {
        "oid": E2SM_CCC_OID,
        "name": E2SM_CCC_NAME,
        "version": E2SM_CCC_VERSION,
        "description": "Cell Configuration and Control Service Model",
        "supportedActions": ["REPORT", "CONTROL"],
        "ranFunctionDefinition": definition.model_dump(),
    }
