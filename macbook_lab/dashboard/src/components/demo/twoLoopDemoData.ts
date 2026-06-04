export const evidenceCards = [
  {
    title: "PTP sync drift alarm",
    source: "ptp-operator-stub + shared trace",
    status: "hardware_anomaly",
    detail:
      "The visible entry condition is timing/PTP sync drift; offset variance triggers evidence collection before any remediation is proposed.",
  },
  {
    title: "NIC timestamp capability",
    source: "Intel NIC / PHC evidence stub",
    status: "unhealthy",
    detail:
      "The affected interface reports inconsistent hardware timestamp capability, pointing away from a pure linuxptp profile mismatch and toward NIC/PHC hardware behavior.",
  },
  {
    title: "Redfish / BMC view",
    source: "redfish-bmc-stub",
    status: "service_followup",
    detail:
      "BMC-side inventory keeps the NIC serviceable and traceable, making hardware follow-up a structured action instead of an ad-hoc ticket.",
  },
  {
    title: "Metal3 / BMO state",
    source: "metal3-bmo-stub",
    status: "node_actionable",
    detail:
      "Bare-metal ownership and node lifecycle state can support drain/isolate coordination before any hardware maintenance path.",
  },
  {
    title: "CRD / KMM / operator state",
    source: "operator-state fixture",
    status: "ruled_out_primary",
    detail:
      "Kernel/module and operator intent are represented as evidence, but the demo recommendation does not make drift the primary cause.",
  },
];

export const standardsMap = [
  "O-RAN O-Cloud notification and O2-style infrastructure handoff",
  "TM Forum intent envelope for companion remediation context",
  "Kubernetes node drain/isolate workflow",
  "Metal3/BMO and Redfish as hardware lifecycle interfaces",
  "MCP gateway guardrails as the governed tool boundary",
];
