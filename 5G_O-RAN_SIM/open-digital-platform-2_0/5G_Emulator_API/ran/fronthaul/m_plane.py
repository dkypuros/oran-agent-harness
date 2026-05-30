#!/usr/bin/env python3
"""M-Plane library - O-RAN WG4 Management Plane YANG datastore (in-memory NETCONF model).

Spec: O-RAN.WG4.TS.MP.0-R005-v20.00 (Management Plane Specification).
Conformance: O-RAN.WG4.TS.CONF.0-R005-v15.00.

Pure library (no server). Models the O-RU M-Plane datastore as plain pydantic models keyed by the
O-RAN YANG modules (o-ran-uplane-conf, o-ran-module-cap, o-ran-supervision, o-ran-fan,
o-ran-software-management, o-ran-performance-management, o-ran-fm). The MPlaneDatastore class
provides NETCONF-style get / merge (edit-config) semantics over an in-memory tree and a
supervision_watchdog() method implementing the cu-plane connectivity supervision timer.
"""
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# M-Plane architecture model (O-RAN.WG4.TS.MP.0 section 3 - hierarchical vs hybrid)
# ---------------------------------------------------------------------------
class MPlaneArchitecture(str, Enum):
    """O-RU management architecture model.

    HIERARCHICAL: O-RU is managed solely by the O-DU (NETCONF endpoint on the O-DU side).
    HYBRID:       O-RU is managed by both the O-DU and a direct SMO/NMS NETCONF session.
    """
    HIERARCHICAL = "HIERARCHICAL"
    HYBRID = "HYBRID"


# ---------------------------------------------------------------------------
# o-ran-uplane-conf : low-level tx/rx endpoints, carriers, array-carriers
# ---------------------------------------------------------------------------
class LowLevelTxEndpoint(BaseModel):
    """low-level-tx-endpoints list entry (o-ran-uplane-conf)."""
    name: str
    array: str = Field("tx-array-0", description="reference to a tx antenna array")
    local_address: str = Field("", description="endpoint local logical address")


class LowLevelRxEndpoint(BaseModel):
    """low-level-rx-endpoints list entry (o-ran-uplane-conf)."""
    name: str
    array: str = Field("rx-array-0", description="reference to an rx antenna array")
    local_address: str = Field("", description="endpoint local logical address")


class TxArrayCarrier(BaseModel):
    """tx-array-carriers list entry (o-ran-uplane-conf)."""
    name: str
    absolute_frequency_center: int = Field(0, description="ARFCN of carrier center")
    channel_bandwidth: int = Field(100_000_000, description="bandwidth in Hz")
    active: str = Field("INACTIVE", description="ACTIVE | INACTIVE | SLEEP")
    state: str = Field("DISABLED", description="BUSY | READY | DISABLED")
    gain: int = Field(0, description="tx gain in dB (per spec scaling)")


class RxArrayCarrier(BaseModel):
    """rx-array-carriers list entry (o-ran-uplane-conf)."""
    name: str
    absolute_frequency_center: int = Field(0, description="ARFCN of carrier center")
    channel_bandwidth: int = Field(100_000_000, description="bandwidth in Hz")
    active: str = Field("INACTIVE", description="ACTIVE | INACTIVE | SLEEP")
    n_ta_offset: int = Field(25600, description="timing advance offset in Tc units")


class UplaneConf(BaseModel):
    """o-ran-uplane-conf top container."""
    low_level_tx_endpoints: List[LowLevelTxEndpoint] = Field(default_factory=list)
    low_level_rx_endpoints: List[LowLevelRxEndpoint] = Field(default_factory=list)
    tx_array_carriers: List[TxArrayCarrier] = Field(default_factory=list)
    rx_array_carriers: List[RxArrayCarrier] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# o-ran-module-cap : band caps, compression caps, supported section types
