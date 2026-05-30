# File location: 5G_Emulator_API/security/zero_trust.py
# O-RAN WG11 Zero-Trust Architecture + Threat Modeling library.
# Specs: O-RAN.WG11.TR.ZTA-R005-v05.00
#        O-RAN.WG11.TR.Threat-Modeling-R005-v08.00
#
# Provides:
#   - per-interface trust evaluation (identity, posture, policy signals)
#   - a threat-surface map across the O-RAN interfaces
#     (E2, A1, O1, O2, R1, Open FH, Y1)
#   - a policy decision point (PDP): evaluate(request_ctx) -> ALLOW / DENY + reason
#
# Pure-Python, import-safe, no third-party dependencies.

"""Zero-Trust Architecture engine and O-RAN threat-surface map (O-RAN.WG11)."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum, IntEnum
from typing import Any, Dict, List, Optional


# =============================================================================
# Enumerations
# =============================================================================

class TrustLevel(IntEnum):
    """Computed trust level for a subject/interface (higher = more trusted)."""
    UNTRUSTED = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    VERIFIED = 4


class Decision(str, Enum):
    """Policy decision point verdict."""
    ALLOW = "ALLOW"
    DENY = "DENY"


class OranInterface(str, Enum):
    """Canonical O-RAN interfaces in scope for zero-trust evaluation."""
    E2 = "E2"
    A1 = "A1"
    O1 = "O1"
    O2 = "O2"
    R1 = "R1"
    OPEN_FH = "Open FH"
    Y1 = "Y1"


class ThreatSeverity(str, Enum):
    """STRIDE-style threat severity (aligned with O-RAN threat modeling)."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


# =============================================================================
# Threat-surface map
# =============================================================================

class ThreatEntry:
    """A single threat associated with an O-RAN interface."""

    def __init__(
        self,
        interface: OranInterface,
        threat_id: str,
        category: str,         # STRIDE category
        description: str,
        severity: ThreatSeverity,
        mitigation: str,
    ) -> None:
        self.interface = interface
        self.threat_id = threat_id
        self.category = category
        self.description = description
        self.severity = severity
        self.mitigation = mitigation

    def to_dict(self) -> Dict[str, Any]:
        return {
            "interface": self.interface.value,
            "threatId": self.threat_id,
            "strideCategory": self.category,
            "description": self.description,
            "severity": self.severity.value,
            "mitigation": self.mitigation,
        }


# O-RAN interface threat surface (subset, per WG11 threat modeling).
_THREAT_SURFACE: List[ThreatEntry] = [
    ThreatEntry(OranInterface.E2, "T-E2-01", "Tampering",
                "E2 control message manipulation alters RAN control decisions",
                ThreatSeverity.HIGH, "mTLS on E2, message integrity, RIC authz"),
    ThreatEntry(OranInterface.E2, "T-E2-02", "DoS",
                "E2 subscription flooding exhausts E2 termination resources",
                ThreatSeverity.MEDIUM, "Rate limiting, subscription quotas"),
    ThreatEntry(OranInterface.A1, "T-A1-01", "Tampering",
                "A1 policy injection forces unsafe RAN behavior via Near-RT RIC",
                ThreatSeverity.HIGH, "Policy schema validation, signed policies, OAuth2 scopes"),
    ThreatEntry(OranInterface.A1, "T-A1-02", "Spoofing",
                "Rogue rApp impersonates Non-RT RIC on A1",
                ThreatSeverity.HIGH, "mTLS client auth, token introspection"),
    ThreatEntry(OranInterface.O1, "T-O1-01", "Elevation of Privilege",
                "O1/NETCONF management session hijack grants config control",
                ThreatSeverity.CRITICAL, "SSH/TLS, NACM role-based access, session binding"),
    ThreatEntry(OranInterface.O1, "T-O1-02", "Information Disclosure",
                "O1 PM/FM data exfiltration leaks topology and KPIs",
                ThreatSeverity.MEDIUM, "TLS, least-privilege NACM, audit logging"),
    ThreatEntry(OranInterface.O2, "T-O2-01", "Tampering",
                "O2 deployment descriptor tampering injects malicious workloads",
                ThreatSeverity.CRITICAL, "Signed artifacts, admission control, mTLS"),
    ThreatEntry(OranInterface.R1, "T-R1-01", "Spoofing",
                "Unauthorized rApp consumes R1 data services / registers fake services",
                ThreatSeverity.MEDIUM, "Service auth, R1 token validation"),
    ThreatEntry(OranInterface.OPEN_FH, "T-FH-01", "DoS",
                "Open Fronthaul C/U-plane flooding disrupts radio scheduling",
                ThreatSeverity.HIGH, "MACsec/IEEE 802.1X, ingress filtering, S-plane PTP auth"),
    ThreatEntry(OranInterface.OPEN_FH, "T-FH-02", "Spoofing",
                "Rogue O-RU/O-DU on M-plane via weak credentials",
                ThreatSeverity.HIGH, "M-plane TLS/SSH, certificate-based O-RU onboarding"),
    ThreatEntry(OranInterface.Y1, "T-Y1-01", "Information Disclosure",
                "Y1 RAI consumer leaks analytics about subscribers/cells",
                ThreatSeverity.LOW, "OAuth2 scopes, data minimization"),
]


