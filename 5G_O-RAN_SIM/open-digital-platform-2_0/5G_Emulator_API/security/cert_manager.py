# File location: 5G_Emulator_API/security/cert_manager.py
# O-RAN WG11 Certificate Management Framework library.
# Spec: O-RAN.WG11.TR.Certficate-Management-Framework.0-R005-v06.00
#
# Simulated CMPv2-style X.509 identity lifecycle for O-RAN network functions:
#   - per-NF identity (one operational cert per NF)
#   - certificate entries: subject, issuer, serial, notBefore/notAfter, status
#   - issuance, rotation/renewal, and revocation
#
# If the `cryptography` package is importable, a real self-signed X.509 cert is
# generated (PEM captured); otherwise issuance is fully simulated. The import is
# wrapped in try/except so this module is always import-safe.

"""CMPv2-style X.509 identity issuance and rotation (O-RAN.WG11 Cert Mgmt Framework)."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

# Optional real-crypto backend. Never let an import failure break the module.
try:  # pragma: no cover - environment dependent
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    _HAS_CRYPTO = True
except Exception:  # pragma: no cover
    _HAS_CRYPTO = False


# =============================================================================
# Enumerations
# =============================================================================

class CertStatus(str, Enum):
    """X.509 certificate lifecycle status."""
    VALID = "VALID"
    EXPIRING = "EXPIRING"          # within the renewal window
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"
    SUPERSEDED = "SUPERSEDED"      # replaced by a newer cert during rotation


class CertProfile(str, Enum):
    """O-RAN certificate profile (intended usage of the identity)."""
    OPERATOR_ROOT_CA = "OPERATOR_ROOT_CA"
    OPERATOR_SUB_CA = "OPERATOR_SUB_CA"
    NF_TLS_SERVER = "NF_TLS_SERVER"
    NF_TLS_CLIENT = "NF_TLS_CLIENT"
    NF_IDENTITY = "NF_IDENTITY"    # generic per-NF operational identity


# =============================================================================
# Certificate entry
# =============================================================================

class CertEntry:
    """A single X.509 certificate entry in the simulated PKI."""

    def __init__(
        self,
        nf_id: str,
        subject: str,
        issuer: str,
        serial: str,
        not_before: datetime,
        not_after: datetime,
        profile: CertProfile = CertProfile.NF_IDENTITY,
        status: CertStatus = CertStatus.VALID,
        pem: Optional[str] = None,
        backend: str = "simulated",
    ) -> None:
        self.nf_id = nf_id
        self.subject = subject
        self.issuer = issuer
        self.serial = serial
        self.not_before = not_before
        self.not_after = not_after
        self.profile = profile
        self.status = status
        self.pem = pem
        self.backend = backend           # "cryptography" or "simulated"

    def evaluate_status(self, renew_window_days: int = 30) -> CertStatus:
        """Recompute time-based status unless revoked/superseded (terminal-ish)."""
        if self.status in (CertStatus.REVOKED, CertStatus.SUPERSEDED):
            return self.status
        now = datetime.now(timezone.utc)
        if now >= self.not_after:
            self.status = CertStatus.EXPIRED
        elif now >= self.not_after - timedelta(days=renew_window_days):
            self.status = CertStatus.EXPIRING
        else:
            self.status = CertStatus.VALID
        return self.status

    def to_dict(self) -> Dict[str, Any]:
        return {
            "nfId": self.nf_id,
            "subject": self.subject,
            "issuer": self.issuer,
            "serialNumber": self.serial,
            "notBefore": self.not_before.isoformat(),
            "notAfter": self.not_after.isoformat(),
            "profile": self.profile.value,
            "status": self.status.value,
            "backend": self.backend,
            "hasPem": self.pem is not None,
        }


# =============================================================================
# Certificate manager
# =============================================================================

class CertManager:
    """Simulated CMPv2 certificate authority for O-RAN network functions.

    Maintains one active operational identity per NF plus a full history of
    superseded/revoked entries. Issuance uses the `cryptography` package when
    available (real self-signed X.509), otherwise it is fully simulated.
    """

    SPEC = "O-RAN.WG11.TR.Certficate-Management-Framework.0-R005-v06.00"

    def __init__(
        self,
        issuer_cn: str = "O-RAN Operator Issuing CA",
        org: str = "O-RAN-Emulator",
        validity_days: int = 365,
        renew_window_days: int = 30,
    ) -> None:
        self.issuer = f"CN={issuer_cn},O={org}"
        self.org = org
        self.validity_days = validity_days
        self.renew_window_days = renew_window_days
        # active[nf_id] -> CertEntry ; history -> all superseded/revoked entries
        self._active: Dict[str, CertEntry] = {}
        self._history: List[CertEntry] = []

    # --- helpers -----------------------------------------------------------

    @staticmethod
    def _new_serial() -> str:
        # 16 hex bytes, CMP/X.509-style positive serial number.
        return secrets.token_hex(16)

    def _build_real_cert(self, subject_cn: str, not_before: datetime,
                         not_after: datetime, serial_int: int) -> Optional[str]:
        """Generate a real self-signed X.509 cert PEM, or None on any failure."""
        if not _HAS_CRYPTO:
            return None
        try:  # pragma: no cover - depends on optional backend
            key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            name = x509.Name([
                x509.NameAttribute(NameOID.COMMON_NAME, subject_cn),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, self.org),
            ])
            cert = (
                x509.CertificateBuilder()
                .subject_name(name)
                .issuer_name(name)
                .public_key(key.public_key())
                .serial_number(serial_int)
                .not_valid_before(not_before)
                .not_valid_after(not_after)
                .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
                .sign(key, hashes.SHA256())
            )
            return cert.public_bytes(serialization.Encoding.PEM).decode("ascii")
        except Exception:
            return None

    # --- issuance / rotation ----------------------------------------------

    def issue(
        self,
        nf_id: str,
        subject_cn: Optional[str] = None,
        profile: CertProfile = CertProfile.NF_IDENTITY,
        validity_days: Optional[int] = None,
    ) -> CertEntry:
        """Issue (or re-issue) the operational identity for an NF.

        Any existing active entry for the NF is moved to history as SUPERSEDED.
        """
        subject_cn = subject_cn or f"{nf_id}.nf.oran.local"
        subject = f"CN={subject_cn},O={self.org}"
        days = validity_days if validity_days is not None else self.validity_days
        not_before = datetime.now(timezone.utc)
        not_after = not_before + timedelta(days=days)
        serial = self._new_serial()
        pem = self._build_real_cert(subject_cn, not_before, not_after, int(serial, 16))
        backend = "cryptography" if pem is not None else "simulated"

        # Supersede any current active cert for this NF.
        prev = self._active.get(nf_id)
        if prev is not None:
            prev.status = CertStatus.SUPERSEDED
            self._history.append(prev)

        entry = CertEntry(
            nf_id=nf_id,
            subject=subject,
            issuer=self.issuer,
            serial=serial,
            not_before=not_before,
            not_after=not_after,
            profile=profile,
            status=CertStatus.VALID,
            pem=pem,
            backend=backend,
        )
        self._active[nf_id] = entry
        return entry

    def rotate(self, nf_id: str) -> CertEntry:
        """Rotate (renew) an NF identity. Issues a fresh cert with the same profile."""
        current = self._active.get(nf_id)
        if current is None:
            raise KeyError(f"No active certificate for NF '{nf_id}'")
        return self.issue(nf_id, profile=current.profile)

    def revoke(self, nf_id: str, reason: str = "unspecified") -> bool:
        """Revoke the active identity for an NF and move it to history."""
        entry = self._active.pop(nf_id, None)
        if entry is None:
            return False
        entry.status = CertStatus.REVOKED
        self._history.append(entry)
        return True

    # --- queries -----------------------------------------------------------

    def get(self, nf_id: str) -> Optional[CertEntry]:
        entry = self._active.get(nf_id)
        if entry is not None:
            entry.evaluate_status(self.renew_window_days)
        return entry

    def get_pem(self, nf_id: str) -> Optional[str]:
        entry = self._active.get(nf_id)
        return entry.pem if entry else None

    def list_active(self) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for entry in self._active.values():
            entry.evaluate_status(self.renew_window_days)
            out.append(entry.to_dict())
        return out

    def list_all(self) -> List[Dict[str, Any]]:
        active = self.list_active()
        history = [e.to_dict() for e in self._history]
        return active + history

    def certificates_needing_rotation(self) -> List[Dict[str, Any]]:
        """Active certs that are EXPIRING or EXPIRED and should be rotated."""
        flagged = (CertStatus.EXPIRING, CertStatus.EXPIRED)
        out: List[Dict[str, Any]] = []
        for entry in self._active.values():
            if entry.evaluate_status(self.renew_window_days) in flagged:
                out.append(entry.to_dict())
        return out

    def summary(self) -> Dict[str, Any]:
        """Compact PKI summary suitable for a security-posture aggregate."""
        by_status: Dict[str, int] = {}
        for entry in self._active.values():
            st = entry.evaluate_status(self.renew_window_days).value
            by_status[st] = by_status.get(st, 0) + 1
        return {
            "spec": self.SPEC,
            "issuer": self.issuer,
            "cryptoBackend": "cryptography" if _HAS_CRYPTO else "simulated",
            "activeCount": len(self._active),
            "historyCount": len(self._history),
            "activeByStatus": by_status,
            "needsRotation": len(self.certificates_needing_rotation()),
        }
