---
title: "Talk track, 25 minutes, spoken voice"
author: David Kypuros
venue: O-RAN nGRG Workshop, Seattle
date: 4th [THU] JUN 2026
license: Apache-2.0
status: speaker script, follows the 9-slide pacing in talk/runsheet_25min.md
voice_reference: /Users/davidkypuros/Documents/Git_Offline/active/10.WORK_IBM_RedHat-BOOKMARK/8_Red-Hat_promotion_2026_v2/4_talk_track_v1/talk_track/9_talk_track_final.txt
note: |
  Speaker script in David's voice. Em dashes converted to commas, periods,
  or parentheses to satisfy the bench's em-dash discipline. Slide cues in
  brackets. Demo prompts are quoted verbatim from talk/demo_logs/.
---

# Talk track, 25 minutes

Good afternoon, my name is David Kypuros, Global Principal Solutions Architect at Red Hat, and thank you to the nGRG organizers for the opportunity to be here today.

So what I want to walk you through is a research bench we've built called the O-RAN Agent Harness. It's a closed-loop day-2 remediation system for multivendor Cloud RAN, and what's interesting about it is that it's not just an architecture diagram. It's a runnable bench. Everything I'm going to show you, you can clone from GitHub and have running on a MacBook in about 60 seconds.

The talk title is *From Multivendor Diagnosis to Closed-Loop Remediation*. And the From half of that title is what I want to start with, because that's the day this work is built to retire.


Slide 2: A day in multivendor diagnosis without the harness
-------------------------------------------------------------------------

So, picture this. It's 9:14 a.m. on a Tuesday in 2026. The on-call NOC engineer at a Tier-1 operator gets a PagerDuty alert. PTP holdover at site X12, two cells degraded, voice quality SLI dropping. Two cells means about 480 connected handsets right now. And here's what really matters, the SLA penalty math: those cells fall outside the contracted four-nines window inside seven minutes. So the clock is already running.

The site is multivendor. The vDU is one vendor. The radios are a different vendor. The cell-site router is a third. The host platform is OpenShift on bare-metal Dell hardware. The PTP grandmaster is a Microchip box. And what happens next is the day-2 status quo.

The on-call engineer opens five tools, basically in this order. Splunk for the PTP events. The vDU vendor's element manager. Red Hat ACM for the cluster. Grafana for the host platform board. And then the radio EMS. Each one shows a partial truth. Splunk says PTP recovered. The vDU EMS says cell sync is still alarmed. ACM says the cluster is healthy. Grafana shows the NIC tx-hardware-timestamp-timeouts counter on one worker node climbing past 4,000. The radios are happy.

So the engineer now has five partial truths, and the cause is somewhere in the gap between consoles two and four. The vDU thinks PTP is bad. The linuxptp daemon says it's fine. Except on one node where the hardware-timestamping path is degrading.

Here's the thing: the engineer doesn't know all of that. The runbook is six clicks deep in Confluence. The Singapore engineer who knows the Intel ice driver story by heart is asleep. So they open a Jira ticket. Severity 2. The host platform team acknowledges in 18 minutes. By then the cells have crossed the SLA threshold. The customer-side commercial team is paged. Three vendors are on a bridge call. By the time someone identifies the root cause and proposes the fix, 47 minutes have elapsed. The SLA window is gone. The fix itself takes 9 minutes.

That's the From half of the title. The harness doesn't eliminate the ambiguity, the firmware-driver-PHC boundary is real. What the harness does is take the diagnosis-to-action path off the human's critical path. Let me show you how.


Slide 3: The 7-box architecture macro
-------------------------------------------------------------------------

So here's the mental map. Seven boxes. You can see it on the slide.

On the left is the observation loop. linuxptp running as a daemon, the NIC PHC, the cloud-event-proxy sidecar publishing O-RAN CloudEvents. Standard stack, you all know this.

In the middle is the agent harness itself. Agentic gateway, three domain agents (Platform, RAN, Hardware), a remediation router, a guardrail engine. And underneath all of that, sitting horizontally as a substrate, is the Digital Twin. I'll come back to the twin in a minute.

On top of the middle box is the killswitch. Crisis mode override. That's the operator's reserve power for macro events, hurricanes, lightning storms, security incidents.

And on the right are two routes. The up route is a TMF921 intent emitted to the partner SMO. The down route is the O-RAN O2 IMS API into the O-Cloud Manager.

Now here's the novelty claim, and I want to land this one before the demo because it's the thing the rest of the talk hangs from.