# Baseline static interface trust posture (defense-in-depth assumption).
_BASELINE_TRUST: Dict[OranInterface, TrustLevel] = {
    OranInterface.E2: TrustLevel.MEDIUM,
    OranInterface.A1: TrustLevel.MEDIUM,
    OranInterface.O1: TrustLevel.HIGH,
    OranInterface.O2: TrustLevel.HIGH,
    OranInterface.R1: TrustLevel.MEDIUM,
    OranInterface.OPEN_FH: TrustLevel.LOW,
    OranInterface.Y1: TrustLevel.LOW,
}


# =============================================================================
# Zero-Trust engine (policy decision point)
# =============================================================================

class ZeroTrustEngine:
    """Zero-Trust policy decision point for O-RAN interfaces.

    Implements the ZTA tenets of "never trust, always verify": every request is
    scored on identity, device/workload posture, and policy signals, then a
    trust level is derived and an ALLOW/DENY decision returned with a reason.
    """

    SPEC = "O-RAN.WG11.TR.ZTA-R005-v05.00"
    THREAT_SPEC = "O-RAN.WG11.TR.Threat-Modeling-R005-v08.00"

    # Minimum trust level required to allow access (per the "verify explicitly" tenet).
    MIN_TRUST_TO_ALLOW = TrustLevel.MEDIUM

    def __init__(self) -> None:
        self.threats: List[ThreatEntry] = list(_THREAT_SURFACE)
        self.baseline_trust: Dict[OranInterface, TrustLevel] = dict(_BASELINE_TRUST)

    # --- trust scoring -----------------------------------------------------

    @staticmethod
    def _score_signals(ctx: Dict[str, Any]) -> int:
        """Convert request signals into an additive trust score (0..4)."""
        score = 0
        # Identity: authenticated subject with a valid token/cert.
        if ctx.get("authenticated") is True:
            score += 1
        if ctx.get("mtls") is True or ctx.get("client_cert_valid") is True:
            score += 1
        # Posture: workload/device attestation healthy.
        posture = str(ctx.get("posture", "")).lower()
        if posture in ("healthy", "compliant", "attested"):
            score += 1
        # Policy: request carries an allowed scope/role for the action.
        scopes = ctx.get("scopes") or []
        required = ctx.get("required_scope")
        if required is None or required in scopes:
            score += 1
        return score

    def evaluate_interface(self, interface: OranInterface, ctx: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Evaluate the effective trust level for a given interface + context."""
        ctx = ctx or {}
        signal_score = self._score_signals(ctx)
        # Effective trust blends static baseline with dynamic signals (capped).
        baseline = int(self.baseline_trust.get(interface, TrustLevel.LOW))
        effective = min(int(TrustLevel.VERIFIED), max(baseline, signal_score))
        level = TrustLevel(effective)
        return {
            "interface": interface.value,
            "baselineTrust": self.baseline_trust.get(interface, TrustLevel.LOW).name,
            "signalScore": signal_score,
            "trustLevel": level.name,
            "trustValue": int(level),
        }

    # --- policy decision point --------------------------------------------

    def evaluate(self, request_ctx: Dict[str, Any]) -> Dict[str, Any]:
        """Policy decision point. Returns ALLOW/DENY + reason for a request.

        Expected keys in request_ctx (all optional, sane defaults applied):
          interface       : O-RAN interface name (e.g. "E2", "A1", "O1")
          subject         : subject/NF identifier requesting access
          action          : requested action (e.g. "read", "write", "subscribe")
          authenticated   : bool, identity was authenticated
          mtls            : bool, mutual TLS established
          client_cert_valid : bool, presented client cert is valid
          posture         : "healthy" | "compromised" | ...
          scopes          : list of granted OAuth2 scopes
          required_scope  : scope needed for the action
        """
        iface_name = str(request_ctx.get("interface", "")).strip()
        subject = request_ctx.get("subject", "anonymous")
        action = request_ctx.get("action", "access")

        # Resolve interface enum (unknown interface -> implicit deny).
        interface = self._resolve_interface(iface_name)
        if interface is None:
            return self._decision(Decision.DENY, TrustLevel.UNTRUSTED, subject, action,
                                  iface_name, f"Unknown interface '{iface_name}'")

        # Hard denials per zero-trust tenets.
        if request_ctx.get("authenticated") is not True:
            return self._decision(Decision.DENY, TrustLevel.UNTRUSTED, subject, action,
                                  interface.value, "Subject not authenticated (identity unverified)")
        if str(request_ctx.get("posture", "")).lower() in ("compromised", "quarantined", "noncompliant"):
            return self._decision(Decision.DENY, TrustLevel.UNTRUSTED, subject, action,
                                  interface.value, "Device/workload posture is not compliant")

        evaluation = self.evaluate_interface(interface, request_ctx)
        level = TrustLevel(evaluation["trustValue"])

        if level < self.MIN_TRUST_TO_ALLOW:
            return self._decision(Decision.DENY, level, subject, action, interface.value,
                                  f"Trust level {level.name} below minimum "
                                  f"{self.MIN_TRUST_TO_ALLOW.name}")

        # Scope/policy enforcement for the requested action.
        required = request_ctx.get("required_scope")
        scopes = request_ctx.get("scopes") or []
        if required is not None and required not in scopes:
            return self._decision(Decision.DENY, level, subject, action, interface.value,
                                  f"Missing required scope '{required}'")

        return self._decision(Decision.ALLOW, level, subject, action, interface.value,
                              "Identity, posture, and policy verified")

    # --- threat surface ----------------------------------------------------

    def threat_model(self, interface: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return the threat-surface map, optionally filtered by interface."""
        if interface:
            iface = self._resolve_interface(interface)
            if iface is None:
                return []
            return [t.to_dict() for t in self.threats if t.interface == iface]
        return [t.to_dict() for t in self.threats]

    # --- helpers -----------------------------------------------------------

    @staticmethod
    def _resolve_interface(name: str) -> Optional[OranInterface]:
        norm = name.strip().lower().replace("_", " ")
        for iface in OranInterface:
            if iface.value.lower() == norm or iface.name.lower() == name.strip().lower():
                return iface
        # tolerate "openfh"/"open-fh"/"fh"
        if norm in ("open fh", "openfh", "open-fh", "fh", "fronthaul"):
            return OranInterface.OPEN_FH
        return None

    @staticmethod
    def _decision(decision: Decision, level: TrustLevel, subject: Any, action: Any,
                  interface: str, reason: str) -> Dict[str, Any]:
        return {
            "decision": decision.value,
            "subject": subject,
            "action": action,
            "interface": interface,
            "trustLevel": level.name,
            "reason": reason,
            "evaluatedAt": datetime.now(timezone.utc).isoformat(),
        }

    def summary(self) -> Dict[str, Any]:
        """Compact ZTA summary suitable for a security-posture aggregate."""
        by_severity: Dict[str, int] = {}
        for t in self.threats:
            by_severity[t.severity.value] = by_severity.get(t.severity.value, 0) + 1
        return {
            "spec": self.SPEC,
            "threatSpec": self.THREAT_SPEC,
            "model": "never-trust-always-verify",
            "minTrustToAllow": self.MIN_TRUST_TO_ALLOW.name,
            "interfaceBaselines": {
                iface.value: lvl.name for iface, lvl in self.baseline_trust.items()
            },
            "threatCount": len(self.threats),
            "threatsBySeverity": by_severity,
        }
