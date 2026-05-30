#!/usr/bin/env python3
"""CUS-Plane library - O-RAN WG4 Control/User/Synchronization Plane over the Open Fronthaul (eCPRI).

Spec: O-RAN.WG4.TS.CUS.0-R005-v20.00 (Control, User and Synchronization Plane Specification).
Conformance: O-RAN.WG4.TS.CONF.0-R005-v15.00.
Timing:      O-RAN.WG4.CTI-TMP.0-R003-v04.00 (Cooperative Transport Interface timing).

This is a pure library (no FastAPI server). It models the eCPRI transport, the C-Plane section
extension types, the U-Plane IQ data frame header, IQ compression methods, beamforming weights and
the S-Plane synchronization (PTP/SyncE, LLS-C topologies and clock states). A CusPlaneStats helper
returns simulated C/U/S plane statistics for the O-RU service to expose.
"""
from enum import Enum, IntEnum
from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# eCPRI common header (IEEE-1914.3 / eCPRI 2.0 message types carried on the FH)
# Per O-RAN.WG4.TS.CUS.0 the lower-layer split (Split Option 7-2x) maps onto eCPRI.
# ---------------------------------------------------------------------------
class EcpriMessageType(IntEnum):
    """eCPRI message type codes (eCPRI Specification v2.0, Table 'Message Types')."""
    IQ_DATA = 0
    BIT_SEQUENCE = 1
    RT_CONTROL_DATA = 2
    GENERIC_DATA_TRANSFER = 3
    REMOTE_MEM_ACCESS = 4
    ONE_WAY_DELAY = 5
    REMOTE_RESET = 6
    EVENT_INDICATION = 7


class EcpriHeader(BaseModel):
    """eCPRI common header fields prefixing every fronthaul message."""
    ecpri_version: int = Field(1, ge=0, le=15, description="eCPRI protocol revision (0x1)")
    ecpri_concatenation: bool = Field(False, description="C-bit: another eCPRI msg follows")
    message_type: EcpriMessageType = Field(EcpriMessageType.IQ_DATA)
    payload_size: int = Field(0, ge=0, le=0xFFFF, description="Payload byte count")
    pc_id: int = Field(0, ge=0, le=0xFFFF, description="Real-time control/eAxC physical channel id")
    seq_id: int = Field(0, ge=0, le=0xFFFF, description="Sequence/subsequence identifier")


# ---------------------------------------------------------------------------
# C-Plane: section types per O-RAN.WG4.TS.CUS.0 section 7 (Control Plane)
# ---------------------------------------------------------------------------
class CPlaneSectionType(IntEnum):
    """C-Plane section types (O-RAN.WG4.TS.CUS.0-R005-v20.00 Table 7.2.2-1)."""
    UNUSED_RB_OR_SYMBOL = 0          # Section Type 0
    MOST_DL_UL_RADIO_CHANNELS = 1    # Section Type 1 (most DL/UL channels)
    PRACH_MIXED_NUMEROLOGY = 3       # Section Type 3 (PRACH and mixed-numerology)
    UE_SCHEDULING_INFO = 5           # Section Type 5 (UE scheduling, real-time BF)
    CHANNEL_INFORMATION = 6          # Section Type 6 (channel information)
    LAA = 7                          # Section Type 7 (LAA / unlicensed)


class FrameStructure(BaseModel):
    """frameStructure: subcarrier spacing (mu) and FFT/iFFT size exponent."""
    fft_size_exponent: int = Field(12, ge=0, le=15, description="log2(FFT size), e.g. 12 -> 4096")
    subcarrier_spacing_index: int = Field(1, ge=0, le=4, description="3GPP numerology mu (0..4)")