The novelty is the 2+3+8+9 conjunction. Refs 2 and 3 are the O-RAN O2 General Aspects and Principles spec and the O-RAN O2 IMS Interface Specification. That's the SMO-to-O-Cloud boundary. Refs 8 and 9 are the Kubernetes-native delivery contracts: Metal3 BareMetalHost and HostFirmwareComponents on one side, and the OpenShift Machine Config Operator on the other.

What's novel is not any one of these four. Each is well-known. What's novel is what they do as an assembly when you make them carry a single remediation proposal end to end. The boundary is the O-RAN spec. The delivery inside is the production Kubernetes contracts that already run on every O-Cloud cluster today. Most prior agentic-RAN work either stops at the SMO boundary without a delivery story, or it proposes a custom controller plane that side-steps O-RAN's own resource layering. The 2+3+8+9 conjunction avoids both. And we're going to see it fire end-to-end in the demo.


Slide 4: The cognitive middle
-------------------------------------------------------------------------

So let's double-click on the middle. You can see the taxonomy.yaml on the screen. There are 20 entries in there, all grounded in the O-RAN WG6 O-Cloud resource model. Each entry has an id, a target layer, an O-RAN spec anchor, a description, a routing hint.

When a fault payload comes in from the observation loop, the router does a deterministic lookup first. Taxonomy match, target layer, confidence. And here's what's important: the great majority of faults resolve right there. No LLM. Just a YAML lookup against the resource model.

Only when the taxonomy resolves to ambiguous does the router invoke the LLM. And even then, the LLM is bounded. It's a disambiguator over the candidate classifications, not a decision-maker. The response gets recorded in a knowledge-base-lookups field on the audit event so you have a complete trail of when the model was asked and what it said.

That architectural commitment is what separates this from the typical agentic-X demo you've all seen. Most demos hand everything to the model. This one routes by taxonomy first and asks the model only on the residual. The deterministic path is auditable. The LLM path is bounded. Both are observable.

And here's the other thing about the LLM substrate. There's a unified inference client. Anthropic Claude, OpenAI GPT, or a vLLM endpoint running on OpenShift AI. You configure the provider via env var. The bench is LLM-neutral by design. So if a telco wants to run this disconnected with their own model on a local vLLM endpoint, the contracts don't change. The router code doesn't change. Just the env var.

Cognitive middle on top of the Digital Twin substrate. EvalOps measuring agent quality continuously. The router producing structured Proposals that flow out to the right side of the architecture. That's section 4.


Slide 5: The routing decision, high side TMF921, low side O2 IMS plus CRDs
-------------------------------------------------------------------------

Now the right side. This is the dual-route teaching moment.

The routing rule splits actions by O-RAN resource layer. High side, service layer: cell re-home, RAN parameter changes, slice intent updates, vDU software version rollouts. These belong to the partner SMO. Ericsson, Nokia, Amdocs, Mavenir, ZTE, depending on the operator. The harness does not execute service-layer actions. It emits a TMF921 intent and observes the result. That's the harness's respect for the service-execution boundary.

Low side, infrastructure layer: MachineConfig, KMM Module CR for driver swaps, Metal3 HostFirmwareComponents for node firmware, PerformanceProfile via the Node Tuning Operator, SR-IOV. Every one of these flows into the O-Cloud via the O-RAN O2 IMS API. Red Hat's open-source O-Cloud Manager, openshift-kni/oran-o2ims, is the reference O2 IMS implementation cited throughout this work.

So that's the routing rule for most remediations. Up or down based on resource layer.

But here's the interesting part. Some scenarios cross the boundary by their nature. A NIC firmware update is the canonical example. The action itself is infrastructure layer. You're pushing firmware via Metal3 to a Redfish endpoint on the BMC. But the consequence, a node reboot that takes cells offline for about 8 minutes, is a service-layer concern. The partner SMO needs to pre-handover cells before the reboot, or those UEs drop.

So the routing rule fires both branches at the same time. The Metal3 apply goes down through O2 IMS. The TMF921 companion intent goes up to the partner SMO. Two routes in parallel, neither vendor loses authority. That's the dual-route pattern. And that's what I'm going to fire live in the demo.

