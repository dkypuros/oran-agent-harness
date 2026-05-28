# O-RAN Agent Harness

Citation-grounded declarative artifact set for the talk *From Multivendor Diagnosis to Closed-Loop
Remediation: An Agent Harness for Cloud RAN Day-2*, O-RAN nGRG Workshop, Seattle, 4th [THU] JUN 2026.

Three goals for this repository, in the author's words:

1. **Here is my presentation to the O-RAN community.** The submission abstract, the architecture
   diagram, the closing trust-loop content, and the ODA Canvas reference mapping all live under `talk/`.
2. **Here is the example work, you can go take a look at it.** The harness pattern's contracts (taxonomy,
   guardrails, schemas, routing rules, MCP tool surfaces, upstream pointers) live under `harness/`.
   Every authored file carries a citation header tying it to an O-RAN, ETSI, IEEE, 3GPP, or TM Forum
   section. The central index is `harness/conformance.md`.
3. **Here is where I actually test the use case.** Two walkthrough scenarios under `scenarios/` exercise
   the harness against host-platform PTP faults. The reference operationalization that runs them lives
   under `omc-skills/o-ran/`.

## What this repository is

A stub-only declarative artifact set. No FastMCP servers, no LangGraph agents, no Python
implementation. The architectural pattern is operationalization-agnostic. We provide an OMC skill bundle
as one reference operationalization, with the explicit framing that the contracts are portable to
LangGraph, OpenAI Agents SDK, Microsoft Semantic Kernel, or any agent framework that can read JSON
Schema and YAML.

The reference O2 IMS implementation cited throughout is Red Hat's open-source O-Cloud Manager
(openshift-kni/oran-o2ims, bibliography ref 6 in `references.md`).

## How the system works (one paragraph)

An observation loop on the edge (Intel NIC PHC, the linuxptp daemon, and cloud-event-proxy publishing
O-RAN CloudEvents) captures PTP drift evidence. The agent harness in the middle (an Agentic Gateway
over MCP, three domain agents for Platform, RAN, and Hardware, and a deterministic taxonomy with
LLM-assist on ambiguous edges) classifies the fault. A routing rule then splits actions by O-RAN
resource layer: service-layer fixes route UP to the partner SMO as a TMF921 intent; infrastructure
fixes route DOWN to the O-Cloud via the O-RAN O2 IMS API, where the Machine Config Operator or the
Kernel Module Management Operator delivers the artifact. Before any live action, the proposal runs
against a digital-twin sandbox; only sandbox-passing proposals reach the human operator with a
populated reversibility profile. Full walkthrough at `talk/architecture_narrative.md`.

## Repository map

```
oran-agent-harness/
|-- README.md            this file
|-- LICENSE              Apache-2.0
|-- references.md        public bibliography, 43 numbered AMA refs, URLs only
|-- .gitignore           defense-in-depth against .local/, python_demo/, .pdf, .env
|-- talk/                presentation artifacts
|   |-- abstract.md      canonical nGRG submission
|   |-- architecture.mmd architecture diagram source (v3, Mermaid)
|   |-- architecture.png 12K-wide rendered diagram
|   |-- trust_loop.md    EvalOps, sandboxing, Reversibility Profile narrative
|   |-- oda_mapping.md   15-element ODA Canvas reference mapping
|   `-- slides.md        slide-deck pointer (deck out of scope here)
|-- harness/             20 authored stub artifacts (the contract set)
|   |-- taxonomy.yaml    20 entries grounded in O-RAN WG6 resource model
|   |-- guardrails.yaml  LLM-free policy contract, TMF688-shaped audit
|   |-- conformance.md   central citation index
|   |-- schemas/         5 JSON Schemas, draft-07
|   |-- routing-rules/   3 YAMLs, one per talk contribution
|   |-- mcp-tool-schemas/ 4 FastMCP tool surfaces
|   `-- references/      5 upstream contract pointers, commit-SHA pinnable
|-- scenarios/           2 PTP host-platform walkthroughs
|   |-- A_fw_lldp_agent/      fw-lldp-agent service interferes with PTP
|   `-- A_prime_ice_driver/   ice driver 1.11.x causes PHC drift
`-- omc-skills/          reference operationalization (OMC)
    `-- o-ran/                4 skills + README + conformance index
```

## Citation discipline

Every authored YAML opens with `# Conforms to:` and `# Bibliography ref:` headers. Every authored JSON
carries a top-level `_conforms_to` key. The central index `harness/conformance.md` maps every file to its
upstream spec, section, version, and bibliography reference number. A file in `harness/` or `scenarios/`
that lacks a citation header is incomplete metadata; a row in the index that points to a non-existent
file is stale documentation. The verify gate runs the cross-check in both directions before publication.

Run the gate locally with:

```
pip install pyyaml
python3 scripts/verify.py
```

It runs 8 deterministic checks (citation headers, JSON parse, YAML parse, conformance.md bidirectional
completeness, em dash audit, leakage guard, README structure, file counts) and exits non-zero on any
failure. See the script header for the full list.

## Running the walkthroughs (OMC reference operationalization)

```
# Scenario A, fw-lldp-agent host service interfering with PTP
/o-ran:plan scenarios/A_fw_lldp_agent/fault_payload.json

# Scenario A-prime, outdated ice driver causing PHC drift
/o-ran:plan scenarios/A_prime_ice_driver/fault_payload.json
```

See `omc-skills/o-ran/README.md` for installation and the per-skill input and output contract.

Each end-to-end run reads a FaultPayload, walks the evidence chain across three domain agents (Platform,
RAN, Hardware), picks a routing direction via the deterministic taxonomy lookup (with LLM-assist on
ambiguous edges only), evaluates against the guardrail engine, and emits a TMF688 AuditEvent with a
populated ReversibilityProfile.

## Three contributions exercised end-to-end

| Contribution                            | Declarative form                                            | Reference operationalization                |
|------------------------------------------|--------------------------------------------------------------|----------------------------------------------|
| Remediation routing rule                 | harness/routing-rules/contribution-1-routing-rule.yaml      | omc-skills/o-ran/remediate.md                |
| Guardrail contract layer                 | harness/routing-rules/contribution-2-guardrail-contract.yaml plus harness/guardrails.yaml | omc-skills/o-ran/sandbox-validation.md       |
| LLM-neutral substrate                    | harness/routing-rules/contribution-3-llm-neutrality.yaml    | Automatic via OMC provider abstraction       |

## License

Apache-2.0. See `LICENSE`.

## Acknowledgements

The diagnostic substrate this work builds on (MCP-coordinated multivendor domain agents) is the published
output of a joint Ericsson, Red Hat, and Intel effort. See bibliography ref 35 in `references.md`. The
closed-loop remediation extension presented here is solo work by the author for the nGRG workshop.
