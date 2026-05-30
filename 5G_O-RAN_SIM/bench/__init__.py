"""5G_O-RAN_SIM research bench.

Orchestrator that runs all 4 walkthrough scenarios (A, A-prime, D, E) end to
end, firing the platform stubs (PTP operator, Metal3 BMO, Redfish BMC, SMO
intent emitter) and capturing per-stage records to the shared JSONL trace
layer. Produces a comparative summary across scenarios.

See README.md for usage.
"""