Now, a reviewer here might ask about transaction atomicity. Fair question, and I want to be precise. The dual-route is parallel emission, not a distributed two-phase commit. All three reconciliation mechanisms are implemented in v0 of the bench, end to end, and exercised by the test suite. First, the Sandbox runs the proposed Metal3 apply against the Digital Twin BEFORE the live commit, and the guardrail engine blocks the apply if the twin does not converge. Second, the SMO's response to the TMF921 companion intent is captured as a `dispatch_result` field on the AuditEvent BEFORE operator co-authorization, so the operator sees both routes' outcomes before signing. There's a fifth scenario in the repo, scenario E_with_smo_reject, that demonstrates the rejection path: same firmware push as scenario E, different worker, SMO says no because neighboring cells are at capacity. Third, the Killswitch (crisis_mode) is the global abort if reconciliation fails mid-flight. All three are file-path anchored in the reviewer FAQ Q14 and proven by the test suite at 8 out of 8 pass. The architectural commitment is operator-mediated reconciliation; distributed two-phase commit is out of scope for v0 and is the Day-3 multi-site coordination workstream.


Slide 6: Live demo
-------------------------------------------------------------------------

OK, let's actually run it. What you're going to see now is a chat interface running on a MacBook in my office. The whole stack is 9 Docker containers. The harness walker, the four platform stubs (PTP, Metal3, Redfish, TMF921 SMO), a trace viewer, a fake vLLM mock, a dashboard, and the tiny agent runtime we're calling oh-my-tiny-oran. The dashboard has a chat tab that talks to oh-my-tiny-oran. It uses my Anthropic API key to drive an agent loop against the lab's HTTP wrappers and the committed repo files. Two read-only tools. No write paths.

I'm going to paste two prompts. The first is the pre-flight survey. The second is the dual-route exercise. Both prompts were captured working end-to-end on this machine yesterday, the transcripts are in the repo under talk/demo_logs.

First prompt. I'm typing: /oran-discover:plan

And you can see the agent take off. What it's doing is reading six discovery skill markdowns (PTP, Metal3, Redfish, SMO, taxonomy, guardrail), then hitting the lab's HTTP wrappers for live state, then synthesizing a one-page survey. Takes about 30 seconds, maybe 10 tool calls. Cost at Haiku 4.5 pricing is about half a cent.

And here's what it tells us. Left loop is quiet. No PTP alarms published. Infrastructure side is quiet too, no Metal3 phases in flight, no Redfish tasks. There are two remediation proposals staged from earlier scenario walks, both pending operator approval, both routed deterministically to infra layer with high confidence. Guardrails pass on both. Dry run defaults are true. Crisis mode is not active. That's the resting state of the lab.

Now I want to see what dual-route looks like in flight. So second prompt. I'm pasting:

"Now actually fire scenario E by calling the harness walker's /run/E_nic_firmware_update endpoint. Then re-check /oran-discover:metal3 and /oran-discover:smo to show me the dual-route really happened. Compare before and after."

You can see what the agent does. It captures the before state. metal3 stub at zero, tmf921 stub at zero. Then it calls /run/E_nic_firmware_update on the harness walker. That single call walks the full pipeline: ingests the fault payload, runs the deterministic taxonomy lookup, gets a node_firmware match, evaluates guardrails, builds the RemediationProposal, attaches the companion_intent, emits the audit event.

The audit event comes back with companion_intent_attached: true. That's the dual-route flag.

Then the agent re-curls metal3 and smo. And you can see in the response: the Metal3 BMO logged 5 firmware phases. Preparing, Pushing, Rebooting, Verifying, Updated. 41.9 MB firmware blob transferred. The Redfish BMC task lifecycle moved from Running to Completed. And in parallel, a TMF921 MaintenanceWindowNotification went up to the partner SMO. Affected resources: worker-ran-02 dot dallas dot example dot com. Window: 8 minutes. Expected handover count: 47.

That's the 2+3+8+9 conjunction in motion. Refs 2 and 3 are the O-RAN boundary the action crossed. Ref 8 is the Metal3 delivery contract inside. Plus ref 7 for the BareMetalOperator, refs 18 and 19 for the TMF688 and TMF921 envelopes, refs 26 through 31 for the IEEE 1588 and CloudEvents 1.0 and O-RAN WG6 Notification API observation chain, and ref 46 for the DMTF Redfish BMC interface. About half the bibliography exercised in one chat turn. 22 seconds, 13 tool calls, about a tenth of a cent.

Without the harness, that's a 47-minute multivendor incident. With the harness, the operator sees a populated TMF688 audit event with a complete reversibility profile and a companion intent already in flight to the SMO. Sign and apply.

Next slide.


Slide 7: Trust loop
-------------------------------------------------------------------------

So the three contributions get a closed-loop system to ship. They don't get it trusted in production. The trust layer sits on top, and this is the part the audience here, the working-group folks, are going to push hardest on. So let me lay it out.

