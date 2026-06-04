# The Operator Inspection & Discovery Surface

This document details **The Operator Inspection & Discovery Surface (The Read-Before-Write Layer)**. It illustrates how the operator-facing inspection surface at `omc-skills/oran-discover/` leverages six modular probes and one orchestrator to compile clear, spec-cited diagnostic evidence before executing mutating actions on the O-Cloud.

## Human-in-the-Loop View Diagram

The following Mermaid diagram visualizes the structural wiring of the `/oran-discover` chat-and-probe interface. It maps how command inputs read from live lab wrappers or static repo fallbacks to return human-readable diagnostic cards.

```mermaid
graph TD
    %% User Console
    subgraph CONSOLE ["Operator Console Tier"]
        operator["Human Operator / NOC Supervisor"]
        chat["oh-my-tiny-oran<br>(OMC Chat Client)"]

        operator -- "1. Issue Command" --> chat
    end

    %% Discovery Engine
    subgraph ENGINE ["oran-discover Probe Directory"]
        plan["/oran-discover:plan<br>(Consolidated Pre-Flight Orchestrator)"]

        subgraph PROBES ["Modular Read-Only Probes"]
            ptp["/oran-discover:ptp<br>(PTP Sync & PHC State)"]
            metal3["/oran-discover:metal3<br>(Metal3 BMO State)"]
            redfish["/oran-discover:redfish<br>(BMC Redfish State)"]
            smo["/oran-discover:smo<br>(TMF921 SMO Intent State)"]
            tax["/oran-discover:taxonomy<br>(20-Entry Routing Taxonomy)"]
            guard["/oran-discover:guardrail<br>(Policy & crisis_mode State)"]
        end

        chat --> |"Invokes Probe"| PROBES
        chat --> |"Pre-Flight Inspection"| plan
        plan --> |"Walks all 6 Probes"| PROBES
    end

    %% Data Boundary
    subgraph DATA ["Harness Data Extraction Layer"]
        subgraph LIVE ["MacBook / Linux Compose Lab"]
            wrappers["HTTP Live API Wrappers"]
        end

        subgraph OFFLINE ["Offline Repository Fallbacks"]
            stubs["Static Fallback Files<br>(omc-skills/oran-discover/stubs/)"]
        end

        PROBES --> |"GET Request"| wrappers
        PROBES --> |"File Read"| stubs
    end

    %% Trust Outputs
    subgraph TRUST ["Human Trust Verification Output"]
        report["Spec-Cited Diagnostic Report Card<br>(With Bidirectional Standards Traceability)"]
        conform["harness/conformance.md Table Check"]
    end

    PROBES ==> report
    report ==> |"2. Present Evidence"| operator
    report -.-> conform

    %% Custom Styling
    classDef console fill:#fff3e0,stroke:#ef6c00,stroke-width:2px,color:#e65100;
    classDef engine fill:#e3f2fd,stroke:#1565c0,stroke-width:2px,color:#0d47a1;
    classDef data fill:#f8f9fa,stroke:#6c757d,stroke-width:2px,color:#6c757d;
    classDef trust fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#1b5e20;

    class CONSOLE,operator,chat console;
    class ENGINE,plan,PROBES,ptp,metal3,redfish,smo,tax,guard engine;
    class DATA,LIVE,OFFLINE,wrappers,stubs data;
    class TRUST,report,conform trust;
```

---

## The Read-Before-Write Philosophy

To establish human trust, the harness enforces a **strict split between read-only discovery probes and write-capable remediation execution**:

The `/oran-discover` commands are deliberately read-before-write. They inspect PTP state, Metal3 state, Redfish state, SMO intent state, taxonomy, and guardrails; they do not apply remediation. The assistant can use those surfaces to explain the environment, but write-capable action remains behind the harness-walker, guardrail engine, sandbox verdict, AuditEvent, and operator co-authorization path.

### 1. The Six Discovery Probes
*   **`:ptp` (`ptp.md`):** Collects raw PTP synchronization events, PHC offsets, and `cloud-event-proxy` states, explaining their **IEEE 1588 / G.8275.1** lineage.
*   **`:metal3` (`metal3.md`):** Inspects host platform and bare-metal firmware states behind **O-RAN O2ims** shapes.
*   **`:redfish` (`redfish.md`):** Verifies out-of-band server BMC statuses without exposing direct writing APIs.
*   **`:smo` (`smo.md`):** Inspects TMF921-shaped intent envelopes and active maintenance window timelines.
*   **`:taxonomy` (`taxonomy.md`):** Exposes the 20-entry routing taxonomy, validating the O-Cloud layer boundaries.
*   **`:guardrail` (`guardrail.md`):** Checks policy caps, allowlists, and whether the NOC supervisor has toggled `crisis_mode`.

### 2. Pre-Flight Orchestration (`:plan`)
Before any remediation write is authorized, the operator invokes `/oran-discover:plan`. This probe runs a sequential pre-flight check across all six probes, compiling their outputs into a single diagnostic report card. The operator can visually inspect this card, confirm that the evidence supports the proposed fix, and promote the remediation proposal with confidence.
