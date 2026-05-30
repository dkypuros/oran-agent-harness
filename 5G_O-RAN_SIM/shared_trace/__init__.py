"""Shared JSON trace layer for cross-stage replay analysis.

File-based persistence pattern: one JSONL file per scenario, append-only,
each line is one stage record. No database. See README.md for the rationale.
"""

from .writer import append_trace

__all__ = ["append_trace"]
