# Upstream contract pointer: cloud-event-proxy (PTP CloudEvents publisher)

Conforms to: O-RAN.WG6 Cloud Notifications, on top of CNCF CloudEvents 1.0
Bibliography ref: 29, 30, 31, 40

## Source

- Upstream repository: https://github.com/redhat-cne/cloud-event-proxy
- Maintainer: Red Hat Cloud Native Events project
- Event envelope: CNCF CloudEvents 1.0 (https://cloudevents.io)
- Event payload contract: O-RAN.WG6 Cloud Notifications

## Pin

Commit SHA: `<commit-sha-pinned-at-publication>`

The pinned snapshot is the cloud-event-proxy release whose schema versions the harness consumes. The
placeholder above is intentional; pinning is a follow-up step before 3rd [WED] JUN 2026 publication.

## How the harness consumes this contract

- `harness/schemas/FaultPayload.json` describes the fault context that the diagnostic substrate produces
  from CloudEvents emitted by cloud-event-proxy. Its `evidence` array carries the linuxptp state transitions
  and NIC counter snapshots that the proxy publishes.
- The Agentic Gateway in the architecture diagram (`talk/architecture.mmd`, v3) consumes O-RAN CloudEvents
  from this proxy on the inbound path.
- The talk walks two PTP scenarios that BOTH originate from linuxptp state changes observed via
  cloud-event-proxy.

## What we do NOT redistribute

The CloudEvents JSON schemas are not copied into this stub. They live in the upstream cloud-event-proxy
repository and in the CNCF CloudEvents 1.0 specification. The harness's FaultPayload schema is a
harness-unique aggregation that consumes CloudEvents-shaped data; it does not replace the upstream contract.
