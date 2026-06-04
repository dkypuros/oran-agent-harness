# The O2ims-to-Operator-CRD Bridge

This document details the **O2ims-to-Operator-CRD Bridge (Bridge 3)**. It zooms in on the crucial interface boundary where high-level, software-layer remediation proposals are translated and dispatched down to Kubernetes-native CRD controllers and physical hardware without inventing a parallel, non-standard control plane.

## Infrastructure Handoff Diagram

The following Mermaid diagram visualizes how a unified `RemediationProposal` is converted into standard O-RAN O2ims API calls and routed to dedicated cluster reconcilers and server BMCs.

```mermaid
graph TD
    %% Source
    subgraph SMO ["Service Management & Orchestration (SMO)"]
        proposal["RemediationProposal<br>(harness/schemas/RemediationProposal.json)"]
    end

    %% Standard Handoff Boundary
    subgraph OCLOUD ["O-Cloud Infrastructure Manager Tier"]
        o2ims["O-RAN O2ims API<br>(Infrastructure Management Service)"]
        ocm["Red Hat O-Cloud Manager<br>(5G_O-RAN_SIM/oam/o2ims_stub.py)"]

        o2ims --> ocm
    end

    %% Kubernetes API Controller Plane
    subgraph K8S ["Kubernetes Platform Controller Plane"]
        k8s_api["Kubernetes API Server"]

        subgraph CRDS ["Target Custom Resource Definitions (CRDs)"]
            mc["MachineConfig CRD<br>(MCO Schema)"]
            kmm_mod["Module CRD<br>(KMM v1beta1 Schema)"]
            bmh["BareMetalHost CRD<br>(Metal3 BMO Schema)"]
            hfc["HostFirmwareComponents CRD<br>(Metal3 BMO Schema)"]
        end

        k8s_api --> mc
        k8s_api --> kmm_mod
        k8s_api --> bmh
        k8s_api --> hfc
    end

    %% Specific Operators (The Reconcilers)
    subgraph RECONCILERS ["Kubernetes-Native Operators"]
        mco["Machine Config Operator (MCO)"]
        kmm["Kernel Module Management (KMM)"]
        bmo["Metal3 BareMetal Operator (BMO)"]
    end

    %% Out-of-Band Hardware Tier
    subgraph HW ["Out-of-Band Physical Hardware Tier"]
        bmc["BMC (Baseboard Management Controller)"]
        redfish["DMTF Redfish API<br>(UpdateService.SimpleUpdate)"]
        nic["Physical Network Interface Card<br>(Intel E810 / PHC)"]

        bmc --> redfish
        redfish --> nic
    end

    %% Trajectories
    proposal == "1. Dispatch Remediate" ==> o2ims
    ocm == "2. Reconcile Target State" ==> k8s_api

    %% Operator Enforcements
    mc ==> mco
    kmm_mod ==> kmm
    bmh ==> bmo
    hfc ==> bmo

    %% Real-world execution outcomes
    mco ==> |"3a. Host Configuration Write"| nic
    kmm ==> |"3b. Driver Swap / Modprobe"| nic
    bmo ==> |"3c. Out-of-Band Config"| bmc

    %% Custom Styling
    classDef smo fill:#fff3e0,stroke:#ef6c00,stroke-width:2px,color:#e65100;
    classDef o2 fill:#cfe2ff,stroke:#0d6efd,stroke-width:2px,color:#084298;
    classDef k8s fill:#e3f2fd,stroke:#1565c0,stroke-width:2px,color:#0d47a1;
    classDef op fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#1b5e20;
    classDef hw fill:#ffebee,stroke:#c62828,stroke-width:2px,color:#b71c1c;

    class SMO,proposal smo;
    class OCLOUD,o2ims,ocm o2;
    class K8S,k8s_api,mc,kmm_mod,bmh,hfc k8s;
    class RECONCILERS,mco,kmm,bmo op;
    class HW,bmc,redfish,nic hw;
```

---

## The Core Novelty: Architectural Composition

Existing closed-loop automation products frequently invent proprietary, vertical agent channels that bypass standard structures. The **O2ims-to-Operator-CRD Bridge** enforces a clean horizontal division of labor:

1.  **High-Level Taxonomy Routing:** High-level diagnostic facts are structured inside `RemediationProposal.json`.
2.  **O-RAN Standard Entry:** The SMO dispatches this proposal across the standardized **O-RAN O2ims API** boundary down to the local O-Cloud Manager.
3.  **Kubernetes-Native Translation:** The O-Cloud Manager translates the O2ims request into native Kubernetes resource manifests, avoiding any vendor-proprietary platform APIs.
4.  **Dedicated Reconciler Execution:** Three standard, pre-existing cluster operators handle the actual change:
    *   **MCO (`harness/routing-rules` / Scenario A):** Writes direct host OS configuration changes.
    *   **KMM (`harness/routing-rules` / Scenario A'):** Deploys out-of-tree hardware kernel modules for NIC driver swaps.
    *   **Metal3 BMO (`harness/routing-rules` / Scenario E):** Executes out-of-band firmware updates through BMCs via DMTF Redfish.
