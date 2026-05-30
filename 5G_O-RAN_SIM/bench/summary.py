"""5G_O-RAN_SIM bench summary writer.

Conforms to:
  harness-unique orchestration, no upstream spec
Bibliography refs: n/a

Produces a comparative markdown summary across the 4 scenarios.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

_BENCH_DIR = Path(__file__).resolve().parent
_SUMMARY_PATH = _BENCH_DIR / "last_run_summary.md"


def summarize(report: dict[str, Any]) -> str:
    """Render the bench report as a comparative markdown table."""
    summary = report.get("summary", {})
    per_scenario = summary.get("per_scenario", [])

    lines: list[str] = []
    lines.append("# 5G_O-RAN_SIM bench last-run summary")
    lines.append("")
    lines.append(f"- Scenarios run: {summary.get('scenario_count', 0)}")
    lines.append(
        f"- Scenarios with companion intent: "
        f"{summary.get('scenarios_with_companion_intent', 0)}"
    )
    lines.append(
        f"- Total duration: {summary.get('total_duration_seconds', 0.0)} seconds"
    )
    lines.append("")
    lines.append("## Per-scenario comparison")
    lines.append("")
    lines.append(
        "| Scenario | Fault ID | Target | Action | Blast cells | Companion intent | Duration (s) |"
    )
    lines.append(
        "|---|---|---|---|---|---|---|"
    )
    for s in per_scenario:
        lines.append(
            f"| {s['scenario_id']} | {s['fault_id']} | {s.get('target_layer', '')} "
            f"| {s.get('action_type', '')} | {s.get('blast_cells', '')} "
            f"| {'yes' if s.get('companion_intent_attached') else 'no'} "
            f"| {s.get('duration_seconds', 0.0)} |"
        )
    lines.append("")
    lines.append("## Trace files")
    lines.append("")
    for s in per_scenario:
        lines.append(f"- `{s['trace_path']}`")
    lines.append("")
    lines.append(
        "Open `5G_O-RAN_SIM/dashboard/trace_view/` for the visual timeline view."
    )
    return "\n".join(lines) + "\n"


def write_summary(markdown: str) -> Path:
    """Write the markdown summary to bench/last_run_summary.md and return the path."""
    _SUMMARY_PATH.write_text(markdown, encoding="utf-8")
    return _SUMMARY_PATH
