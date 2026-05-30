"""End-to-end walkthrough for both PTP scenarios.

Conforms to:
  harness/schemas/FaultPayload.json (input shape)
  harness/schemas/RCA.json (intermediate shape, produced by stubbed_agents)
  harness/schemas/RemediationProposal.json (intermediate shape, produced by router)
  harness/schemas/AuditEvent.json (final shape, produced by guardrail)
Bibliography refs: 3, 18, 19, 31, 35

Stubs the Agentic Gateway, MCP servers, Domain Agents, and Digital Twin. The FaultPayload's
evidence array already contains what the Domain Agents would produce, so the stub re-shapes it
into the RCA shape. The Twin stub returns canned pass with twin_pass_rate 1.0.

Real components: harness.runtime.router (deterministic taxonomy lookup) and
harness.runtime.guardrail (deterministic rule evaluation, AuditEvent emission).

Usage:
  python -m harness.runtime.walker scenarios/A_fw_lldp_agent/fault_payload.json
  python -m harness.runtime.walker scenarios/A_fw_lldp_agent/fault_payload.json --verbose
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from harness.runtime import guardrail, router

_RCA_TIMESTAMP = {
    "flt-2026-05-14-001": "2026-05-14T10:42:15Z",
    "flt-2026-05-14-002": "2026-05-14T11:15:10Z",
}


def stubbed_agents(fault_payload: dict[str, Any]) -> dict[str, Any]:
    """Stubbed Gateway plus MCP servers plus Domain Agents.

    In real deployment, the Domain Agents (Platform, RAN, Hardware) consult their respective MCP
    servers and emit findings. Here we re-shape the FaultPayload evidence array (which already
    contains the findings the agents would have produced) into the RCA shape.
    """
    classification = fault_payload["expected_classification"]
    fault_id = fault_payload["fault_id"]

    rationale_map = {
        "ptp_host_stack": (
            "fw-lldp-agent.service active on PTP-bound slave interface, correlated with "
            "tx_hwtstamp_timeouts and master offset spikes. Classic host-service interference "
            "with PTP hardware timestamping."
        ),
        "host_driver": (
            "ice driver 1.11.17 matches known PHC drift regression (Intel KB 730421); monotonic "
            "frequency drift with no host-service correlation. Driver swap to 1.13.7+ via KMM is "
            "the deterministic fix."
        ),
    }

    rca: dict[str, Any] = {
        "fault_id": fault_id,
        "timestamp": _RCA_TIMESTAMP.get(fault_id, fault_payload["timestamp"]),
        "evidence": [
            {
                "source_agent": entry["source_agent"],
                "tool_name": entry["tool_name"],
                "finding": entry["finding"],
                "raw_data": entry["raw_data"],
            }
            for entry in fault_payload["evidence"]
        ],
        "candidate_classifications": [
            {
                "taxonomy_match": classification["taxonomy_match"],
                "target_layer": classification["target_layer"],
                "confidence": classification["confidence"],
                "rationale": rationale_map.get(
                    classification["taxonomy_match"],
                    "Taxonomy match per FaultPayload.expected_classification.",
                ),
            }
        ],
    }
    return rca


def stubbed_twin(proposal: dict[str, Any]) -> dict[str, Any]:
    """Stubbed Digital Twin pass.

    Real twin would deploy the proposal against a same-topology mirrored cluster and observe
    convergence. Here we return canned twin_pass_rate 1.0 so the guardrail engine proceeds. The
    twin verdict lives inside reversibility_profile.validation_history (populated by the guardrail
    engine in the next stage).
    """
    return proposal


def walk(fault_payload_path: str, verbose: bool = False) -> dict[str, Any]:
    """Walk the closed-loop pipeline end-to-end. Return the final AuditEvent.

    Stages:
      1. Load FaultPayload from disk.
      2. Stub Gateway plus MCP plus Domain Agents to produce RCA.
      3. Real Router consults taxonomy and routing rule to produce RemediationProposal.
      4. Stub Twin pass.
      5. Real Guardrail engine emits AuditEvent with reversibility_profile.
    """
    fp = json.loads(Path(fault_payload_path).read_text())
    if "_conforms_to" in fp:
        fp_no_meta = {k: v for k, v in fp.items() if k != "_conforms_to"}
    else:
        fp_no_meta = fp

    if verbose:
        print("---- Stage 1: FaultPayload (inbound) ----")
        print(json.dumps(fp_no_meta, indent=2))

    rca = stubbed_agents(fp_no_meta)
    if verbose:
        print("\n---- Stage 2: RCA (stubbed_agents) ----")
        print(json.dumps(rca, indent=2))

    proposal = router.route(rca)
    if verbose:
        print("\n---- Stage 3: RemediationProposal (real Router) ----")
        print(json.dumps(proposal, indent=2))

    proposal = stubbed_twin(proposal)

    audit_event = guardrail.evaluate(proposal, fault_id=fp_no_meta["fault_id"])
    if verbose:
        print("\n---- Stage 4: AuditEvent (real Guardrail) ----")
        print(json.dumps(audit_event, indent=2))

    return audit_event


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Walk a FaultPayload end-to-end through the harness pipeline."
    )
    parser.add_argument("fault_payload", help="Path to a FaultPayload JSON file")
    parser.add_argument("--verbose", action="store_true", help="Print each pipeline stage")
    args = parser.parse_args(argv)

    audit = walk(args.fault_payload, verbose=args.verbose)
    if not args.verbose:
        print(json.dumps(audit, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