class CPlaneSection(BaseModel):
    """A single C-Plane section description (radio app header + section fields)."""
    section_type: CPlaneSectionType = Field(CPlaneSectionType.MOST_DL_UL_RADIO_CHANNELS)
    section_id: int = Field(0, ge=0, le=0xFFF, description="12-bit section identifier")
    rb: int = Field(0, ge=0, le=1, description="resource block indicator (0=every RB,1=every other)")
    sym_inc: int = Field(0, ge=0, le=1, description="symbol number increment command")
    start_prbc: int = Field(0, ge=0, le=1023, description="starting PRB of control section")
    num_prbc: int = Field(0, ge=0, le=255, description="number of contiguous PRBs (0=all)")
    re_mask: int = Field(0xFFF, ge=0, le=0xFFF, description="12-bit resource-element mask")
    num_symbol: int = Field(14, ge=1, le=14, description="number of symbols this section applies to")
    frame_structure: Optional[FrameStructure] = None
    beam_id: int = Field(0, ge=0, le=0x7FFF, description="15-bit beam identifier")


# ---------------------------------------------------------------------------
# U-Plane: IQ data frame header per O-RAN.WG4.TS.CUS.0 section 6 (User Plane)
# ---------------------------------------------------------------------------
class CompressionMethod(str, Enum):
    """udCompHdr compression methods (O-RAN.WG4.TS.CUS.0-R005-v20.00 Table 6.3.3.13-3)."""
    NO_COMPRESSION = "NO_COMPRESSION"               # udCompMeth 0x0
    BLOCK_FLOATING_POINT = "BLOCK_FLOATING_POINT"   # udCompMeth 0x1 (BFP)
    BLOCK_SCALING = "BLOCK_SCALING"                 # udCompMeth 0x2
    U_LAW = "U_LAW"                                 # udCompMeth 0x3 (mu-law)
    MODULATION = "MODULATION"                       # udCompMeth 0x4 (modulation compression)


# udCompMeth numeric code lookup (used on the wire in udCompHdr)
COMPRESSION_METHOD_CODE: Dict[CompressionMethod, int] = {
    CompressionMethod.NO_COMPRESSION: 0x0,
    CompressionMethod.BLOCK_FLOATING_POINT: 0x1,
    CompressionMethod.BLOCK_SCALING: 0x2,
    CompressionMethod.U_LAW: 0x3,
    CompressionMethod.MODULATION: 0x4,
}


class PrbRange(BaseModel):
    """Physical Resource Block range carried within a U-Plane section."""
    start_prbu: int = Field(0, ge=0, le=1023, description="startPrbu: first PRB of the section")
    num_prbu: int = Field(273, ge=0, le=1023, description="numPrbu: number of PRBs (0=all to end)")


class UPlaneFrameHeader(BaseModel):
    """U-Plane IQ data frame header (transport header + application header).

    Fields frameId/subframeId/slotId/symbolId locate the IQ samples in the radio frame
    structure per O-RAN.WG4.TS.CUS.0 section 6.3.2.
    """
    frame_id: int = Field(0, ge=0, le=255, description="frameId: 8-bit radio frame number")
    subframe_id: int = Field(0, ge=0, le=15, description="subframeId: 4-bit subframe (0..9 used)")
    slot_id: int = Field(0, ge=0, le=63, description="slotId: 6-bit slot within subframe")
    symbol_id: int = Field(0, ge=0, le=13, description="symbolId: OFDM symbol (0..13)")
    data_direction: int = Field(1, ge=0, le=1, description="0=UL (RX), 1=DL (TX)")
    payload_version: int = Field(1, ge=0, le=7, description="application payload version")
    filter_index: int = Field(0, ge=0, le=15, description="filterIndex for mixed numerology/PRACH")
    section_id: int = Field(0, ge=0, le=0xFFF, description="12-bit section id matching C-Plane")
    prb_range: PrbRange = Field(default_factory=PrbRange)
    compression: CompressionMethod = Field(CompressionMethod.BLOCK_FLOATING_POINT)
    iq_bit_width: int = Field(9, ge=1, le=16, description="iqWidth: bits per I or Q sample")


# ---------------------------------------------------------------------------
# Beamforming (O-RAN.WG4.TS.CUS.0 section 7 - beamforming extensions)
# ---------------------------------------------------------------------------
class BeamWeight(BaseModel):
    """Complex beamforming weight (I/Q pair) for one antenna element."""
    re: int = Field(0, description="real (I) component of the weight, signed")
    im: int = Field(0, description="imaginary (Q) component of the weight, signed")


