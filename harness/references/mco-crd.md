# Upstream contract pointer: MachineConfig CRD (Machine Config Operator)

Conforms to: machineconfiguration.openshift.io/v1 MachineConfig
Bibliography ref: 9, 12, 41

## Source

- Upstream repository: https://github.com/openshift/machine-config-operator
- CRD path within repo:
  https://github.com/openshift/machine-config-operator/tree/main/manifests/machineconfiguration.crd.yaml
- Documentation: https://docs.redhat.com/en/documentation/openshift_container_platform (managing machine
  configurations)
- API group/version: machineconfiguration.openshift.io/v1
- Kind: MachineConfig

## Pin

Commit SHA: `<commit-sha-pinned-at-publication>`

The pinned snapshot is the MachineConfig CRD version that scenario `A_fw_lldp_agent` conforms to. The
placeholder above is intentional; pinning is a follow-up step before 3rd [WED] JUN 2026 publication.

## How the harness consumes this contract

- `scenarios/A_fw_lldp_agent/remediation.yaml` is a real MachineConfig manifest using
  `apiVersion: machineconfiguration.openshift.io/v1` and `kind: MachineConfig`. It masks the
  `fw-lldp-agent.service` systemd unit on the worker-ran node pool.
- `harness/routing-rules/contribution-1-routing-rule.yaml` routes the `host_config` and `ptp_host_stack`
  taxonomy entries through `ocloud_internal: machine-config-operator` with `action_type:
  apply_machine_config`.
- `harness/schemas/RemediationProposal.json` includes `apply_machine_config` in its `actionType` enum and
  `machine-config-operator` in its `ocloudInternalPath` enum.

## What we do NOT redistribute

The MachineConfig CRD lives in the openshift/machine-config-operator repository. We do not vendor the CRD
YAML into this stub. The scenario remediation.yaml is a CONSUMER of the CRD (a MachineConfig instance), not
a copy of the CRD itself.
