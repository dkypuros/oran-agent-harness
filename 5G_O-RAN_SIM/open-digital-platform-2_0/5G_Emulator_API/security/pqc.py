# File location: 5G_Emulator_API/security/pqc.py
# O-RAN WG11 Post-Quantum Cryptography readiness library.
# Spec: O-RAN.WG11.TR.PQC-Security.0-R005-v02.00
#
# Provides a crypto-agility inventory for the emulated O-RAN deployment:
#   - classical vs PQC algorithm catalog (ML-KEM/Kyber, ML-DSA/Dilithium, SLH-DSA)
#   - per-interface crypto posture (which suite each O-RAN interface negotiates)
#   - migration-readiness scoring (how far each interface is from PQC / hybrid)
#
# Pure-Python, no third-party dependencies, import-safe.

"""Post-Quantum Cryptography readiness inventory (O-RAN.WG11.TR.PQC-Security)."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


# =============================================================================
# Enumerations
# =============================================================================

class AlgoFamily(str, Enum):
    """Cryptographic algorithm family / role."""
    KEM = "KEM"                  # key encapsulation / key establishment
    SIGNATURE = "SIGNATURE"      # digital signature
    SYMMETRIC = "SYMMETRIC"      # bulk encryption
    HASH = "HASH"                # message digest


class QuantumResistance(str, Enum):
    """Resistance of an algorithm to a cryptographically-relevant quantum computer (CRQC)."""
    CLASSICAL = "CLASSICAL"      # broken by Shor (RSA/ECC) ,  must migrate
    QUANTUM_VULNERABLE = "QUANTUM_VULNERABLE"  # weakened by Grover ,  increase key size
    QUANTUM_SAFE = "QUANTUM_SAFE"              # NIST PQC standardized / believed safe
    HYBRID = "HYBRID"            # classical + PQC combined (defense in depth)


class MigrationState(str, Enum):
    """Per-interface PQC migration lifecycle state."""
    CLASSICAL_ONLY = "CLASSICAL_ONLY"      # no PQC at all
    INVENTORIED = "INVENTORIED"            # crypto assets discovered, no change yet
    HYBRID_CAPABLE = "HYBRID_CAPABLE"      # can negotiate hybrid suites
    HYBRID_ENFORCED = "HYBRID_ENFORCED"    # hybrid mandatory
    PQC_ONLY = "PQC_ONLY"                  # fully migrated, classical disabled


# Readiness weight per migration state (0..100), used for scoring.
_MIGRATION_WEIGHT: Dict[MigrationState, int] = {
    MigrationState.CLASSICAL_ONLY: 0,
    MigrationState.INVENTORIED: 20,
    MigrationState.HYBRID_CAPABLE: 55,
    MigrationState.HYBRID_ENFORCED: 80,
    MigrationState.PQC_ONLY: 100,
}


# =============================================================================
# Algorithm catalog
# =============================================================================

class CryptoAlgorithm:
    """A single cryptographic primitive in the inventory."""

    def __init__(
        self,
        name: str,
        family: AlgoFamily,
        resistance: QuantumResistance,
        nist_level: int = 0,
        standard: str = "",
        notes: str = "",
    ) -> None:
        self.name = name
        self.family = family
        self.resistance = resistance
        self.nist_level = nist_level          # NIST PQC security category (1,3,5); 0 = n/a
        self.standard = standard              # e.g. FIPS 203 / RFC number
        self.notes = notes

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "family": self.family.value,
            "resistance": self.resistance.value,
            "nistLevel": self.nist_level,
            "standard": self.standard,
            "notes": self.notes,
        }


# Default algorithm catalog spanning classical and NIST PQC primitives.
_DEFAULT_ALGORITHMS: List[CryptoAlgorithm] = [
    # --- Classical (quantum-broken) ---
    CryptoAlgorithm("RSA-2048", AlgoFamily.SIGNATURE, QuantumResistance.CLASSICAL,
                    standard="PKCS#1 / RFC 8017", notes="Broken by Shor's algorithm"),
    CryptoAlgorithm("ECDSA-P256", AlgoFamily.SIGNATURE, QuantumResistance.CLASSICAL,
                    standard="FIPS 186-4", notes="Broken by Shor's algorithm"),
    CryptoAlgorithm("ECDHE-P256", AlgoFamily.KEM, QuantumResistance.CLASSICAL,
                    standard="RFC 8446", notes="Classical key agreement, harvest-now-decrypt-later risk"),
    # --- Symmetric / hash (quantum-weakened but usable with larger params) ---
    CryptoAlgorithm("AES-128-GCM", AlgoFamily.SYMMETRIC, QuantumResistance.QUANTUM_VULNERABLE,
                    standard="FIPS 197 / SP 800-38D", notes="Grover halves strength; prefer AES-256"),
    CryptoAlgorithm("AES-256-GCM", AlgoFamily.SYMMETRIC, QuantumResistance.QUANTUM_SAFE,
                    standard="FIPS 197 / SP 800-38D", notes="256-bit key, 128-bit post-quantum margin"),
    CryptoAlgorithm("SHA-256", AlgoFamily.HASH, QuantumResistance.QUANTUM_VULNERABLE,
                    standard="FIPS 180-4", notes="Grover reduces collision resistance; prefer SHA-384"),
    CryptoAlgorithm("SHA-384", AlgoFamily.HASH, QuantumResistance.QUANTUM_SAFE,
                    standard="FIPS 180-4", notes="Adequate post-quantum margin"),
    # --- NIST PQC standardized (quantum-safe) ---
    CryptoAlgorithm("ML-KEM-768", AlgoFamily.KEM, QuantumResistance.QUANTUM_SAFE,
                    nist_level=3, standard="FIPS 203 (Kyber)",
                    notes="Module-Lattice KEM; recommended general-purpose level"),
    CryptoAlgorithm("ML-KEM-1024", AlgoFamily.KEM, QuantumResistance.QUANTUM_SAFE,
                    nist_level=5, standard="FIPS 203 (Kyber)",
                    notes="Highest ML-KEM security category"),
    CryptoAlgorithm("ML-DSA-65", AlgoFamily.SIGNATURE, QuantumResistance.QUANTUM_SAFE,
                    nist_level=3, standard="FIPS 204 (Dilithium)",
                    notes="Module-Lattice digital signature"),
    CryptoAlgorithm("ML-DSA-87", AlgoFamily.SIGNATURE, QuantumResistance.QUANTUM_SAFE,
                    nist_level=5, standard="FIPS 204 (Dilithium)",
                    notes="Highest ML-DSA security category"),
    CryptoAlgorithm("SLH-DSA-SHA2-128s", AlgoFamily.SIGNATURE, QuantumResistance.QUANTUM_SAFE,
                    nist_level=1, standard="FIPS 205 (SPHINCS+)",
                    notes="Stateless hash-based signature; conservative, no lattice assumption"),
    # --- Hybrid suites (classical + PQC) ---
    CryptoAlgorithm("X25519+ML-KEM-768", AlgoFamily.KEM, QuantumResistance.HYBRID,
                    nist_level=3, standard="draft-ietf-tls-hybrid-design",
                    notes="Hybrid TLS 1.3 key exchange, recommended migration target"),
]


# =============================================================================
# Per-interface crypto posture
# =============================================================================

class InterfaceCryptoPosture:
    """Crypto posture negotiated on a single O-RAN interface."""

    def __init__(
        self,
        interface: str,
        kem: str,
        signature: str,
        symmetric: str,
        migration_state: MigrationState,
        transport: str = "TLS 1.3",
    ) -> None:
        self.interface = interface
        self.kem = kem
        self.signature = signature
        self.symmetric = symmetric
        self.migration_state = migration_state
        self.transport = transport

    def to_dict(self) -> Dict[str, Any]:
        return {
            "interface": self.interface,
            "transport": self.transport,
            "kem": self.kem,
            "signature": self.signature,
            "symmetric": self.symmetric,
            "migrationState": self.migration_state.value,
            "readinessScore": _MIGRATION_WEIGHT[self.migration_state],
        }


# Default per-interface posture across the canonical O-RAN interface set.
_DEFAULT_POSTURE: List[InterfaceCryptoPosture] = [
    InterfaceCryptoPosture("E2", "ECDHE-P256", "ECDSA-P256", "AES-256-GCM",
                           MigrationState.INVENTORIED),
    InterfaceCryptoPosture("A1", "X25519+ML-KEM-768", "ML-DSA-65", "AES-256-GCM",
                           MigrationState.HYBRID_CAPABLE),
    InterfaceCryptoPosture("O1", "X25519+ML-KEM-768", "ECDSA-P256", "AES-256-GCM",
                           MigrationState.HYBRID_CAPABLE),
    InterfaceCryptoPosture("O2", "X25519+ML-KEM-768", "ML-DSA-65", "AES-256-GCM",
                           MigrationState.HYBRID_ENFORCED),
    InterfaceCryptoPosture("R1", "ECDHE-P256", "ECDSA-P256", "AES-256-GCM",
                           MigrationState.INVENTORIED),
    InterfaceCryptoPosture("Open FH M-Plane", "ECDHE-P256", "RSA-2048", "AES-256-GCM",
                           MigrationState.CLASSICAL_ONLY, transport="TLS 1.2/SSH"),
    InterfaceCryptoPosture("Y1", "ECDHE-P256", "ECDSA-P256", "AES-256-GCM",
                           MigrationState.INVENTORIED),
]


# =============================================================================
# Inventory
# =============================================================================

class PqcInventory:
    """Crypto-agility inventory and PQC migration-readiness scorer.

    Holds the algorithm catalog plus per-interface posture, and computes an
    aggregate migration-readiness score per O-RAN.WG11.TR.PQC-Security.
    """

    SPEC = "O-RAN.WG11.TR.PQC-Security.0-R005-v02.00"

    def __init__(self) -> None:
        self.algorithms: List[CryptoAlgorithm] = list(_DEFAULT_ALGORITHMS)
        self.postures: List[InterfaceCryptoPosture] = list(_DEFAULT_POSTURE)

    # --- algorithm catalog -------------------------------------------------

    def list_algorithms(self, resistance: Optional[QuantumResistance] = None) -> List[Dict[str, Any]]:
        algos = self.algorithms
        if resistance is not None:
            algos = [a for a in algos if a.resistance == resistance]
        return [a.to_dict() for a in algos]

    def quantum_vulnerable_algorithms(self) -> List[Dict[str, Any]]:
        """Algorithms that must migrate (classical) or be strengthened (quantum-vulnerable)."""
        vuln = (QuantumResistance.CLASSICAL, QuantumResistance.QUANTUM_VULNERABLE)
        return [a.to_dict() for a in self.algorithms if a.resistance in vuln]

    # --- interface posture -------------------------------------------------

    def list_postures(self) -> List[Dict[str, Any]]:
        return [p.to_dict() for p in self.postures]

    def get_posture(self, interface: str) -> Optional[Dict[str, Any]]:
        for p in self.postures:
            if p.interface.lower() == interface.lower():
                return p.to_dict()
        return None

    def set_migration_state(self, interface: str, state: MigrationState) -> bool:
        for p in self.postures:
            if p.interface.lower() == interface.lower():
                p.migration_state = state
                return True
        return False

    # --- scoring -----------------------------------------------------------

    def readiness_score(self) -> int:
        """Aggregate migration-readiness score (0..100) across all interfaces."""
        if not self.postures:
            return 0
        total = sum(_MIGRATION_WEIGHT[p.migration_state] for p in self.postures)
        return round(total / len(self.postures))

    def readiness_level(self) -> str:
        """Human-readable readiness band."""
        score = self.readiness_score()
        if score >= 80:
            return "PQC_READY"
        if score >= 50:
            return "HYBRID_IN_PROGRESS"
        if score >= 20:
            return "INVENTORY_COMPLETE"
        return "NOT_STARTED"

    def summary(self) -> Dict[str, Any]:
        """Compact inventory summary suitable for a security-posture aggregate."""
        by_resistance: Dict[str, int] = {}
        for a in self.algorithms:
            by_resistance[a.resistance.value] = by_resistance.get(a.resistance.value, 0) + 1
        return {
            "spec": self.SPEC,
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "algorithmCount": len(self.algorithms),
            "algorithmsByResistance": by_resistance,
            "quantumVulnerableCount": len(self.quantum_vulnerable_algorithms()),
            "interfaceCount": len(self.postures),
            "readinessScore": self.readiness_score(),
            "readinessLevel": self.readiness_level(),
            "interfaces": self.list_postures(),
        }
