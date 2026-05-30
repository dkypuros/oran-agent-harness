#!/usr/bin/env python3
"""
O-RAN Compliance Test Suite.

Validates the O-RAN enhancement layer (WG1-WG11) in-process using FastAPI's
TestClient, so no ports need to be free and services do not have to be launched.
For each interface it boots the app, exercises a key procedure, and records a
PASS/FAIL. Finishes with the spec-coverage summary and a non-zero exit on any
failure.

Run:  python test_oran_compliance.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient  # noqa: E402

results = []  # (name, ok, detail)


def check(name, fn):
    try:
        detail = fn()
        results.append((name, True, detail))
        print(f"  PASS  {name:<42} {detail}")
    except Exception as e:  # noqa: BLE001
        results.append((name, False, f"{type(e).__name__}: {e}"))
        print(f"  FAIL  {name:<42} {type(e).__name__}: {e}")


def get_ok(app, path, expect_status=200):
    with TestClient(app) as client:
        r = client.get(path)
        assert r.status_code == expect_status, f"GET {path} -> {r.status_code}"
        return r


print("=" * 78)
print("O-RAN Compliance Test Suite (WG1-WG11)")
print("=" * 78)

# -------------------------------------------------------------- WG3 E2SM registry
def _e2sm():
    from ran.ric.e2ap import e2sm_registry
    oids = {m.get("name") for m in e2sm_registry.list_service_models()}
    for sm in ("E2SM-KPM", "E2SM-RC", "E2SM-CCC", "E2SM-NI", "E2SM-LLC"):
        assert sm in oids, f"missing {sm} (have {sorted(oids)})"
    return f"service models: {sorted(oids)}"
check("WG3 E2SM registry (KPM/RC/CCC/NI/LLC)", _e2sm)

# -------------------------------------------------------------- WG3 Y1
def _y1():
    from ran.ric import y1
    r = get_ok(y1.app, "/y1/analytics-types")
    return f"analytics types ok ({len(r.json()) if isinstance(r.json(), list) else 'obj'})"
check("WG3 Y1 analytics types", _y1)

# -------------------------------------------------------------- WG4 Open Fronthaul
def _ofh():
    from ran.fronthaul import o_ru
    r = get_ok(o_ru.app, "/cus/s-plane/sync")
    body = str(r.json())
    assert "LOCK" in body.upper() or "sync" in body.lower(), "no sync state"
    get_ok(o_ru.app, "/o-ran/uplane-conf")
    get_ok(o_ru.app, "/o-ran/module-cap")
    return "M-Plane + S-Plane PTP reachable"
check("WG4 Open Fronthaul O-RU (M/CUS-Plane)", _ofh)

# -------------------------------------------------------------- WG2 R1 + SMO + AIML
def _r1():
    from smo import r1
    get_ok(r1.app, "/r1/sme/services")
    get_ok(r1.app, "/r1/dme/data-types")
    return "R1 SME + DME reachable"
check("WG2 R1 (SME + DME)", _r1)

def _smo():
    from smo import smo_framework
    get_ok(smo_framework.app, "/smo/inventory")
    get_ok(smo_framework.app, "/smo/framework-services")
    return "SMO inventory + framework services"
check("WG1/WG2 SMO framework", _smo)

def _aiml():
    from smo.aiml import AimlModelRegistry
    reg = AimlModelRegistry()
    return f"AIML registry init ({len(reg.list_models()) if hasattr(reg, 'list_models') else 'ok'})"
check("WG2 AI/ML model registry", _aiml)

# -------------------------------------------------------------- WG10 O1 + TE&IV
def _o1():
    from oam import o1
    get_ok(o1.app, "/o1/nrm")
    get_ok(o1.app, "/o1/cm/managed-elements")
    return "O1 NRM + managed elements"
check("WG10 O1 (NRM / FCAPS)", _o1)

def _teiv():
    from oam import teiv
    get_ok(teiv.app, "/teiv/topology")
    return "TE&IV topology graph"
check("WG10 TE&IV topology", _teiv)

# -------------------------------------------------------------- WG6 O-Cloud notif
def _ocn():
    from etsi.o2 import o_cloud_notification as ocn
    get_ok(ocn.app, "/o-cloud/v1/subscriptions")
    return "O-Cloud notification subscriptions"
check("WG6 O-Cloud Notification API", _ocn)

# -------------------------------------------------------------- WG11 Security
def _sec():
    from security import security_service as sec
    with TestClient(sec.app) as client:
        tok = client.post("/oauth2/token", json={"grant_type": "client_credentials",
                                                  "client_id": "rapp-analytics", "client_secret": "rapp-secret"})
        assert tok.status_code in (200, 201), f"token -> {tok.status_code}"
        posture = client.get("/security/posture")
        assert posture.status_code == 200, f"posture -> {posture.status_code}"
    return "OAuth2 token + security posture"
check("WG11 Security (OAuth2 + posture)", _sec)

# -------------------------------------------------------------- WG1 Slicing + NES
def _slice():
    from ran.slicing import oran_slicing
    get_ok(oran_slicing.app, "/slicing/nsi")
    get_ok(oran_slicing.app, "/slicing/nssi")
    return "Slicing NSI + NSSI"
check("WG1 RAN Slicing (NSSMF)", _slice)

def _nes():
    from ran.energy import nes
    get_ok(nes.app, "/nes/cells")
    get_ok(nes.app, "/nes/kpi")
    return "NES cells + energy KPI"
check("WG1 Network Energy Savings", _nes)

# -------------------------------------------------------------- WG9 Transport
def _xhaul():
    from transport import xhaul
    get_ok(xhaul.app, "/xhaul/sync/clocks")
    get_ok(xhaul.app, "/xhaul/sync/status")
    return "xHaul sync clocks + status"
check("WG9 xHaul Transport / Sync", _xhaul)

# -------------------------------------------------------------- Gateway
def _gw():
    from api_gateway import oran_gateway
    get_ok(oran_gateway.app, "/api/oran/spec-coverage")
    get_ok(oran_gateway.app, "/health")
    return "gateway spec-coverage + health"
check("Gateway :8088 contract", _gw)

# -------------------------------------------------------------- Spec coverage
print("-" * 78)
from oran.o_ran_spec_map import coverage_summary  # noqa: E402
cov = coverage_summary()
print(f"  Spec coverage: {cov['implemented']} implemented + {cov['referenced']} referenced "
      f"= {cov['specs_mapped']} specs mapped across WGs {', '.join(cov['working_groups_covered'])}")
print(f"  (of {cov['spec_catalog_total']} documents in the O-RAN catalog)")

print("=" * 78)
passed = sum(1 for _, ok, _ in results if ok)
total = len(results)
print(f"RESULT: {passed}/{total} interface checks passed")
print("=" * 78)
sys.exit(0 if passed == total else 1)
