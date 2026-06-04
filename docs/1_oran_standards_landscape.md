# O-RAN Standards Reference Landscape

This document contains a comprehensive architectural diagram mapping the global O-RAN reference topology and standardized interface conduits, explicitly highlighting the structural boundaries and active touchpoints of the **O-RAN Agent Harness**.

## Architectural Topology Diagram

The following Mermaid diagram visualizes the O-RAN standards landscape. The styling highlights **active conduits** (interfaces traversed or bridged by the harness), **boundary seams** (respected interfaces used for scoping), and **out-of-scope baselines** (radio-real-time control and internal baseband interfaces).

```mermaid
graph TB
    %% Core Nodes & Subgraphs

    subgraph SMO ["Service Management & Orchestration (SMO)"]
        nonrt["Non-RT RIC"]
        rapp["rApps"]
        rapp -- "R1" --> nonrt
    end

    subgraph OCLOUD ["O-Cloud Infrastructure Platform"]
        ocm["O-Cloud Manager"]
        k8s["Container Platform (Kubernetes / OpenShift)"]
        hw["Physical Hardware (Worker Nodes, SmartNICs, BMCs)"]
        ocm --> k8s
        k8s --> hw
    end

    subgraph RAN ["Radio Access Network (RAN)"]
        nearrt["Near-RT RIC"]

        subgraph CU ["O-CU (Centralized Unit)"]
            cucp["O-CU-CP (Control Plane)"]
            cuup["O-CU-UP (User Plane)"]
            cucp -- "E1" --> cuup
        end

        odu["O-DU (Distributed Unit)"]
        oru["O-RU (Radio Unit)"]
    end

    %% Standard Interfaces & Harness Bounds

    %% Service Route
    nonrt -- "O1 telemetry" --> nearrt
    nonrt -- "O1 telemetry" --> CU
    nonrt -- "O1 telemetry" --> odu
    nonrt -- "O1 telemetry" --> oru

    %% Optimization & RT Control (Out of Scope)
    nonrt -- "A1 policy" --> nearrt
    nearrt -- "E2 control" --> CU
    nearrt -- "E2 control" --> odu

    %% Baseband Conduits (Out of Scope)
    CU -- "F1 transport" --> odu
    odu -- "Open Fronthaul 7.2x" --> oru

    %% Infrastructure Deployment (Out of Scope)
    nonrt -- "O2dms" --> ocm

    %% Infrastructure Provisioning (Harness Core Right Loop)
    nonrt -- "O2ims" --> ocm

    %% Harness Overlay Definition
    subgraph HARNESS ["O-RAN Agent Harness (Cognitive Middle)"]
        gateway["Agentic Gateway"]
        router["Remediation Router"]
        guardrail["Guardrail Engine"]

        gateway --> router
        router --> guardrail
    end

    %% Harness Connection Trajectories
    hw -. "PTP Timing Drifts & Events" .-> gateway
    guardrail == "Bridge 3: O2ims-to-Operator-CRD Apply" ==> ocm
    guardrail == "Bridge 4: TMF921 Companion Intent" ==> nonrt

    %% Custom Styling for Harmonious, Premium Design
    classDef harness fill:#d4edda,stroke:#28a745,stroke-width:3px,color:#155724;
    classDef inscope fill:#cfe2ff,stroke:#0d6efd,stroke-width:2.5px,color:#084298;
    classDef boundary fill:#fff3cd,stroke:#ffc107,stroke-width:2px,color:#664d03;
    classDef outofscope fill:#f8f9fa,stroke:#6c757d,stroke-width:1px,color:#6c757d;

    %% Class Assignments
    class HARNESS,gateway,router,guardrail harness;
    class ocm,k8s,hw inscope;
    class nonrt,rapp boundary;
    class nearrt,cucp,cuup,odu,oru outofscope;
```

---

## Interface Definition Directory

### 1. Active Harness Touchpoints (In-Scope)
*   **O2ims (Infrastructure Management Services):** Connecting the SMO down to the O-Cloud Manager. The harness routes infrastructure remediation proposals (reboots, driver updates, firmware pushes) down this conduit.
*   **O1 (FCAPS Control Plane):** Consumed in the harness's left loop. Precision timing anomalies and platform events are ingested as standard `FaultPayload` objects.
*   **TMF921 / TMF688 (TM Forum Intent & Audit):** Used by the harness to register TMF921-shaped intent requests for dual-route coordination and write TMF688-shaped audit events for human co-authorization.

### 2. Isolated Boundaries & Seams (Respected/Prospective)
*   **R1 Interface:** Standard API boundary connecting rApps to the Non-RT RIC framework. The harness marks this as a prospective Bridge 7 seam for v1 packaging.
*   **O2dms (Deployment Management Services):** Responsible for scaling software containers (vDUs/vCUs). Explicitly bypassed, as the harness handles infrastructure remediation, not deployment lifecycle.

### 3. Baseband & Real-Time Control (Out-of-Scope)
*   **A1 / E2 Interfaces:** Used for real-time edge radio optimization. Marked out-of-scope to enforce strict layer-boundary discipline.
*   **E1 / F1 / Open Fronthaul:** Internal baseband transport protocols. The harness monitors physical synchronization status from the Open Fronthaul boundary but does not intercept the transport packets.
