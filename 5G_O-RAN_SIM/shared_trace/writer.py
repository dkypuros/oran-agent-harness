"""Shared JSON trace writer for the 5G_O-RAN_SIM platform substrate.

Conforms to:
  harness-unique persistence pattern, no upstream spec
Bibliography refs: n/a (harness-defined)

File-based trace persistence. Every pipeline stage appends one JSON record to
a per-scenario JSONL file. No database. Runtime traces are gitignored;
committed example traces use the .example.jsonl suffix.

Exposes:
  append_trace(scenario_id, stage, payload) -> None
    Adds one timestamped record to 5G_O-RAN_SIM/shared_trace/{scenario_id}.jsonl.
    Filesystem errors are swallowed (best effort); never raises in the demo path.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_TRACE_DIR = Path(__file__).resolve().parent


def append_trace(scenario_id: str, stage: str, payload: dict[str, Any]) -> None:
    """Append one JSON line to the per-scenario trace file.

    Args:
      scenario_id: identifier matching the scenario folder, e.g. "D_phc_drift_hw_only"
      stage: which pipeline stage emitted this record, e.g. "ptp_operator", "router"
      payload: any JSON-serializable dict carrying stage-specific data

    Side effects:
      Writes one line of JSON to 5G_O-RAN_SIM/shared_trace/{scenario_id}.jsonl.
      ISO 8601 timestamp added automatically as the first record field.
      Never raises; filesystem errors are swallowed so the demo path stays clean.
    """
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "scenario_id": scenario_id,
        "stage": stage,
        **payload,
    }
    target = _TRACE_DIR / f"{scenario_id}.jsonl"
    try:
        with target.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")
    except Exception:
        pass