# ---------------------------------------------------------------------------
class BandCapabilities(BaseModel):
    """band-capabilities list entry (o-ran-module-cap)."""
    band_number: int = Field(78, description="3GPP NR operating band (e.g. n78)")
    max_supported_frequency_dl: int = Field(3_800_000, description="max DL freq (kHz)")
    min_supported_frequency_dl: int = Field(3_300_000, description="min DL freq (kHz)")
    max_supported_bandwidth_dl: int = Field(100_000, description="max DL bandwidth (kHz)")
    max_num_carriers_dl: int = Field(4, description="max simultaneous DL carriers")
    max_num_component_carriers: int = Field(4, description="max component carriers")


class CompressionCapabilities(BaseModel):
    """ru-compression-capabilities (o-ran-module-cap)."""
    iq_bit_width: int = Field(9, description="supported IQ bit width")
    compression_method: str = Field("BLOCK_FLOATING_POINT")
    fixed_point: bool = Field(True, description="fixed-point exponent supported")


class ModuleCap(BaseModel):
    """o-ran-module-cap top container."""
    ru_supported_category: str = Field("CAT_B", description="O-RU category A or B")
    max_power_per_pa_antenna: int = Field(33, description="dBm")
    band_capabilities: List[BandCapabilities] = Field(default_factory=list)
    compression_caps: List[CompressionCapabilities] = Field(default_factory=list)
    supported_section_types: List[int] = Field(
        default_factory=lambda: [0, 1, 3, 5, 6, 7],
        description="C-Plane section types supported by this O-RU",
    )
    ul_mixed_num_required_guard_rbs: int = Field(0)


# ---------------------------------------------------------------------------
# o-ran-supervision : cu-plane monitoring watchdog + supervision-notification
# ---------------------------------------------------------------------------
class CuPlaneMonitoring(BaseModel):
    """cu-plane-monitoring container (o-ran-supervision)."""
    configured_cu_mon_interval: int = Field(160, description="CU-plane inactivity timeout (s)")
    configured_cu_mon_guard_timer: int = Field(20, description="guard timer applied to interval (s)")


class Supervision(BaseModel):
    """o-ran-supervision top container (watchdog model)."""
    supervision_notification_interval: int = Field(60, description="notify request interval (s)")
    guard_timer_overhead: int = Field(10, description="extra guard added to the interval (s)")
    cu_plane_monitoring: CuPlaneMonitoring = Field(default_factory=CuPlaneMonitoring)


# ---------------------------------------------------------------------------
# o-ran-fan : fan state
# ---------------------------------------------------------------------------
class FanState(BaseModel):
    """fan-state list entry (o-ran-fan)."""
    name: str = Field("fan-0")
    fan_location: int = Field(0)
    present_and_operating: bool = Field(True)
    target_speed: int = Field(60, description="percent of max")
    fan_speed: int = Field(58, description="measured percent of max")


class Fan(BaseModel):
    """o-ran-fan top container."""
    fan_states: List[FanState] = Field(default_factory=lambda: [FanState()])


# ---------------------------------------------------------------------------
# o-ran-software-management : slots, running/inactive
# ---------------------------------------------------------------------------
class SoftwareSlot(BaseModel):
    """software-slot list entry (o-ran-software-management)."""
    name: str
    status: str = Field("VALID", description="VALID | INVALID | EMPTY")
    active: bool = Field(False)
    running: bool = Field(False)
    access: str = Field("READ_ONLY", description="READ_ONLY | READ_WRITE")
    product_code: str = Field("O-RU-78B")
    build_version: str = Field("v20.00")


class SoftwareManagement(BaseModel):
    """o-ran-software-management top container."""
    software_slots: List[SoftwareSlot] = Field(
        default_factory=lambda: [
            SoftwareSlot(name="slot-1", active=True, running=True, build_version="v20.00"),
            SoftwareSlot(name="slot-2", active=False, running=False, build_version="v19.02"),
        ]
    )


# ---------------------------------------------------------------------------
# o-ran-performance-management : RSSI / RX-window measurements
# ---------------------------------------------------------------------------
class RxWindowMeasurement(BaseModel):
    """rx-window-measurement object (o-ran-performance-management)."""
    name: str = Field("RX_ON_TIME")
    count: int = Field(0)