class BeamformingConfig(BaseModel):
    """Beamforming descriptor: beam id plus per-antenna weight vector (real-time BF, ST5/ST6)."""
    beam_id: int = Field(0, ge=0, le=0x7FFF, description="15-bit beamId")
    bf_compression: CompressionMethod = Field(CompressionMethod.BLOCK_FLOATING_POINT)
    bf_iq_width: int = Field(9, ge=1, le=16, description="bfwIqWidth: bits per BF weight sample")
    num_bf_weights: int = Field(32, ge=1, le=1024, description="number of antenna weights in vector")
    weights: List[BeamWeight] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# S-Plane: synchronization per O-RAN.WG4.TS.CUS.0 section 11 (Sync Plane)
# ---------------------------------------------------------------------------
class PtpProfile(str, Enum):
    """IEEE 1588 PTP telecom profiles referenced by O-RAN WG4 S-Plane."""
    G_8275_1 = "G.8275.1"   # full timing support from the network (Class 6, multicast L2)
    G_8275_2 = "G.8275.2"   # partial timing support (unicast over IP)


class SyncEMode(str, Enum):
    """Synchronous Ethernet frequency-sync support (ITU-T G.8262 EEC)."""
    DISABLED = "DISABLED"
    SYNCE_ENABLED = "SYNCE_ENABLED"
    ESYNCE_ENABLED = "ESYNCE_ENABLED"   # enhanced SyncE (eEEC, G.8262.1)


class LlsSyncTopology(str, Enum):
    """Lower-Layer-Split sync topologies (O-RAN.WG4.TS.CUS.0 section 11 'LLS-C' configurations)."""
    LLS_C1 = "LLS-C1"   # direct O-DU to O-RU, network timing terminates at O-DU
    LLS_C2 = "LLS-C2"   # O-DU and O-RU bridged by one or more network elements
    LLS_C3 = "LLS-C3"   # PRTC/T-GM in the fronthaul network distributes timing
    LLS_C4 = "LLS-C4"   # O-RU has a local primary reference (e.g. GNSS), no FH timing


class SyncState(str, Enum):
    """PTP/clock servo state (per IEEE 1588 and G.8275)."""
    LOCKED = "LOCKED"
    HOLDOVER = "HOLDOVER"
    FREERUN = "FREERUN"


class SyncConfig(BaseModel):
    """S-Plane configuration and live state for the O-RU clock."""
    ptp_profile: PtpProfile = Field(PtpProfile.G_8275_1)
    synce_mode: SyncEMode = Field(SyncEMode.SYNCE_ENABLED)
    lls_topology: LlsSyncTopology = Field(LlsSyncTopology.LLS_C3)
    sync_state: SyncState = Field(SyncState.LOCKED)
    clock_class: int = Field(6, ge=0, le=255, description="PTP clockClass (6=PRTC locked)")
    clock_accuracy: int = Field(0x21, description="PTP clockAccuracy (0x21 = within 100 ns)")
    # Time-error budget per O-RAN.WG4.CTI-TMP.0 / G.8273.2 Class C network limits.
    tos_category: str = Field("LLS-C3 Category-A", description="ToS time-error category")
    max_te_budget_ns: int = Field(1100, description="Time Alignment Error budget at antenna (ns)")
    measured_te_ns: int = Field(12, description="currently measured time error (ns)")


