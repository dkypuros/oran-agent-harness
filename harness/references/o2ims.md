# Upstream contract pointer: O-Cloud Manager (O2 IMS reference implementation)

Conforms to: O-RAN.WG6.O2IMS-Interface
Bibliography ref: 3, 6, 39

## Source

- Upstream repository: https://github.com/openshift-kni/oran-o2ims
- Spec authority: O-RAN Alliance e.V., Working Group 6
- Spec document: O-RAN.WG6.O2IMS-Interface (Infrastructure Management Services)
- Spec portal: https://www.o-ran.org/specifications

## Pin

Commit SHA: `913484da469255ebd9446d48ec65c8217bccf872`

The pinned snapshot is the O-Cloud Manager release used as the reference O2 IMS implementation for the talk's
walkthroughs, resolved against main HEAD on 2026-05-30. The upstream is authoritative if the pinned commit
diverges from a later upstream release.

## Canonical URI structure

Per O-RAN.WG6.TS.O2IMS-INTERFACE-R005-v11 (docs/references.md bibliography ref 3), Section 3.4.3
and Section 3.4.4.2.2 (p. 118), Table 3.4.3-1, the canonical ProvisioningRequest REST resource
URI is:

  {apiRoot}/O2ims_infrastructureProvisioning/{apiMajorVersion}/provisioningRequests

apiName is `O2ims_infrastructureProvisioning`. apiMajorVersion shall be `1`. The collection
resource is `provisioningRequests` (camelCase, no underscore). The instance resource is
`{apiRoot}/O2ims_infrastructureProvisioning/v1/provisioningRequests/{provisioningRequestId}`.

Any harness demo stub that mocks this endpoint MUST follow this URI structure to remain spec
conformant on the URI dimension. HTTP semantics (response codes, status callbacks) MAY be
simplified for demo purposes.

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
