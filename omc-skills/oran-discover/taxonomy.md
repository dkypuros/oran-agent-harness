---
name: oran-discover:taxonomy
description: Survey the harness routing taxonomy. List all 20 entries grouped by routing layer (service, infra, ambiguous) with their O-RAN spec anchors.
argument-hint: "(no arguments)"
level: 1
citation_anchor:
  inputs:
    - ../../harness/taxonomy.yaml
    - ../../harness/routing-rules/contribution-1-routing-rule.yaml
  outputs: []
  bibliography_refs: [2, 3, 8, 9, 10]
---

# /oran-discover:taxonomy

<Purpose>
Survey the cognitive middle's routing surface. List every taxonomy entry the harness uses to
classify faults. Each entry says: which class of fault it matches, which O-RAN resource layer
it targets, and which spec section grounds the classification. This is what makes the routing
decision deterministic (not LLM-driven) for the great majority of faults.
</Purpose>

<Use_When>
- Reviewer wants to see the deterministic side of the cognitive middle, not just the LLM-assist
- Operator is debugging a misroute and wants to inspect what the taxonomy actually says
- Pre-talk dry-run: confirm the taxonomy contains entries covering the scenarios about to be
  demonstrated
- Comparing routing behavior across vendors: the taxonomy is the portable contract
</Use_When>

<Steps>

1. **Read the taxonomy.** Static mode only (no HTTP wrapper; the taxonomy is declarative).
   - Read `harness/taxonomy.yaml`
   - The file has 20 entries. Each is an object with `id`, `layer`, `o_ran_anchor`,
     `description`, `routing_hint`.

2. **Group entries by `layer`.** The three routing layers in `harness/taxonomy.yaml` are:
   - `service` (route UP to partner SMO via TMF921)
   - `infra` (route DOWN to O-Cloud via O2 IMS, delivered by Machine Config Operator at
     [ref 9](../../docs/references.md#ref-9), KMM at
     [ref 10](../../docs/references.md#ref-10), or Metal3 at
     [ref 8](../../docs/references.md#ref-8))
   - `ambiguous` (the LLM-assist class)

   Host-level configuration changes (MachineConfig path) and hardware-level changes (Metal3
   firmware, BMC Redfish) are NOT distinct routing layers; they are sub-classes within `infra`
   identified by the `id` field (`host_config`, `host_driver`, `node_firmware`, etc.). The
   router selects the delivery reconciler by `id` lookup against
   `harness/routing-rules/contribution-1-routing-rule.yaml`, not by an additional layer.

3. **Print the layer counts.** One line per layer with `layer | count | example ids`.

4. **Print the full taxonomy table.** One row per entry, columns:
   `id | layer | o_ran_anchor | description (truncated to 60 chars)`.

5. **Surface the ambiguous-class entries by name.** Those are the entries the LLM disambiguator
   has to handle. Operator should know which fault classes go to the model and which do not.

6. **Citation footer.** O-RAN O2 GA&P ([ref 2](../../docs/references.md#ref-2)), O-RAN O2 IMS
   Interface ([ref 3](../../docs/references.md#ref-3)), Metal3 CRDs
   ([ref 8](../../docs/references.md#ref-8)), MCO ([ref 9](../../docs/references.md#ref-9)),
   KMM ([ref 10](../../docs/references.md#ref-10)).

</Steps>

<Determinism_Contract>
The taxonomy is YAML data; reading it is deterministic. The grouping by `layer` is
deterministic. No LLM call. If the taxonomy adds an entry, this skill will list it without
edit because it iterates over the file's entries.
</Determinism_Contract>

<Verification>
- Source path: `harness/taxonomy.yaml`.
- Routing rule that consumes the taxonomy:
  `harness/routing-rules/contribution-1-routing-rule.yaml`.
- The verify gate validates taxonomy entries against `harness/schemas/` and confirms each entry's
  `o_ran_anchor` is registered in `harness/conformance.md`.
</Verification>
