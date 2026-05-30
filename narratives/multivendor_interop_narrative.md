---
title: "Multivendor Interop: why TMF921 respects partner authority and why O2 IMS is the right boundary"
author: David Kypuros
license: Apache-2.0
status: where each vendor keeps authority and where the harness's contracts let them
audience: vendor product managers, SMO architects, integration leads at SIs
---

# Multivendor Interop Narrative

A multivendor Cloud RAN site is built from the work of competitors. Vendor A's vDU runs next to
Vendor B's radio next to Vendor C's transport, all running on a shared O-Cloud platform, all
under the same SLA. Day-2 remediation in that environment is fundamentally a coordination
problem: any change to a shared layer affects everyone, but the authority to make changes is
distributed by design.

This bench is built to respect that distribution. The architecture does not centralize
remediation authority into a single agent or a single vendor. It declares two boundaries and
emits standardized contracts at both. This narrative walks each boundary, names which partner
keeps authority on which side, and explains why the contracts the bench emits are the
appropriate interop surface.

## The first boundary: service vs infrastructure

The harness splits actions at the O-RAN resource layer line. Above the line, service-layer
actions: cell re-home, RAN parameter changes, slice intent updates, vDU software version
rollouts, scheduler reconfiguration. Below the line, infrastructure-layer actions: MachineConfig
changes, KMM driver swaps, Metal3 firmware updates, PerformanceProfile changes, SR-IOV
reconfiguration.

The split is not arbitrary. It follows O-RAN's own resource model
(`../docs/references.md#ref-2`, `../docs/references.md#ref-3`) and aligns with where partner
authority already lives in production deployments.

The high side is the partner SMO's domain. Vendor A's SMO already owns cell parameters, slice
intent, and vDU version control. The harness does not propose to execute those actions itself.
It emits a TMF921 intent (`../docs/references.md#ref-19`) UP toward the SMO and observes the
result. The harness is a consumer of partner-side authority on the high side, not a competitor
to it.

The low side is the O-Cloud's domain. The O-Cloud platform team already owns infrastructure
delivery (MachineConfig, KMM, Metal3, the Node Tuning Operator, SR-IOV). The harness routes
infrastructure actions DOWN to the O-Cloud via the O-RAN O2 IMS interface
(`../docs/references.md#ref-3`). The O-Cloud's existing operators do the actual delivery; the
harness is a structured originator of those changes, not a replacement for them.

The architectural claim is that both interfaces (TMF921 above, O2 IMS below) are sufficient to
operationalize day-2 remediation without taking authority away from anyone. The novelty is in
how cleanly the boundary falls; the contracts are pre-existing.

## What each partner SMO keeps

The harness's high-side intents target whichever partner SMO the operator is integrating with.
The list of integration partners is the list of major SMO vendors in production today: Ericsson,
Nokia, Amdocs, Mavenir, ZTE. The TMF921 contract is identical for all five. A SMO vendor's PM
should read this section as the explicit declaration of what does NOT change in their world
when the bench is introduced.

  - **Cell parameter authority** stays with the SMO. The harness emits a TMF921 intent that
    references the cell by O-RAN object id; the SMO decides whether to accept it, what to
    schedule it for, and what other cells it might affect. If the SMO rejects the intent, the
    harness records the rejection in the audit event and routes the operator to manual review.
  - **Slice intent authority** stays with the SMO. The harness never proposes a slice change
    directly; it emits a TMF921 intent referencing slice id and a target. Slice arbitration is
    out of scope for the harness.
  - **vDU software version authority** stays with the SMO. vDU upgrades have downstream
    consequences (handover behavior, mobility profiles, KPI baselines) the SMO is responsible
    for. The harness can detect a vDU-version-related fault and emit a TMF921 intent suggesting
    a rollback or upgrade window, but it does not push a version itself.
  - **Cell re-home authority** stays with the SMO. The harness emits a TMF921 intent with the
    target serving cell; the SMO orchestrates the handover.

In every case the harness's role is to surface a structured proposal with the action's blast
radius, expected service impact, and an explicit window. The SMO retains the decision and the
execution.

## What the harness claims authority over

Below the resource-layer line, the harness routes structured remediation proposals into the
O-Cloud via the O2 IMS interface. The O-Cloud's existing CRDs do the actual work:

  - **MachineConfig** (`../docs/references.md#ref-9`). Host-level configuration changes. The MCO
    handles draining, ordered reboot, pool-level coordination. The harness emits a structured
    MachineConfig spec; the MCO does the delivery.
  - **KMM Module** (`../docs/references.md#ref-10`). In-tree to out-of-tree kernel module swaps
    for NIC drivers and similar. The harness emits a Module CR; KMM signs, schedules, loads.
  - **Metal3 HostFirmwareComponents** (`../docs/references.md#ref-8`). Node firmware updates,
    BIOS updates, NIC firmware updates. The harness emits a HostFirmwareComponents apply
    target; Metal3's BareMetalOperator (`../docs/references.md#ref-7`) drives the BMC, which
    handles the actual firmware write via DMTF Redfish DSP0266
    (`../docs/references.md#ref-46`).
  - **PerformanceProfile**. Node Tuning Operator changes for CPU isolation, hugepages, RT
    scheduling. The harness emits a PerformanceProfile spec.

These are all upstream CRDs that already run in production O-Cloud deployments. The harness does
not introduce a new controller plane. It populates existing controllers with structured input.

## The dual-route case: when both boundaries fire at once

