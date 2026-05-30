#!/usr/bin/env python3
"""O-RAN WG11 Security Service.

Spec: O-RAN.WG11.TS.SecProtSpec.0-R005-v14.00 (Security Protocols),
      O-RAN.WG11.TS.SRCS.0-R005-v14.00 (Security Requirements & Controls),
      O-RAN.WG11.TS.STS-R005-v12.00 (Security Test Specifications).

Provides the emulated O-RAN security control plane:
  - OAuth2 client-credentials token endpoint + token introspection
  - aggregate security posture (ZeroTrust + PQC + certificate summary)
  - SRCS security-control catalog with status
  - O-RAN threat-surface model
  - security event log
  - certificate inventory (CMPv2-style)

Wires in ZeroTrustEngine, PqcInventory, and CertManager from the sibling libs.

Port: 8128
"""
import argparse, logging, uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
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

# Sibling security libraries (relative import with absolute fallback).
try:
    from .pqc import PqcInventory
    from .cert_manager import CertManager, CertProfile
    from .zero_trust import ZeroTrustEngine
except Exception:  # pragma: no cover - allow running as a loose script
    from pqc import PqcInventory  # type: ignore
    from cert_manager import CertManager, CertProfile  # type: ignore
    from zero_trust import ZeroTrustEngine  # type: ignore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("svc")

SERVICE_PORT = 8128
NRF_URL = "http://127.0.0.1:8000"


def _now() -> datetime:
    return datetime.now(timezone.utc)


# =============================================================================
# Wired-in security engines
# =============================================================================

PQC = PqcInventory()
CERTS = CertManager()
ZTA = ZeroTrustEngine()

# Seed a few per-NF identities so /security/certificates is non-empty.
for _nf, _profile in (
    ("near-rt-ric", CertProfile.NF_TLS_SERVER),
    ("non-rt-ric", CertProfile.NF_TLS_SERVER),
    ("o-du", CertProfile.NF_IDENTITY),
    ("o-cu", CertProfile.NF_IDENTITY),
    ("smo", CertProfile.NF_TLS_SERVER),
):
    CERTS.issue(_nf, profile=_profile)


# =============================================================================
# In-memory OAuth2 client registry + token store
# =============================================================================

# Pre-registered confidential clients (client_id -> record).
_CLIENT_REGISTRY: Dict[str, Dict[str, Any]] = {
    "near-rt-ric": {"client_secret": "ric-secret", "scopes": ["a1.policy", "e2.subscribe", "security.read"]},
    "smo": {"client_secret": "smo-secret", "scopes": ["o1.config", "o2.deploy", "security.read", "security.write"]},
    "rapp-analytics": {"client_secret": "rapp-secret", "scopes": ["r1.data", "y1.rai"]},
}

# Issued tokens (access_token -> metadata).
_TOKEN_STORE: Dict[str, Dict[str, Any]] = {}

# Security event log (newest appended last).
_EVENT_LOG: List[Dict[str, Any]] = []

TOKEN_TTL_SECONDS = 3600


# =============================================================================
# SRCS security-control catalog (O-RAN.WG11.TS.SRCS)
# =============================================================================

_SECURITY_CONTROLS: List[Dict[str, Any]] = [
    {"id": "SEC-AUTH-01", "family": "Authentication",
     "title": "Mutual TLS on all O-RAN interfaces", "status": "ENFORCED",
     "reference": "SecProtSpec 5.x"},
    {"id": "SEC-AUTH-02", "family": "Authorization",
     "title": "OAuth2 client-credentials with least-privilege scopes", "status": "ENFORCED",
     "reference": "SRCS"},
    {"id": "SEC-CRYP-01", "family": "Cryptography",
     "title": "TLS 1.3 with AEAD ciphers (AES-256-GCM)", "status": "ENFORCED",
     "reference": "SecProtSpec"},
    {"id": "SEC-CRYP-02", "family": "Cryptography",
     "title": "PQC / hybrid key establishment migration", "status": "IN_PROGRESS",
     "reference": "PQC-Security TR"},
    {"id": "SEC-PKI-01", "family": "PKI",
     "title": "CMPv2 automated certificate enrollment and rotation", "status": "ENFORCED",
     "reference": "Cert-Mgmt-Framework TR"},
    {"id": "SEC-ZTA-01", "family": "Zero Trust",
     "title": "Per-request policy decision point (never trust, always verify)", "status": "ENFORCED",
     "reference": "ZTA TR"},
    {"id": "SEC-LOG-01", "family": "Logging",
     "title": "Tamper-evident security event logging", "status": "ENFORCED",
     "reference": "SRCS"},
    {"id": "SEC-FH-01", "family": "Fronthaul",
     "title": "MACsec / 802.1X on Open Fronthaul C/U/S-plane", "status": "PLANNED",
     "reference": "SecProtSpec"},
]


