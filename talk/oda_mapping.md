---
title: "ODA Agentic Intent-Driven Closed Loop Flow: TM Forum Reference Mapping"
author: David Kypuros
venue: O-RAN nGRG Workshop, Seattle
date: 4th [THU] JUN 2026
license: Apache-2.0
source: Architectural Support Appendix lifted from architecture_bibliography.txt section J
---

# ODA Agentic Intent-Driven Closed Loop Flow, TM Forum Reference Mapping

This document maps each labeled element in the ODA Agentic Intent-Driven Closed Loop Flow diagram to the
official TM Forum reference that supports it. Used to justify the Red Hat positioning argument: the platform
sits as the ODA Canvas Base, with intelligence and service execution in standards-defined domains above it.

| # | Element                        | Reference                                                                  | Description                                                                                                                              |
|---|---------------------------------|----------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------|
| 1 | Identity and Access Management  | TMF720 Digital Identity Management API, ODA Canvas IAM                     | Proves access control is an overarching Canvas governance feature, not a proprietary Red Hat lock-in.                                    |
| 2 | Security API                    | TMF630 (API Design Guidelines, with API security profile)                  | Standardizes how components authenticate, reinforcing the separation of concerns. Note: TMF630 canonical title is "REST API Design Guidelines." API security in TM Forum is layered on top via the Open API Security profile. Cite both where strict accuracy is required. |
| 3 | Standardized Event Bus          | TMF688 Event Management API                                                | Proves infrastructure telemetry (Red Hat / Kafka) must standardize its events to pass them up to the intelligence layer, rather than executing logic natively. Crucial for the Red Hat positioning argument.                                                       |
| 4 | Intelligence Management Domain  | IG1228 AIOps and Intelligence Management Domain Implementation Guide       | The official ODA domain for AI. Confirms that intelligence sits apart from the underlying cloud execution platform.                       |
| 5 | Model Registry                  | TMF902 AI Model Management API                                             | Standardizes the onboarding and tracking of AI models, keeping them agnostic of the infrastructure layer.                                 |
| 6 | Model as a Service              | TMF902 AI Model Management API                                             | Governs how the intelligence layer exposes analytical models to the Agent Fabric for inference.                                           |
| 7 | Knowledge Base (RAG)            | GB922 Information Framework (SID) Concepts and Principles                  | The TM Forum SID provides the standardized telecom data context. Proves that parsing telecom anomalies requires telecom data structures that a generic cloud platform does not have.                                                                                |
| 8 | Agent Fabric                    | TM Forum Project ONE (Agentic ODA Canvas Extension)                        | TM Forum's official Project ONE initiative defines the AI-Native Canvas extensions for agent collaboration.                              |
| 9 | AI Secure Gateway               | ODA AI-Native Canvas (Guardrails)                                          | An emerging ODA Canvas component that enforces enterprise guardrails, auditing, and observability before AI models act on network data.   |
|10 | Agent Orchestrator              | IG1253D Intent Manager Implementation Guide, TMF921 Intent Management API  | Critical to the architectural argument. The Intent Manager does not execute fixes; it translates the AI's decision into a standard intent (TMF921) to hand off to the Domain Orchestrator.                                                                          |
|11 | Production Domain               | GB999 ODA Production Implementation Guidelines                             | TM Forum's blueprint for the domain that actually executes telecom services. Proves that Service and Resource management are distinctly separate from the Canvas Base. Note: GB999 attribution should be verified against the current TM Forum library; ODA production implementation guidance is also covered by IG1171 (ODA Component Definition) and IG1230 (ODA Production Implementation). Cite the most current of these for a formal submission. |
|12 | Service Operations Layer        | IG1190 ODA Functional Architecture                                         | Validates that a dedicated layer exists for managing the lifecycle of telecom services (the Ericsson / Amdocs layer), sitting above the infrastructure.                                                                                                            |
|13 | Domain Orchestrator             | TMF641 Service Order Management API and IG1253                             | The entity that receives the intent and orchestrates the specific steps across the network to fix the issue. For example, the Ericsson PTP sync fix executed via the Domain Orchestrator.                                                                          |
|14 | Service Management              | TMF639 Service Inventory Management API                                    | Maintains the real-time state of the network service. Without this, no closed loop can safely occur, and a cloud infrastructure layer does not possess this context.                                                                                                |
|15 | Service Catalog                 | TMF633 Service Catalog Management API                                      | Defines the allowable configurations and parameters for the telecom services being managed.                                              |

## Example flow (illustrative narrative)

The telemetry flows via TMF688 up to the IG1228 Intelligence Management Domain. The AI uses GB922 SID
context to characterize the problem and issues a TMF921 Intent to the IG1190 Service Operations Layer. The
Domain Orchestrator then executes the fix.

This example flow shows that Red Hat can create an orchestrator that leverages the partner Domain
Orchestrator as the overall solution, without claiming the service-execution role itself.

## Notes on appendix accuracy

i.   The diagram references in this appendix correspond to the numbered callouts (1) to (15) in the ODA
     Agentic Intent-Driven Closed Loop Flow figure used in the supporting deck. Element (16), Resource
     Operations Layer, is added separately in the broader bibliography and maps to the O-RAN O2 IMS
     interface and TMF634 Resource Inventory Management API.

ii.  TMF630 is correctly the REST API Design Guidelines document. API security in TM Forum is governed by
     the API Security profile guidance applied to those design guidelines; some materials informally label
     this combination as "API Management and Security."

iii. The Production Domain (11) reference GB999 should be confirmed against the current TM Forum library.
     The ODA Production Implementation Guidelines have been published under multiple document identifiers
     across revisions; cite the active version at time of submission.

iv.  Project ONE (8) is an active TM Forum initiative defining agentic extensions to the ODA Canvas; the
     specific deliverable name and version should be cited from the current TM Forum Project ONE workspace.
