---
title: "1-minute pitch, elevator version"
author: David Kypuros
venue: O-RAN nGRG Workshop, Seattle
date: 4th [THU] JUN 2026
license: Apache-2.0
status: spoken-word, 60 seconds, no slides, no demo
---

# 1-minute pitch

The version you deliver when someone asks "what do you work on?" in the elevator on the way to
the keynote. One paragraph, no preamble, names the novelty, points at the repo.

## The pitch

> Closed-loop day-2 remediation for multivendor Cloud RAN is mostly human triage across vendor
> consoles today. We built a research bench that automates the diagnosis-to-remediation path
> without taking authority from the partner SMO. A deterministic taxonomy grounded in the O-RAN
> WG6 O-Cloud resource model classifies the fault; an LLM is invoked only on the residual
> ambiguous class; the routing decision splits service-layer actions UP to the partner SMO as
> TMF921 intents and infrastructure-layer actions DOWN to the O-Cloud through the O2 IMS
> interface, delivered by Metal3 and the Machine Config Operator. That O2 IMS plus Metal3 plus
> MCO conjunction is what makes the right-side execution path concretely operationalizable on
> production Kubernetes-native O-Cloud, not just a paper architecture. The bench is at
> github.com/dkypuros/oran-agent-harness under Apache 2.0.

## Variants by lead-in cue

- **"What do you work on?"** -> use the pitch above verbatim.
- **"What did you talk about today?"** -> "I gave a 25 minute version of the same thing at the
  nGRG workshop. The bench is the durable artifact, github.com/dkypuros/oran-agent-harness."
- **"Are you with Red Hat?"** -> "Yes, Global Principal SA. This work draws on a 1+ year
  Ericsson Red Hat Intel initiative; the bench is the open-source crystallization."
- **"Can I help?"** -> "Pull the repo. The contracts are portable. If you build something on
  top, I want to see it."

## What NOT to say in 60 seconds

- Do not name vendor competitive failures by name. Stay above the line.
- Do not promise dates or features beyond the bench.
- Do not say "agent" without naming what it does. Empty "agentic" sentences read as marketing.
- Do not apologize for length. 60 seconds is the budget.
