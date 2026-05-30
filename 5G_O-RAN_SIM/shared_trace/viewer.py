"""Shared trace viewer for 5G_O-RAN_SIM JSONL traces.

Conforms to:
  harness-unique persistence pattern, no upstream spec
Bibliography refs: n/a

CLI: python -m shared_trace.viewer <scenario_id> [--json]
  Prints the per-scenario trace as a human-readable timeline by default, or
  raw JSONL with --json.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_TRACE_DIR = Path(__file__).resolve().parent


def _load_records(path: Path) -> list[dict]:
    records: list[dict] = []
    if not path.exists():
        return records
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records


def _print_timeline(records: list[dict]) -> None:
    if not records:
        print("(no records)")
        return
    print(f"{'TIMESTAMP':<27} {'STAGE':<22} SUMMARY")
    print("-" * 100)
    for rec in records:
        ts = rec.get("ts", "")[:26]
        stage = rec.get("stage", "")[:22]
        summary_fields = {k: v for k, v in rec.items() if k not in {"ts", "scenario_id", "stage"}}
        summary = json.dumps(summary_fields)[:80]
        print(f"{ts:<27} {stage:<22} {summary}")


def _print_raw(records: list[dict]) -> None:
    for rec in records:
        print(json.dumps(rec))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="View a 5G_O-RAN_SIM trace file")
    parser.add_argument("scenario_id", help="Scenario id, e.g. D_phc_drift_hw_only")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print raw JSONL instead of the human-readable timeline",
    )
    parser.add_argument(
        "--example",
        action="store_true",
        help="Read the committed .example.jsonl variant instead of the runtime file",
    )
    args = parser.parse_args(argv)

    suffix = ".example.jsonl" if args.example else ".jsonl"
    path = _TRACE_DIR / f"{args.scenario_id}{suffix}"
    records = _load_records(path)
    if args.json:
        _print_raw(records)
    else:
        print(f"Trace: {path}")
        print(f"Records: {len(records)}")
        print()
        _print_timeline(records)
    return 0


if __name__ == "__main__":
    sys.exit(main())
