---
name: o-ran:troubleshoot
description: Read a CloudEvents-shaped FaultPayload, walk the evidence chain across domain agents, produce an RCA artifact conforming to harness/schemas/RCA.json
argument-hint: "<path to fault_payload.json>"
level: 2
citation_anchor:
  inputs:
    - ../../harness/schemas/FaultPayload.json
  outputs:
    - ../../harness/schemas/RCA.json
  bibliography_refs: [31, 35]
---

# /o-ran:troubleshoot

<Purpose>
Reads a FaultPayload that has arrived via the Agentic Gateway from cloud-event-proxy. Walks the evidence
chain across the three domain agents (Platform, RAN, Hardware). Produces a structured Root Cause Analysis
artifact that the routing rule will consume.
</Purpose>

<Use_When>
- A new CloudEvent has arrived from linuxptp via cloud-event-proxy
- Operator wants to understand a fault before authorizing remediation
- Diagnostic substrate walkthrough on stage
</Use_When>

<Steps>

1. **Load the FaultPayload**: Read the file path provided as argument. Validate against
   `../../harness/schemas/FaultPayload.json`. If validation fails, stop and report the validation error.

2. **Inspect evidence by domain**:
   - Platform Agent evidence (source_agent == "platform"): linuxptp state, host service status, NIC stats
   - RAN Agent evidence (source_agent == "ran"): cell sync, PM counters, RAN parameters
   - Hardware Agent evidence (source_agent == "hardware"): PHC introspection, BMC Redfish, CPU counters

3. **Build candidate classifications**:
   - Look up taxonomy entries in `../../harness/taxonomy.yaml` whose id matches a finding pattern
   - For each candidate, record taxonomy_match, target_layer, confidence, rationale
   - If multiple candidates have the same confidence, mark the classification as ambiguous

4. **Emit RCA**: Produce a JSON document conforming to `../../harness/schemas/RCA.json` with:
   - `fault_id` from the input payload
   - `timestamp` set to now
   - `evidence` flattened from all domain agents in chronological order
   - `candidate_classifications` ranked by confidence

5. **Hand off**: The RCA artifact is the input to `/o-ran:remediate`. Do NOT propose remediation here.
   The talk's argument depends on diagnosis and routing being distinct steps.

</Steps>

<Determinism_Contract>
This skill is taxonomy-driven. The taxonomy lookup is deterministic. LLM reasoning is invoked ONLY when
all candidate classifications resolve to layer "ambiguous" in the taxonomy. In that case, the LLM consults
the knowledge base (RAG) before disambiguating. Every LLM call is recorded in `knowledge_base_lookups`.
</Determinism_Contract>

<Verification>
Output must validate against `../../harness/schemas/RCA.json`. The verify pass in Phase 6 runs this
validation on both walkthrough scenarios.
</Verification>
