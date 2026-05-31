---
title: "Verified run: Fedora 42 Cloud Edition + podman 5.4.1 + podman-compose 1.5.0"
date: 2026-05-31
runtime:
  os: Fedora Linux 42 (Cloud Edition)
  podman: 5.4.1
  podman_compose: 1.5.0
  host_orchestrator: Lima 2.0.3 (Apple Hypervisor backend on macOS)
  vm_resources: 4 vCPU, 4 GiB RAM, 100 GiB disk
status: PASS, end-to-end
verifier: live invocation by the bench author's session
note: This file is the canonical verification anchor for the linux_lab/. A reviewer can cite it as proof that the Fedora + podman path is not a paper claim.
---

# Verified run: Fedora 42 + podman 5.4.1 (2026-05-31)

This file records the live verification of `linux_lab/` against a real Fedora 42 VM. The bench
came up end-to-end under rootless podman with `podman-compose` against the unmodified
`macbook_lab/docker-compose.yml`. All 9 services responded to health checks; both scenario E
variants walked through the harness pipeline producing the expected dual-route output.

The test was run by spinning up a Fedora 42 Cloud Edition VM via Lima on macOS, mounting the
repo into the VM, running `linux_lab/run.sh`, and curling each endpoint from inside the VM
(no host port forwarding). This isolates the test from the Docker stack running on the host.

## Setup steps performed

```bash
# On macOS host:
limactl start fedora-test                                          # boots Fedora 42 VM
limactl shell fedora-test -- sudo dnf install -y podman-compose jq # podman already pre-installed
limactl shell fedora-test -- bash -c 'cd /Users/.../linux_lab && ./run.sh'
```

Total wall-clock time: VM boot ~30 seconds; dnf install ~10 seconds; image builds + container
starts ~5 minutes (first run, all images built fresh).

## Container state

```
NAMES                   STATUS
oran-fake-vllm          Up 42 seconds (healthy)
oran-ptp-operator-stub  Up 42 seconds (healthy)
oran-metal3-bmo-stub    Up 41 seconds (healthy)
oran-redfish-bmc-stub   Up 41 seconds (healthy)
oran-tmf921-smo-stub    Up 41 seconds (healthy)
oran-trace-viewer       Up 41 seconds
oran-harness-walker     Up 40 seconds (healthy)
oran-harness-chat       Up 40 seconds (healthy)
oran-dashboard          Up 40 seconds
```

All 9 services from `macbook_lab/docker-compose.yml` (including the dashboard profile and
oh-my-tiny-oran). Containers with healthchecks report healthy; trace-viewer and dashboard
have no healthcheck so they report only "Up" which is correct.

## Health endpoint smoke test

```
http://localhost:8090/                        OK    fake-vllm
http://localhost:8091/health                  OK    ptp-operator-stub
http://localhost:8092/health                  OK    metal3-bmo-stub
http://localhost:8093/health                  OK    redfish-bmc-stub
http://localhost:8094/health                  OK    tmf921-smo-stub
http://localhost:8096/health                  OK    harness-walker
http://localhost:8098/health                  OK    oh-my-tiny-oran
http://localhost:8095/dashboard/trace_view/   HTTP/1.0 200 OK
http://localhost:8097                         HTTP/1.1 200 OK
```

All 9 endpoints respond inside the VM. The host's Docker stack on macOS was running
simultaneously at the same port numbers; the VM boundary prevents conflict because the VM
exposes ports on its own loopback, not the host's.

## Scenario E walk (dual-route accepted path)

```
curl -sS http://localhost:8096/run/E_nic_firmware_update | jq '.event.remediation | { ... }'

{
  "action_type": "apply_metal3_firmware",
  "target_layer": "infra",
  "taxonomy_match": "node_firmware",
  "sandbox_apply_allowed": true,
  "companion_intent_accepted": true
}
```

The harness walker fired the deterministic taxonomy lookup, attached the Sandbox verdict
(apply_allowed true), and captured the SMO's accepted dispatch_result on the companion intent.
Identical behavior to the macOS Docker stack.

## Scenario E_with_smo_reject walk (dual-route rejected path)

```
curl -sS http://localhost:8096/run/E_with_smo_reject | jq '.event.remediation.companion_intent | { ... }'

{
  "accepted": false,
  "rejection_reason": "neighboring_cells_at_capacity"
}
```

The dual-route's rejection path also fires correctly under podman. The SMO's rejection lands
in the AuditEvent's `companion_intent.dispatch_result` exactly as the architecture narrative
and Q14 in `talk/reviewer_faq.md` describe.

## What this verification proves

1. **The compose YAML is genuinely runtime-portable.** Unmodified
   `macbook_lab/docker-compose.yml` parses and runs under `podman-compose` 1.5.0 (compose-spec
   compliant).
2. **The Dockerfiles are genuinely runtime-portable.** Same Dockerfile.harness-walker,
   Dockerfile.platform-stub, Dockerfile.fake-vllm, Dockerfile.trace-viewer, Dockerfile.dashboard,
   and Dockerfile.harness-chat build and run under podman.
3. **The bench's deterministic behavior is reproducible across container engines.** Same
   scenario walks produce the same audit event shapes (taxonomy match, target layer, action
   type, sandbox verdict, companion intent dispatch_result).
4. **The dual-route teaching moment works under podman.** Both E scenarios (accepted and
   rejected paths) exhibit the documented behavior.
5. **The bench's reproducibility claim ("clone the repo, run two commands") is honest for
   Fedora users.** A Fedora reviewer can reproduce this run.

## Pointers for a Fedora reviewer

To reproduce this verification on your own Fedora host (or any Fedora VM):

```bash
# Clone the repo
git clone https://github.com/dkypuros/oran-agent-harness
cd oran-agent-harness

# Run the linux_lab setup + start
cd linux_lab
./setup_fedora.sh   # installs podman-compose + jq (podman pre-installed on Fedora Cloud)
./run.sh            # builds and starts the 9 containers via podman-compose

# Verify (from any shell on the Fedora host)
curl -sS http://localhost:8096/run/E_nic_firmware_update | jq '.event.remediation.companion_intent.dispatch_result'
```

Expected output: `{"accepted": true, "smo_intent_id": "SMO-ACK-INT-flt-E-001-companion", ...}`.

If your output differs, see `linux_lab/troubleshooting.md` for common Fedora + podman issues.