Some remediation classes cross the service-vs-infrastructure boundary by their nature. A NIC
firmware update is the canonical example: the action itself is infrastructure-layer (Metal3
firmware push, low side), but the consequence (a node reboot affecting connected cells) is
service-layer (handover coordination required, high side).

The harness handles this with the dual-route pattern. For any `node_firmware`-class action, the
routing rule fires BOTH branches: a Metal3 apply on the low side AND a TMF921 companion intent
on the high side. The high-side intent notifies the partner SMO that node X will be offline
during a specified window, so the SMO can prepare handover.

Scenario E in this repo exercises exactly this case. The audit event carries an elevated blast
radius (one node, one site, four cells) reflecting the maintenance window. The companion intent
fires regardless of the cell count because firmware reboots require SMO coordination by their
semantic, not by their magnitude. See `scenarios/E_nic_firmware_update/companion_intent.json`
for the canonical intent envelope and `harness/routing-rules/contribution-1-routing-rule.yaml`
for the rule that produces it.

This dual-route pattern is the architectural respect-the-vendor-boundary discipline made
operational. The harness does not unilaterally do anything that affects the partner SMO's
domain. When it must touch the infrastructure side AND inform the service side, it touches both
through their respective standardized contracts at the same time.

## Why TMF921 is the right high-side envelope

TMF921 Intent Management API is the TM Forum standard for SMO-bound intents
(`../docs/references.md#ref-19`). The envelope has structured fields the harness needs and the
SMO understands:

  - `intent_id` (idempotent identifier)
  - `intent_type` (handover, maintenance window, etc.)
  - `affected_resources` (cell ids, sector ids, node ids)
  - `window_start` / `window_end` (when the intent applies)
  - `service_impact_hint` (what the SMO should expect)
  - `expected_handover_count` (an explicit consequence estimate)

The harness does not invent these fields. They are what the SMO already exposes. The TMF688
(`../docs/references.md#ref-18`) audit envelope wraps every emitted intent, giving the operator
a single audit log shape across both sides.

For a vendor PM reading this: the bench does not require any change in your SMO's TMF921
implementation. It produces intents that conform to the standard you already support. The
integration cost on your side is zero beyond what you have already shipped to support TMF921.

## Why O2 IMS is the right low-side boundary

O-RAN.WG6.O2-GA&P (`../docs/references.md#ref-2`) defines the SMO-to-O-Cloud API. O-RAN.WG6
O2 IMS Interface Specification (`../docs/references.md#ref-3`) defines the structured payloads.
The reference open-source implementation is Red Hat's O-Cloud Manager
(`../docs/references.md#ref-6`).

Routing through O2 IMS rather than direct kubectl has four properties that matter for
multivendor coordination:

  1. **Auditable.** Every action lands in the same audit log the O-Cloud platform team already
     reviews. No new tool, no new ticket type.
  2. **Authorization-separated.** O2 IMS enforces the SMO-vs-platform authorization split. A
     bench that direct-kubectls would bypass cluster-admin separation.
  3. **Vendor-neutral.** O2 IMS is an O-RAN specification, not a vendor API. A multivendor
     O-Cloud (Red Hat in one site, a different distro in another) can support the same
     contracts.
  4. **Replicable.** Other O2 IMS implementations exist beyond Red Hat's reference; the bench's
     contracts are portable to any conformant implementation.

For a vendor PM whose company has its own O-Cloud distribution: the bench can target your O2
IMS endpoint just as it targets Red Hat's. The routing rule reads identically. The integration
point is the O2 IMS API your distribution already exposes.

## What this means for an integration partnership

If you are an SMO vendor and you are reading this because you want to evaluate the bench:

  - Your SMO authority does not move. The harness's high-side actions emit TMF921 intents that
    your SMO arbitrates.
  - The integration cost on your side is zero if you already implement TMF921.
  - The harness's infrastructure-side actions never touch your domain. They flow through O2 IMS
    into the O-Cloud's existing CRDs.
  - The dual-route pattern (scenario E) is the explicit case where both sides cooperate. Your
    SMO handles the handover; the O-Cloud handles the firmware.
  - The ODA Canvas reference mapping at `../talk/oda_mapping.md` shows where the harness sits
    in the ODA component model. Read that file if you want the architectural alignment in TM
    Forum terms.

If you are an O-Cloud vendor:

  - Your CRDs do the actual work. The harness is a structured originator, not a replacement.
  - The O2 IMS endpoint your distribution exposes is the integration point. No new API surface
    needed.

## Above the line on competitor positioning

This narrative deliberately does not list specific competitor failures. The framing is
"respect-the-vendor-boundary," not "win against vendor X." That framing is durable: it is true
no matter which SMO is on the other end of the TMF921 emission, and it remains true if the
vendor landscape shifts. The bench is not optimized for any single vendor's SMO; it is
optimized for the boundary that every SMO already lives behind.

The competitive landscape (per the May 16 literature search) is that most other agentic-RAN
efforts either stop at the SMO boundary without a delivery story or propose a custom controller
plane that side-steps O-RAN's resource layering. The bench's 2+3+8+9 conjunction is the
specific contribution that fills the gap without taking authority from anyone. That is the
positioning. It is in the lede of the main narrative, not in this file.

## Summary

The bench is multivendor-interop-friendly by construction. It splits actions at the
service-vs-infrastructure boundary, emits TMF921 to the partner SMO on the high side and O2
IMS to the O-Cloud on the low side, and fires both in parallel for actions whose blast radius
spans the boundary. Each partner keeps the authority they already have. The contracts the
bench emits are standards every major vendor already supports. The cost of integration is the
cost of running the bench, not the cost of changing your SMO.