class PerformanceManagement(BaseModel):
    """o-ran-performance-management top container."""
    transceiver_measurement_active: bool = Field(True)
    rssi_dbm: int = Field(-92, description="received signal strength indicator (dBm)")
    rx_window_measurements: List[RxWindowMeasurement] = Field(
        default_factory=lambda: [
            RxWindowMeasurement(name="RX_ON_TIME", count=9_811_900),
            RxWindowMeasurement(name="RX_EARLY", count=60),
            RxWindowMeasurement(name="RX_LATE", count=44),
            RxWindowMeasurement(name="RX_CORRUPT", count=0),
        ]
    )


# ---------------------------------------------------------------------------
# o-ran-fm : alarm list (fault management)
# ---------------------------------------------------------------------------
class Alarm(BaseModel):
    """active-alarm-list entry (o-ran-fm)."""
    fault_id: int
    fault_source: str
    fault_severity: str = Field("MINOR", description="CRITICAL|MAJOR|MINOR|WARNING")
    is_cleared: bool = Field(False)
    fault_text: str = Field("")
    event_time: str = Field("")


class FaultManagement(BaseModel):
    """o-ran-fm top container."""
    active_alarm_list: List[Alarm] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Datastore aggregate
# ---------------------------------------------------------------------------
class MPlaneTree(BaseModel):
    """Full O-RU M-Plane datastore tree keyed by YANG module names."""
    architecture: MPlaneArchitecture = Field(MPlaneArchitecture.HYBRID)
    uplane_conf: UplaneConf = Field(default_factory=UplaneConf)
    module_cap: ModuleCap = Field(default_factory=ModuleCap)
    supervision: Supervision = Field(default_factory=Supervision)
    fan: Fan = Field(default_factory=Fan)
    software_management: SoftwareManagement = Field(default_factory=SoftwareManagement)
    performance_management: PerformanceManagement = Field(default_factory=PerformanceManagement)
    fault_management: FaultManagement = Field(default_factory=FaultManagement)


def _default_tree() -> MPlaneTree:
    """Seed a realistic O-RU datastore (n78 100 MHz, CAT-B, two SW slots)."""
    tree = MPlaneTree()
    tree.uplane_conf.low_level_tx_endpoints = [LowLevelTxEndpoint(name="tx-ep-0")]
    tree.uplane_conf.low_level_rx_endpoints = [LowLevelRxEndpoint(name="rx-ep-0")]
    tree.uplane_conf.tx_array_carriers = [
        TxArrayCarrier(name="txcc-0", absolute_frequency_center=3_700_000,
                       active="ACTIVE", state="READY")
    ]
    tree.uplane_conf.rx_array_carriers = [
        RxArrayCarrier(name="rxcc-0", absolute_frequency_center=3_700_000, active="ACTIVE")
    ]
    tree.module_cap.band_capabilities = [BandCapabilities()]
    tree.module_cap.compression_caps = [CompressionCapabilities()]
    return tree


