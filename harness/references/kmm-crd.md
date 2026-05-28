# Upstream contract pointer: Module v1beta1 CRD (Kernel Module Management)

Conforms to: kmm.sigs.x-k8s.io/v1beta1 Module
Bibliography ref: 10, 42

## Source

- Upstream repository: https://github.com/kubernetes-sigs/kernel-module-management
- CRD path within repo:
  https://github.com/kubernetes-sigs/kernel-module-management/tree/main/config/crd/bases/kmm.sigs.x-k8s.io_modules.yaml
- API group/version: kmm.sigs.x-k8s.io/v1beta1
- Kind: Module
- Lineage note: KMM was originally developed under rh-ecosystem-edge before moving to kubernetes-sigs. Both
  repositories may be referenced depending on the OpenShift release.

## Pin

Commit SHA: `<commit-sha-pinned-at-publication>`

The pinned snapshot is the KMM Module v1beta1 release that scenario `A_prime_ice_driver` conforms to. The
placeholder above is intentional; pinning is a follow-up step before 3rd [WED] JUN 2026 publication.

## How the harness consumes this contract

- `scenarios/A_prime_ice_driver/remediation.yaml` is a real Module manifest using
  `apiVersion: kmm.sigs.x-k8s.io/v1beta1` and `kind: Module`. It swaps the in-tree `ice` driver for an
  out-of-tree 1.13.7 build via KMM's `inTreeRemoval` and `kernelMappings` mechanism.
- `harness/routing-rules/contribution-1-routing-rule.yaml` routes the `host_driver` taxonomy entry through
  `ocloud_internal: kernel-module-management` with `action_type: apply_kmm_module`.
- `harness/schemas/RemediationProposal.json` includes `apply_kmm_module` in its `actionType` enum and
  `kernel-module-management` in its `ocloudInternalPath` enum.

## Why KMM instead of MachineConfig for driver swaps

OpenShift driver updates require building the OOT module against the running kernel, signing it, unloading
the in-tree variant via `inTreeRemoval`, and restarting dependent services (PTP via the linuxptp-daemon).
MachineConfig does not perform module compilation. KMM does. This routing decision is the architectural
teaching point of Scenario A-prime: same DOWN branch as Scenario A, different internal delivery mechanism.

## What we do NOT redistribute

The KMM CRD lives in the kubernetes-sigs/kernel-module-management repository. We do not vendor the CRD YAML
into this stub. The scenario remediation.yaml is a CONSUMER of the CRD (a Module instance), not a copy of
the CRD itself.
