---
name: New walkthrough scenario
about: Propose a new PTP or host-platform fault scenario for the harness
title: "New scenario: <short_name> <one-line fault description>"
labels: scenario
assignees: ''
---

## Scenario short name

<!-- Use snake_case, prefixed with the scenario family letter, e.g. B_ptp_master_offset or A_double_prime_phc_clock_id. -->

`<short_name>`

## Fault description

<!-- One paragraph: what is observed at the edge, and what evidence sources surface it.
     Cite the upstream PHC, linuxptp, or O-RAN WG6 Cloud Notifications behavior if applicable. -->

## Taxonomy match (expected)

<!-- Which row in harness/taxonomy.yaml does this scenario fall into?
     If a new taxonomy entry is needed, list its proposed name, target_layer, ocloud_internal_path,
     and the action_type the routing rule would produce. -->

- Existing taxonomy entry: `<taxonomy_id_or_none>`
- New taxonomy entry needed: yes / no
  - Proposed `id`:
  - Proposed `target_layer` (infra | service | ambiguous):
  - Proposed `ocloud_internal_path` (machine-config-operator | kernel-module-management | none):
  - Proposed `action_type`:

## Target layer

- [ ] infra (routes DOWN to O2 IMS, applied by O-Cloud spoke operator)
- [ ] service (routes UP to SMO as a TMF921 intent)
- [ ] ambiguous (LLM-assist consults knowledge base)

## Evidence sources

<!-- Which MCP servers (per harness/mcp-tool-schemas/) would surface the fault evidence?
     Tick all that apply. -->

- [ ] mcp-platform (linuxptp, systemd, MachineConfig pool state)
- [ ] mcp-ran (3GPP TS 28.552 PM counters, KPI degradation)
- [ ] mcp-hardware (PHC, Intel NIC, Redfish, firmware versions)
- [ ] mcp-ocloud (O2 IMS Inventory, Alarms, Provisioning)

## Expected remediation

<!-- Which O-Cloud spoke operator delivers the artifact, and what is the artifact type? -->

- Operator: <MachineConfigOperator | KernelModuleManagement | NodeTuningOperator | other>
- Artifact CR type: <MachineConfig | Module | Tuned | other>
- Reversibility profile expected:
  - rollback_intent (replace | mask | uninstall | other):
  - confidence_in_reversibility (high | medium | low):
  - blast_radius_if_reverse (nodes/sites/cells):

## Bibliography refs

<!-- Which entries in docs/references.md back this scenario? List the numbered refs. -->

- Refs:

## Notes

<!-- Anything else reviewers should know: known caveats, future-work flags, partner sensitivity. -->
