# Dual-Route Coordination Sequence

This document details the **Dual-Route Coordination Sequence (Bridge 4)**. It outlines the chronological sequence of events that occur when a critical physical infrastructure fault (such as a NIC firmware update in Scenario E) requires a service coordination maintenance window before physical execution is authorized.

## Logical Sequence Diagram

The following Mermaid sequence diagram maps out the asynchronous signal-to-remediation flow, showing how service-layer intents and infrastructure-layer dispatches are coordinated in parallel before landing at the human co-authorization seat.

```mermaid
sequenceDiagram
    autonumber
    actor Operator as Human Operator (Co-Auth Seat)
    participant HW as Hardware Domain (PTP/NIC)
    participant Harness as Agent Harness (Cognitive Middle)
    participant SMO as Partner SMO (Service Route)
    participant OCM as O-Cloud Manager (O2ims Route)
    participant Audit as TMF688 Audit Sink

    %% Step 1: Observation
    HW->>Harness: Inbound FaultPayload (NIC/PHC drift detected)

    %% Step 2: Cognitive Evaluation
    activate Harness
    Note over Harness: Domain Agents compile RCA findings
    Note over Harness: router.py determines taxonomy class
    Note over Harness: walker.py executes sandbox_simulation()
    Harness->>Harness: Attach sandbox_verdict (apply_allowed: true)

    %% Step 3: Dual-Route Parallel Dispatch
    Note over Harness: Dual-Route Triggered (Firmware update requires host reboot)

    par Service Route: Request Maintenance Window
        Harness->>SMO: Post TMF921 Companion Intent (Request Window)
        activate SMO
        Note over SMO: Check neighboring capacity
        SMO-->>Harness: Return dispatch_result (Accepted / Rejected)
        deactivate SMO
    and Infrastructure Route: Prepare Delivery Path
        Harness->>Harness: Format O2ims dispatch payload
    end

    %% Step 4: Guardrail Gating
    Harness->>Harness: guardrail.py executes 5-Gate checks
    Harness->>Harness: Attach 7-Field ReversibilityProfile
    Harness->>Operator: Present Draft Audit Event (Pending State)
    deactivate Harness

    %% Step 5: Human Co-Authorization
    Note over Operator: Operator inspects evidence,<br/>sandbox verdict, & SMO window status
    Operator->>Harness: Promote Draft (Approve and Commit)

    %% Step 6: Physical Execution
    activate Harness
    Harness->>OCM: Execute O2ims Provisioning Request
    activate OCM
    OCM->>HW: Reconcile CRD state (Metal3 BMO Redfish write + reboot)
    OCM-->>Harness: Return dispatch status
    deactivate OCM

    %% Step 7: Persisted Audit
    Harness->>Audit: Append Promoted AuditEvent (TMF688 Envelope)
    deactivate Harness
```

---

## Chronological Walkthrough & Key Boundaries

### 1. Inbound Event Ingestion (Left Loop)
A physical timing or hardware fault surfaces on a bare-metal node. The `cloud-event-proxy` translates the state change into an O-RAN WG6 Cloud Notification and pushes a `FaultPayload` to the Agentic Gateway.

### 2. Sandbox Verification (Digital Twin)
Before making external network dispatches, the harness executes `sandbox_simulation()` within `walker.py`. It obtains a `sandbox_verdict` from the digital twin mirroring surface. If `apply_allowed` is `False`, the loop is terminated immediately.

### 3. Parallel Dual-Route Action (The Seam)
Because a NIC firmware update requires offline host reboots, the harness initiates parallel operations:
*   **The Service Route:** A **TM Forum TMF921** Companion Intent is emitted to the Partner SMO. The partner SMO checks neighboring cells (Scenario E' is accepted; Scenario E'' is rejected because neighboring capacity is already at 92 percent).
*   **The Infrastructure Route:** The draft **O-RAN O2ims** dispatch parameters are packaged.

### 4. Human-Governed Co-Authorization
The `guardrail.py` engine processes the outputs, attaches the **7-field Reversibility Profile**, and blocks physical dispatch. The NOC Operator reviews the draft, inspects the SMO's maintenance window decision, and commits (promotes) the action, prompting live O2ims execution and TMF688 audit storage.

### Scenario E and E-with-SMO-reject Nuance
The dual-route pattern is parallel emission, not hidden two-phase commit. Scenario E sends the infrastructure preparation down through O2ims while the companion service context goes up through TMF921. Scenario E-with-SMO-reject keeps the same infrastructure-side sandbox verdict but captures `dispatch_result.accepted=false` from the partner SMO. That rejection lands in the AuditEvent before operator co-authorization, so the operator sees both facts at once: the twin says the payload can land, and the SMO says the service window is not safe yet.
