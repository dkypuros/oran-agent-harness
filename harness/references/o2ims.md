# Upstream contract pointer: O-Cloud Manager (O2 IMS reference implementation)

Conforms to: O-RAN.WG6.O2IMS-Interface
Bibliography ref: 3, 6, 39

## Source

- Upstream repository: https://github.com/openshift-kni/oran-o2ims
- Spec authority: O-RAN Alliance e.V., Working Group 6
- Spec document: O-RAN.WG6.O2IMS-Interface (Infrastructure Management Services)
- Spec portal: https://www.o-ran.org/specifications

## Pin

Commit SHA: `<commit-sha-pinned-at-publication>`

The pinned snapshot is the O-Cloud Manager release used as the reference O2 IMS implementation for the talk's
walkthroughs. The placeholder above is intentional; pinning is a follow-up step before 3rd [WED] JUN 2026
publication. Until pinned, the live URL above remains authoritative.

## How the harness consumes this contract

- `harness/mcp-tool-schemas/mcp-ocloud.json` declares the MCP tool surface that the harness uses to call
  into the O-Cloud Manager. Its conformance metadata cites this contract.
- `harness/schemas/RemediationProposal.json` carries a `ocloudInternalPath` enum whose values correspond to
  the operator paths the O-Cloud Manager delegates to (machine-config-operator, kernel-module-management,
  metal3-baremetal-operator, etc.).
- `harness/routing-rules/contribution-1-routing-rule.yaml` sends every infra-layer remediation through the
  O2 IMS path defined here.

## What we do NOT redistribute

We do not embed the O2 IMS OpenAPI from the upstream repository into this stub repo. The contract is
referenced by URL and SHA; the upstream owns it. If the stub data here diverges from the upstream contract
at a given SHA, the upstream is authoritative.