class MPlaneDatastore:
    """In-memory O-RU M-Plane datastore with NETCONF get / edit-config (merge) semantics.

    Implements just enough of RFC 6241 NETCONF behaviour for the emulator: get() returns the
    serialized tree (optionally a single module), merge() applies an edit-config 'merge' operation
    by deep-merging a partial dict into the running datastore, and supervision_watchdog() evaluates
    the cu-plane supervision timer against the last keep-alive ('pet').
    """

    def __init__(self, architecture: MPlaneArchitecture = MPlaneArchitecture.HYBRID) -> None:
        self.tree: MPlaneTree = _default_tree()
        self.tree.architecture = architecture
        self._last_pet: datetime = datetime.now(timezone.utc)

    # -- NETCONF <get> ------------------------------------------------------
    def get(self, module: Optional[str] = None) -> Dict[str, Any]:
        """Return the running datastore (whole tree, or a single YANG module if named)."""
        full = self.tree.model_dump()
        if module is None:
            return full
        key = module.replace("o-ran-", "").replace("-", "_")
        if key not in full:
            raise KeyError(f"unknown M-Plane module: {module}")
        return {key: full[key]}

    # -- NETCONF <edit-config> operation="merge" ----------------------------
    def merge(self, patch: Dict[str, Any]) -> Dict[str, Any]:
        """Deep-merge a partial config into the running datastore (edit-config merge)."""
        current = self.tree.model_dump()
        merged = self._deep_merge(current, patch)
        self.tree = MPlaneTree(**merged)
        return self.tree.model_dump()

    @staticmethod
    def _deep_merge(base: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively merge patch into base; lists and scalars are replaced wholesale."""
        out = dict(base)
        for key, value in patch.items():
            if key in out and isinstance(out[key], dict) and isinstance(value, dict):
                out[key] = MPlaneDatastore._deep_merge(out[key], value)
            else:
                out[key] = value
        return out

    # -- o-ran-supervision watchdog ----------------------------------------
    def pet(self) -> datetime:
        """Reset the supervision watchdog (O-DU/SMO keep-alive received)."""
        self._last_pet = datetime.now(timezone.utc)
        return self._last_pet

    def supervision_watchdog(self) -> Dict[str, Any]:
        """Evaluate the supervision timer; report ALIVE/EXPIRED versus the configured interval.

        The effective deadline is supervision-notification-interval + guard-timer-overhead
        (o-ran-supervision). If the elapsed time since the last pet exceeds the deadline the
        O-RU would tear down the C/U-plane per O-RAN.WG4.TS.MP.0 supervision behaviour.
        """
        sup = self.tree.supervision
        deadline = sup.supervision_notification_interval + sup.guard_timer_overhead
        now = datetime.now(timezone.utc)
        elapsed = (now - self._last_pet).total_seconds()
        expired = elapsed > deadline
        return {
            "spec": "O-RAN.WG4.TS.MP.0-R005-v20.00",
            "module": "o-ran-supervision",
            "supervision_notification_interval": sup.supervision_notification_interval,
            "guard_timer_overhead": sup.guard_timer_overhead,
            "cu_plane_mon_interval": sup.cu_plane_monitoring.configured_cu_mon_interval,
            "cu_plane_mon_guard": sup.cu_plane_monitoring.configured_cu_mon_guard_timer,
            "deadline_seconds": deadline,
            "elapsed_seconds": round(elapsed, 3),
            "last_pet": self._last_pet.isoformat(),
            "status": "EXPIRED" if expired else "ALIVE",
        }


def hardware_inventory() -> Dict[str, Any]:
    """Return a simulated o-ran-hardware (ietf-hardware) component inventory for the O-RU."""
    return {
        "spec": "O-RAN.WG4.TS.MP.0-R005-v20.00",
        "module": "o-ran-hardware (ietf-hardware)",
        "components": [
            {"name": "o-ru-chassis", "class": "chassis", "mfg-name": "OpenDigitalPlatform",
             "model-name": "ODP-ORU-78B", "serial-num": "ORU-SN-0001",
             "admin-state": "unlocked", "oper-state": "enabled"},
            {"name": "rf-board-0", "class": "module", "parent": "o-ru-chassis",
             "oper-state": "enabled"},
            {"name": "pa-0", "class": "power-amplifier", "parent": "rf-board-0",
             "oper-state": "enabled"},
            {"name": "fan-0", "class": "fan", "parent": "o-ru-chassis", "oper-state": "enabled"},
        ],
    }


__all__ = [
    "MPlaneArchitecture",
    "LowLevelTxEndpoint",
    "LowLevelRxEndpoint",
    "TxArrayCarrier",
    "RxArrayCarrier",
    "UplaneConf",
    "BandCapabilities",
    "CompressionCapabilities",
    "ModuleCap",
    "CuPlaneMonitoring",
    "Supervision",
    "FanState",
    "Fan",
    "SoftwareSlot",
    "SoftwareManagement",
    "RxWindowMeasurement",
    "PerformanceManagement",
    "Alarm",
    "FaultManagement",
    "MPlaneTree",
    "MPlaneDatastore",
    "hardware_inventory",
]
