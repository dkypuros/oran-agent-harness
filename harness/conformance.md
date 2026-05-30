# Conformance index

Central index mapping every authored stub artifact in this repository to the upstream specification it
conforms to and the bibliography reference that documents it. This file is the contract the project's
verify gate (`/oh-my-claudecode:verify`) runs against. Bibliography ref numbers index into
`docs/references.md`.

## Rule

Every YAML or YML file under `harness/` and `scenarios/` opens with a `# Conforms to:` header and a
`# Bibliography ref:` header. Every JSON file under those paths carries a top-level `_conforms_to` key
with the same metadata fields. If a file in those paths is missing from the table below or missing its
header, the verify gate fails.

## Harness artifacts

| File                                            | Document family                                                   | Section                                                | Version              | Bibliography ref |
|-------------------------------------------------|-------------------------------------------------------------------|--------------------------------------------------------|----------------------|------------------|
| harness/taxonomy.yaml                           | O-RAN.WG6 O-Cloud resource model                                  | Resource categorization, applied per WG1 Architecture  | WG6 current, WG1 v8  | 1, 2             |
| harness/guardrails.yaml                         | harness-unique policy contract, audit shape per TMF688            | Policy schema and TMF688 event envelope                | v0, TMF688 current   | 18               |
| harness/conformance.md                          | this file (meta-index)                                            | n/a                                                    | v0                   | n/a              |
| harness/schemas/RemediationProposal.json        | O-RAN.WG6.O2IMS-Interface and TMF921 Intent Management API        | O2 IMS ProvisioningRequest; TMF921 Intent envelope     | WG6 current, TMF921  | 3, 19            |
| harness/schemas/FaultPayload.json               | harness-unique, evidence shape approximates O2 IMS Monitoring     | AlarmEventRecord (O2IMS-INTERFACE R005-v11 Section 3.3.6.2.2), AlarmChangeNotification (Section 3.3.5.1.2), Cloud Notifications | WG6 O2IMS R005-v11   | 3, 31            |
| harness/schemas/AuditEvent.json                 | TMF688 Event Management API                                       | Event envelope and notification body                   | TMF688 current       | 18               |
| harness/schemas/RCA.json                        | harness-unique Root Cause Analysis evidence chain                 | Prior demo substrate, Ericsson blog (ref 35)           | v0                   | 35               |
| harness/schemas/ReversibilityProfile.json       | harness-unique trust-loop contribution                            | v0 reversibility contract, see talk/trust_loop.md      | v0                   | n/a              |
| harness/schemas/CrisisModeActivation.json       | harness-unique Killswitch contract, AT&T-reviewed                 | v0 crisis-mode activation envelope, see talk/killswitch.md | v0               | n/a              |
| harness/routing-rules/contribution-1-routing-rule.yaml  | O-RAN.WG6 resource model and TMF921 Intent envelope       | Up-vs-down routing per resource layer                  | v0                   | 1, 2, 3, 19      |
| harness/routing-rules/contribution-2-guardrail-contract.yaml | harness-unique, audit shape per TMF688               | Four named elements, declarative form                  | v0                   | 18               |
| harness/routing-rules/contribution-3-llm-neutrality.yaml | harness-unique substrate constraint, LiteLLM-style       | Provider abstraction assertion                         | v0                   | 17               |
| harness/mcp-tool-schemas/mcp-platform.json      | Anthropic MCP tool-schema spec                                    | tools object, per server                               | MCP current          | 13, 14, 15       |
| harness/mcp-tool-schemas/mcp-ran.json           | Anthropic MCP tool-schema spec, PM context per 3GPP TS 28.552     | tools object; 3GPP 5G performance measurements         | MCP current, 28.552  | 13, 32           |
| harness/mcp-tool-schemas/mcp-hardware.json      | Anthropic MCP tool-schema spec, PHC and Redfish references        | tools object                                           | MCP current          | 13, 34           |
| harness/mcp-tool-schemas/mcp-ocloud.json        | Anthropic MCP tool-schema spec, O-Cloud surface per O2 IMS        | tools object; O2 IMS Inventory, Alarms, Provisioning   | MCP current, WG6     | 3, 6, 13         |
| harness/references/o2ims.md                     | O-RAN.WG6.O2IMS-Interface (pointer)                               | O2 IMS reference implementation                        | 913484d              | 3, 6, 39         |
| harness/references/cloudevents.md               | O-RAN.WG6 Cloud Notifications, CNCF CloudEvents 1.0 (pointer)     | Event publisher, schema versions                       | 3774ede              | 29, 30, 31, 40   |
| harness/references/mco-crd.md                   | machineconfiguration.openshift.io/v1 MachineConfig (pointer)      | MachineConfig CRD                                      | d72b715              | 9, 12, 41        |
| harness/references/kmm-crd.md                   | kmm.sigs.x-k8s.io/v1beta1 Module (pointer)                        | Module CRD                                             | b8e0265              | 10, 42           |
| harness/references/mcp-spec.md                  | Anthropic Model Context Protocol Specification (pointer)          | MCP tool-schema spec                                   | d069881              | 13, 14, 15, 43   |
| harness/runtime/scenario_stubs.json             | harness-unique consolidated stub table (single source of truth)   | Per-scenario stub values consumed by router + guardrail + walker | v0           | 3, 18, 19, 31, 35 |

