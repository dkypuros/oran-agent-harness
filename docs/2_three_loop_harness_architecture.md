# The Three-Loop Harness Architecture

This document maps the functional control-loop sequence of the **O-RAN Agent Harness**. It details the flow of data from raw physical telemetry, through agentic diagnostic aggregation, down to policy-gated infrastructure execution and human co-authorization.

## Functional & Control Loop Diagram

The following Mermaid diagram visualizes how physical signals are compressed into actionable evidence, routed deterministically, evaluated against safety policies, and delivered to operational systems under a strict human governance overlay.

```mermaid
graph TD
    %% Left Loop (Observation)
    subgraph LEFT ["Left Loop: Observation (Blue)"]
        signal["Bare Metal Timing Domain<br>(IEEE 1588 / G.8275.1 PHC)"]
        cep["cloud-event-proxy<br>(linuxptp state events)"]
        fp["FaultPayload<br>(harness/schemas/FaultPayload.json)"]

        signal --> cep
        cep --> fp
    end

    %% Cognitive Middle (Augmentation)
    subgraph MIDDLE ["Cognitive Middle: Augmentation (Orange)"]
        gateway["Agentic Gateway<br>(MCP Tool Interface)"]

        subgraph MCPS ["MCP Server Mesh"]
            mcp_plat["mcp-platform"]
            mcp_ran["mcp-ran"]
            mcp_hw["mcp-hardware"]
            mcp_oc["mcp-ocloud"]
        end

        subgraph AGENTS ["Domain Agents (Platform / RAN / HW)"]
            rca["Root Cause Analysis (RCA)<br>(harness/schemas/RCA.json)"]
        end

        router["Remediation Router<br>(harness/runtime/router.py)"]
        llm["LLM Neutral Assist<br>(For Ambiguous Path)"]
        proposal["RemediationProposal<br>(harness/schemas/RemediationProposal.json)"]

        fp --> gateway
        gateway -. "Introspection Probes" .-> MCPS
        MCPS -. "Evidence & Findings" .-> AGENTS
        AGENTS --> rca
        rca --> router
        router -. "Ambiguous Case" .-> llm
        llm -.-> router
        router --> proposal
    end

    %% Governance Overlay (Safety)
    subgraph GOV ["Governance Overlay: Safety & Authorization (Red)"]
        twin["Digital Twin Sandbox<br>(sandbox_simulation in walker.py)"]
        verdict["sandbox_verdict<br>(apply_allowed check)"]

        subgraph ENGINE ["Guardrail Engine (harness/runtime/guardrail.py)"]
            g1["Gate 1: crisis_mode check"]
            g2["Gate 2: sandbox verdict check"]
            g3["Gate 3: action_allowlist check"]
            g4["Gate 4: blast_radius cap check"]
            g5["Gate 5: require_human_approval"]
        end

        coauth["Operator Co-Authorization Seat<br>(NOC supervisor)"]

        proposal --> twin
        twin --> verdict
        verdict --> ENGINE
        ENGINE --> coauth
    end

    %% Right Loop (Action)
    subgraph RIGHT ["Right Loop: Action Proposal (Green)"]
        o2ims["O2ims Infrastructure Handoff<br>(5G_O-RAN_SIM o2ims_stub)"]
        tmf921["TMF921 Companion Intent<br>(Partner SMO Service Route)"]

        subgraph RECONCILERS ["Kubernetes-Native Operators"]
            mco["Machine Config Operator (MCO)"]
            kmm["Kernel Module Management (KMM)"]
            metal3["Metal3 BMO (Redfish BMC Update)"]
        end

        coauth == "Approved & Committed" ==> o2ims
        coauth -. "Dual-Route Coordination" .-> tmf921

        o2ims --> mco
        o2ims --> kmm
        o2ims --> metal3
    end

    %% Final Audit Sink
    audit["TMF688 AuditEvent Sink<br>(harness/schemas/AuditEvent.json)"]
    coauth --> |"Attaches ReversibilityProfile"| audit

    %% Custom Styling
    classDef left fill:#e3f2fd,stroke:#1565c0,stroke-width:2px,color:#0d47a1;
    classDef middle fill:#fff3e0,stroke:#ef6c00,stroke-width:2px,color:#e65100;
    classDef gov fill:#ffebee,stroke:#c62828,stroke-width:2px,color:#b71c1c;
    classDef right fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#1b5e20;
    classDef sink fill:#f3e5f5,stroke:#6a1b9a,stroke-width:2px,color:#4a148c;

    class LEFT,signal,cep,fp left;
    class MIDDLE,gateway,router,llm,proposal,rca,mcp_plat,mcp_ran,mcp_hw,mcp_oc middle;
    class GOV,twin,verdict,g1,g2,g3,g4,g5,coauth gov;
    class RIGHT,o2ims,tmf921,mco,kmm,metal3 right;
    class audit sink;
```

---

## Component-to-Loop Directory

### 1. Left Loop (Observation)
*   **Signal Processing:** The precision timing hardware domain streams local synchronization state.
*   **Eventing:** The `cloud-event-proxy` sidecar watches the state and publishes structured CNCF CloudEvents.
*   **The Interface:** The walker ingests this payload via the `FaultPayload` JSON Schema.

### 2. Cognitive Middle (Augmentation)
*   **Introspection Scaffolding:** The `Agentic Gateway` hosts four `Model Context Protocol` (MCP) server probes (`mcp-platform`, `mcp-ran`, `mcp-hardware`, `mcp-ocloud`) providing read-only system facts.
*   **Diagnosis:** Domain agents accumulate findings to write a unified Root Cause Analysis (`RCA.json`) artifact.
*   **Remediation Routing:** The `router.py` module evaluates the taxonomic rules, using provider-neutral LLMs only for ambiguous cases.

### 3. Governance Overlay (Safety)
*   **Digital Twin Sandbox:** The walker simulates execution against a clone topology in `sandbox_simulation()` to write a `sandbox_verdict`.
*   **Deterministic Policies:** The `guardrail.py` engine processes the `sandbox_verdict` and five structural checks declared in `guardrails.yaml`.
*   **Co-Authorization:** NOC operators retain absolute authority. They review the draft proposal, inspect the diagnostic evidence, and commit changes with the 7-field `ReversibilityProfile` appended.

### 4. Right Loop (Action)
*   **Infrastructure Handoff:** Dispatched via O-Cloud Manager stubs utilizing the **O-RAN O2ims** boundary towards Kubernetes controllers (`MCO`, `KMM`, or `Metal3`).
*   **Service Coordination:** Dispatched upward to the partner SMO using **TM Forum TMF921** intent models.