# =============================================================================
# Pydantic models
# =============================================================================

class TokenRequest(BaseModel):
    grant_type: str = Field(default="client_credentials")
    client_id: str
    client_secret: str
    scope: Optional[str] = None


class IntrospectRequest(BaseModel):
    token: str


class SecurityEvent(BaseModel):
    event_type: str = Field(..., description="e.g. AUTH_FAILURE, POLICY_DENY, CERT_ROTATED")
    severity: str = Field(default="INFO", description="INFO|WARNING|CRITICAL")
    source: str = Field(default="unknown", description="originating NF / interface")
    interface: Optional[str] = Field(default=None, description="O-RAN interface, if applicable")
    message: str = Field(default="")
    details: Optional[Dict[str, Any]] = None


# =============================================================================
# Lifespan / app
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        requests.post(
            f"{NRF_URL}/register",
            json={"nf_type": "SEC", "ip": "127.0.0.1", "port": SERVICE_PORT},
            timeout=3,
        )
        logger.info("Security service registered with NRF")
    except requests.RequestException:
        logger.warning("Could not register security service with NRF")
    yield


app = FastAPI(
    title="O-RAN WG11 Security Service",
    description="OAuth2, security posture, SRCS controls, threat model, certificates (port 8128)",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# =============================================================================
# Helpers
# =============================================================================

def _log_event(event_type: str, severity: str, source: str,
               message: str, interface: Optional[str] = None,
               details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    entry = {
        "id": str(uuid.uuid4()),
        "timestamp": _now().isoformat(),
        "eventType": event_type,
        "severity": severity,
        "source": source,
        "interface": interface,
        "message": message,
        "details": details or {},
    }
    _EVENT_LOG.append(entry)
    return entry


# =============================================================================
# OAuth2 (O-RAN.WG11.TS.SecProtSpec)
# =============================================================================

@app.post("/oauth2/token")
async def oauth2_token(req: TokenRequest):
    """OAuth2 client-credentials grant -> returns a bearer token."""
    with _tracer.start_as_current_span("oauth2_token"):
        if req.grant_type != "client_credentials":
            raise HTTPException(status_code=400, detail="unsupported_grant_type")
        client = _CLIENT_REGISTRY.get(req.client_id)
        if client is None or client["client_secret"] != req.client_secret:
            _log_event("AUTH_FAILURE", "WARNING", req.client_id,
                       "Invalid client credentials")
            raise HTTPException(status_code=401, detail="invalid_client")

        granted = client["scopes"]
        if req.scope:
            requested = req.scope.split()
            granted = [s for s in requested if s in client["scopes"]]
            if not granted:
                raise HTTPException(status_code=400, detail="invalid_scope")

        access_token = uuid.uuid4().hex + uuid.uuid4().hex
        expires_at = _now() + timedelta(seconds=TOKEN_TTL_SECONDS)
        _TOKEN_STORE[access_token] = {
            "client_id": req.client_id,
            "scopes": granted,
            "issued_at": _now().isoformat(),
            "expires_at": expires_at.isoformat(),
        }
        _log_event("TOKEN_ISSUED", "INFO", req.client_id,
                   f"Issued token with scopes {granted}")
        return {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": TOKEN_TTL_SECONDS,
            "scope": " ".join(granted),
        }


@app.post("/oauth2/introspect")
async def oauth2_introspect(req: IntrospectRequest):
    """RFC 7662-style token introspection."""
    meta = _TOKEN_STORE.get(req.token)
    if meta is None:
        return {"active": False}
    expires_at = datetime.fromisoformat(meta["expires_at"])
    if _now() >= expires_at:
        _TOKEN_STORE.pop(req.token, None)
        return {"active": False}
    return {
        "active": True,
        "client_id": meta["client_id"],
        "scope": " ".join(meta["scopes"]),
        "exp": int(expires_at.timestamp()),
    }


# =============================================================================
# Security posture / controls / threat model
# =============================================================================

@app.get("/security/posture")
async def security_posture():
    """Aggregate security posture: ZeroTrust + PQC + certificate summary."""
    with _tracer.start_as_current_span("security_posture"):
        controls_total = len(_SECURITY_CONTROLS)
        controls_enforced = sum(1 for c in _SECURITY_CONTROLS if c["status"] == "ENFORCED")
        return {
            "generatedAt": _now().isoformat(),
            "spec": "O-RAN.WG11.TS.SRCS.0-R005-v14.00",
            "zeroTrust": ZTA.summary(),
            "pqc": PQC.summary(),
            "certificates": CERTS.summary(),
            "controls": {
                "total": controls_total,
                "enforced": controls_enforced,
                "coveragePct": round(100 * controls_enforced / controls_total) if controls_total else 0,
            },
            "securityEvents": len(_EVENT_LOG),
        }


@app.get("/security/controls")
async def security_controls(status: Optional[str] = None, family: Optional[str] = None):
    """SRCS control catalog with status (O-RAN.WG11.TS.SRCS)."""
    controls = _SECURITY_CONTROLS
    if status:
        controls = [c for c in controls if c["status"].upper() == status.upper()]
    if family:
        controls = [c for c in controls if c["family"].lower() == family.lower()]
    return {"spec": "O-RAN.WG11.TS.SRCS.0-R005-v14.00", "count": len(controls), "controls": controls}


@app.get("/security/threat-model")
async def security_threat_model(interface: Optional[str] = None):
    """O-RAN threat surface (O-RAN.WG11.TR.Threat-Modeling)."""
    all_threats = ZTA.threat_model()
    interfaces = sorted({t["interface"] for t in all_threats})
    return {
        "spec": ZTA.THREAT_SPEC,
        "interfaces": interfaces,
        "threats": ZTA.threat_model(interface),
    }


# =============================================================================
# Zero-trust policy decision endpoint (PDP)
# =============================================================================

@app.post("/security/authorize")
async def security_authorize(request_ctx: Dict[str, Any]):
    """Evaluate a request against the zero-trust policy decision point."""
    with _tracer.start_as_current_span("security_authorize"):
        decision = ZTA.evaluate(request_ctx)
        if decision["decision"] == "DENY":
            _log_event("POLICY_DENY", "WARNING", str(request_ctx.get("subject", "unknown")),
                       decision["reason"], interface=decision.get("interface"))
        return decision


# =============================================================================
# Security event log (O-RAN.WG11.TS.STS)
# =============================================================================

@app.post("/security/events", status_code=201)
async def post_security_event(event: SecurityEvent):
    """Log a security event."""
    entry = _log_event(event.event_type, event.severity, event.source,
                       event.message, interface=event.interface, details=event.details)
    return entry


@app.get("/security/events")
async def get_security_events(severity: Optional[str] = None, limit: int = 100):
    """Retrieve logged security events (most recent first)."""
    events = list(reversed(_EVENT_LOG))
    if severity:
        events = [e for e in events if e["severity"].upper() == severity.upper()]
    return {"count": len(events[:limit]), "events": events[:limit]}


# =============================================================================
# Certificate inventory (CMPv2-style)
# =============================================================================

@app.get("/security/certificates")
async def get_certificates():
    """List the CertManager certificate inventory."""
    return {
        "spec": CERTS.SPEC,
        "summary": CERTS.summary(),
        "active": CERTS.list_active(),
    }


@app.post("/security/certificates/{nf_id}/rotate")
async def rotate_certificate(nf_id: str):
    """Rotate (renew) the identity for a network function."""
    try:
        entry = CERTS.rotate(nf_id)
    except KeyError:
        # Issue a fresh identity if none exists yet.
        entry = CERTS.issue(nf_id)
    _log_event("CERT_ROTATED", "INFO", nf_id, f"Certificate rotated for {nf_id}")
    return entry.to_dict()


# =============================================================================
# Health
# =============================================================================

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "security",
        "spec": "O-RAN.WG11.TS.SecProtSpec.0-R005-v14.00",
        "port": SERVICE_PORT,
        "cryptoBackend": CERTS.summary()["cryptoBackend"],
    }


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--host", default="0.0.0.0")
    p.add_argument("--port", type=int, default=SERVICE_PORT)
    a = p.parse_args()
    logger.info(f"Starting O-RAN WG11 Security Service on {a.host}:{a.port}")
    uvicorn.run(app, host=a.host, port=a.port)