# ---------------------------------------------------------------------------
# Simulated statistics helper consumed by the O-RU FastAPI service.
# ---------------------------------------------------------------------------
class CusPlaneStats:
    """Returns simulated C/U/S-Plane statistics for the Open Fronthaul interface.

    Numbers are representative of a healthy Split-Option-7-2x link and are stable
    per process (deterministic seed) so demos read consistently.
    """

    def __init__(self, eaxc_id: int = 0, num_prb: int = 273) -> None:
        self.eaxc_id = eaxc_id
        self.num_prb = num_prb

    def c_plane_stats(self) -> Dict[str, object]:
        """Control-Plane counters: sections transmitted/received and error tallies."""
        return {
            "spec": "O-RAN.WG4.TS.CUS.0-R005-v20.00",
            "plane": "C-Plane",
            "eaxc_id": self.eaxc_id,
            "section_types_active": [
                CPlaneSectionType.MOST_DL_UL_RADIO_CHANNELS.value,
                CPlaneSectionType.UE_SCHEDULING_INFO.value,
            ],
            "rx_c_messages": 1_482_350,
            "tx_c_messages": 1_482_351,
            "rx_on_time": 1_482_180,
            "rx_early": 95,
            "rx_late": 75,
            "rx_corrupt": 0,
            "rx_total_c": 1_482_350,
            "seqid_errors": 0,
        }

    def u_plane_stats(self) -> Dict[str, object]:
        """User-Plane counters: IQ data frames, PRB throughput and window stats."""
        return {
            "spec": "O-RAN.WG4.TS.CUS.0-R005-v20.00",
            "plane": "U-Plane",
            "eaxc_id": self.eaxc_id,
            "compression": CompressionMethod.BLOCK_FLOATING_POINT.value,
            "iq_bit_width": 9,
            "num_prb": self.num_prb,
            "rx_iq_frames": 9_812_004,
            "tx_iq_frames": 9_812_010,
            "rx_window_on_time": 9_811_900,
            "rx_window_early": 60,
            "rx_window_late": 44,
            "dropped_late": 44,
            "throughput_mbps_dl": 4_812,
            "throughput_mbps_ul": 1_603,
        }

    def s_plane_stats(self) -> Dict[str, object]:
        """Sync-Plane status: PTP lock state, clock class and time-error budget."""
        cfg = SyncConfig()
        return {
            "spec": "O-RAN.WG4.TS.CUS.0-R005-v20.00 / O-RAN.WG4.CTI-TMP.0-R003-v04.00",
            "plane": "S-Plane",
            "ptp_profile": cfg.ptp_profile.value,
            "synce_mode": cfg.synce_mode.value,
            "lls_topology": cfg.lls_topology.value,
            "sync_state": cfg.sync_state.value,
            "clock_class": cfg.clock_class,
            "clock_accuracy": cfg.clock_accuracy,
            "tos_category": cfg.tos_category,
            "max_te_budget_ns": cfg.max_te_budget_ns,
            "measured_te_ns": cfg.measured_te_ns,
            "ptp_packets_rx": 2_500_311,
            "ptp_packets_lost": 0,
        }

    def all_stats(self) -> Dict[str, object]:
        """Aggregate of C/U/S plane statistics."""
        return {
            "c_plane": self.c_plane_stats(),
            "u_plane": self.u_plane_stats(),
            "s_plane": self.s_plane_stats(),
        }


def default_beamforming(num_weights: int = 32) -> BeamformingConfig:
    """Build a representative beamforming weight vector (unit-magnitude, steered)."""
    weights = [BeamWeight(re=8191, im=0) for _ in range(num_weights)]
    return BeamformingConfig(
        beam_id=1,
        bf_compression=CompressionMethod.BLOCK_FLOATING_POINT,
        bf_iq_width=9,
        num_bf_weights=num_weights,
        weights=weights,
    )


def default_uplane_header() -> UPlaneFrameHeader:
    """Build a representative DL U-Plane IQ frame header for a 100 MHz / mu=1 carrier."""
    return UPlaneFrameHeader(
        frame_id=0,
        subframe_id=0,
        slot_id=0,
        symbol_id=0,
        data_direction=1,
        prb_range=PrbRange(start_prbu=0, num_prbu=273),
        compression=CompressionMethod.BLOCK_FLOATING_POINT,
        iq_bit_width=9,
    )


__all__ = [
    "EcpriMessageType",
    "EcpriHeader",
    "CPlaneSectionType",
    "FrameStructure",
    "CPlaneSection",
    "CompressionMethod",
    "COMPRESSION_METHOD_CODE",
    "PrbRange",
    "UPlaneFrameHeader",
    "BeamWeight",
    "BeamformingConfig",
    "PtpProfile",
    "SyncEMode",
    "LlsSyncTopology",
    "SyncState",
    "SyncConfig",
    "CusPlaneStats",
    "default_beamforming",
    "default_uplane_header",
]