## Scenario artifacts

| File                                                     | Document family                                                 | Section                                                | Version              | Bibliography ref |
|----------------------------------------------------------|-----------------------------------------------------------------|--------------------------------------------------------|----------------------|------------------|
| scenarios/A_fw_lldp_agent/fault_payload.json             | validates against harness/schemas/FaultPayload.json             | Synthetic platform-agent evidence bundle               | v0                   | 31               |
| scenarios/A_fw_lldp_agent/remediation.yaml               | machineconfiguration.openshift.io/v1 MachineConfig              | Real MCO MachineConfig instance                        | mcov1 current        | 9, 41            |
| scenarios/A_fw_lldp_agent/audit_event.json               | TMF688 Event Management API and ReversibilityProfile (Phase 4)  | Event envelope plus reversibility_profile field        | TMF688 current       | 18               |
| scenarios/A_prime_ice_driver/fault_payload.json          | validates against harness/schemas/FaultPayload.json             | Synthetic platform-agent evidence bundle               | v0                   | 31               |
| scenarios/A_prime_ice_driver/remediation.yaml            | kmm.sigs.x-k8s.io/v1beta1 Module                                | Real KMM Module instance                               | kmmv1beta1 current   | 10, 42           |
| scenarios/A_prime_ice_driver/audit_event.json            | TMF688 Event Management API and ReversibilityProfile (Phase 4)  | Event envelope plus reversibility_profile field        | TMF688 current       | 18               |
| scenarios/A_fw_lldp_agent/rca.json                       | validates against harness/schemas/RCA.json                      | Diagnostic substrate output (stubbed_agents fixture)   | v0                   | 35               |
| scenarios/A_fw_lldp_agent/remediation_proposal.json      | validates against harness/schemas/RemediationProposal.json      | Router output before guardrail evaluation              | v0                   | 3, 19            |
| scenarios/A_prime_ice_driver/rca.json                    | validates against harness/schemas/RCA.json                      | Diagnostic substrate output (stubbed_agents fixture)   | v0                   | 35               |
| scenarios/A_prime_ice_driver/remediation_proposal.json   | validates against harness/schemas/RemediationProposal.json      | Router output before guardrail evaluation              | v0                   | 3, 19            |
| scenarios/README.md                                      | walkthrough narrative (not a contract artifact)                 | Documents pipeline stages and stub vs real boundaries  | v0                   | n/a              |
| scenarios/D_phc_drift_hw_only/fault_payload.json         | validates against harness/schemas/FaultPayload.json             | Software-LOCKED + hardware-NOT-OK divergence pattern    | v0                   | 26, 28, 29, 30, 31, 44 |
| scenarios/D_phc_drift_hw_only/rca.json                   | validates against harness/schemas/RCA.json                      | Diagnostic substrate output for the D scenario          | v0                   | 35               |
| scenarios/D_phc_drift_hw_only/remediation_proposal.json  | validates against harness/schemas/RemediationProposal.json      | Router output for the D scenario                        | v0                   | 3, 19            |
| scenarios/D_phc_drift_hw_only/remediation.yaml           | kmm.sigs.x-k8s.io/v1beta1 Module                                | KMM Module CR swapping ice 1.11.17 for 1.13.7+          | kmmv1beta1 current   | 10, 42           |
| scenarios/D_phc_drift_hw_only/audit_event.json           | TMF688 Event Management API and ReversibilityProfile            | Event envelope plus reversibility_profile field         | TMF688 current       | 18               |
| scenarios/E_nic_firmware_update/fault_payload.json       | validates against harness/schemas/FaultPayload.json             | NIC firmware regression alarm; PHC drift persistent post-KMM | v0              | 26, 28, 29, 30, 31, 34, 44, 46 |
| scenarios/E_nic_firmware_update/rca.json                 | validates against harness/schemas/RCA.json                      | Diagnostic substrate output isolating firmware as root cause | v0              | 35               |
| scenarios/E_nic_firmware_update/remediation_proposal.json | validates against harness/schemas/RemediationProposal.json plus companion_intent extension | Router output with TMF921 companion intent for dual-route | v0              | 3, 7, 8, 19, 46 |
| scenarios/E_nic_firmware_update/remediation.yaml         | metal3.io/v1alpha1 HostFirmwareComponents                       | Metal3 BMO firmware update CR for Intel E810 NIC          | metal3v1alpha1 current | 7, 8           |
| scenarios/E_nic_firmware_update/audit_event.json         | TMF688 Event Management API, ReversibilityProfile, companion_intent | Event envelope at blast (cells:4) plus SMO companion intent for firmware-class action | TMF688 current | 18, 19   |

## How the verify gate uses this index

The gate runs two cross-checks:

1. Every authored YAML and JSON file with a citation header is listed as a row above.
2. Every row above points to a file that exists and parses (YAML for `.yaml`, JSON for `.json`).

A leak in either direction fails the gate. A file with a header but no row in this table is incomplete
metadata. A row pointing to a non-existent file is stale documentation.

The exception is `harness/conformance.md` itself, which lists itself as a meta-index row but is not subject
to a separate conformance header (it is the conformance contract).