Three activities run on a Digital Twin substrate. The twin is the floor. Same-topology mirrored cluster, or a simulated linuxptp plus NIC driver stack. The bench is twin-substrate-neutral.

Activity one is EvalOps. Continuous measurement of agent quality on the twin. Per taxonomy entry, historical accuracy of both the deterministic classifier and the LLM-assist tier. Drift in either signal means either the taxonomy needs an entry or the LLM provider changed behavior. EvalOps is what turns "the model said yes" into "the model has been right on this scenario class 91 percent of the time over 600 events." That's how you grade an agent in production.

Activity two is the Sandbox. Pre-validation test flight on the twin. The same MachineConfig or KMM Module CR or HostFirmwareComponents apply that would go live. The harness observes PTP state, NIC counters, pod readiness after a settle interval. Only twins that converge inside the expected envelope produce an apply-allowed signal back to the guardrail engine. That's the two-key gate. The operator authorizes the action class. The twin authorizes the specific payload.

Activity three is Agentic Recoverability. Inverse action validation. This is the per-action undo, not disaster recovery. Disaster recovery rebuilds the house. Agentic Recoverability undoes the last paint job. RTO and RPO concepts don't apply.

The contract for the undo is the Reversibility Profile. Seven fields, same place every time, same shape every time. Rollback intent. Blast radius if reverse. Rebuild timeline. Replication history. Validation history. Risk profile burn-down. Confidence in reversibility. That's the contract between the harness and the human at decision time. No vendor doc lookup. No buried instructions. Seven fields, on the audit event, every time.

Above all three activities is the Intelligence Augmentation banner. This isn't letting AI loose in a production RAN. Agents observe and propose. The operator decides. Doug Engelbart sketched this in the 1960s as the goal of computing. The harness is built that way on purpose.

And then there's the killswitch. Formal name crisis_mode in guardrails.yaml. AT&T-reviewed. When a NOC supervisor activates it, all write paths get revoked. O2 IMS access gone. SMO TMF921 access gone. EvalOps confidence pinned at zero. Telemetry routed to manual human queues. Existing in-flight actions are allowed to complete or roll back. No new actions accepted. The reversibility profile rewinds one applied action. The killswitch freezes all of them. The two compose. They answer different questions.

So the trust posture, end to end: deterministic taxonomy first, LLM only on the ambiguous residual. Twin-based EvalOps for agent grading. Sandbox for payload-specific pre-validation. Agentic Recoverability for the per-action undo. ReversibilityProfile as the operator-facing contract. Killswitch as reserve power. Intelligence Augmentation as the explicit framing. That's how you trust this in production. Every contract has a file path in the repo. Every file path has a citation to a standard or a piece of upstream code.


Slide 8: Novelty positioning and repo handoff
-------------------------------------------------------------------------

So bringing it together. The bench is at github dot com slash dkypuros slash oran-agent-harness. Apache 2.0. The 2+3+8+9 conjunction is the novelty claim. The boundary at the top is the O-RAN O2 spec. The delivery inside is the production Kubernetes contracts. A single RemediationProposal travels from the cognitive layer through a standardized O-RAN interface into a concrete Kubernetes-native contract that already runs in production O-Cloud deployments. That's what makes the right-side execution path concretely operationalizable, not a paper architecture.

And the whole thing is reproducible. Clone the repo. Run macbook_lab slash run dot sh. That brings up the 8 containers in about a minute on Docker Desktop. Open the dashboard at localhost colon 8097. Click the oh-my-tiny-oran tab. Paste the two prompts I just showed you. You get the same chain firing on your machine.

The repo also has, under talk slash, a runsheet for this talk, a reviewer FAQ with 13 anticipated questions, a 5-minute pitch and a 1-minute pitch for hallway capture, and the demo logs I just walked you through. Under narratives slash, there are 5 long-form per-audience cuts: an operator-day narrative for SREs, a trust-loop framing for architects, a standards-conformance walkthrough for working-group chairs, a multivendor interop narrative for vendor PMs, and a Day-3 trajectory for workshop reviewers.

So if you want to use this as a research substrate for your own closed-loop work, the bench is durable. The talk is one moment. The bench is the artifact.


Slide 9: Q&A
-------------------------------------------------------------------------

That's the work. I'll take your questions. If we don't get to your question in the time we have, the reviewer FAQ in the repo covers the 13 most-anticipated ones, citation-anchored, and I'm here through the rest of the day for follow-up.

Thank you.
