"""Simple text-based status dashboard for cronwrap job history."""
from __future__ import annotations
import os
from typing import List, Optional
from cronwrap.history import HistoryStore, HistoryConfig, HistoryEntry


def _status_symbol(success: bool) -> str:
    return "✓" if success else "✗"


def _format_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"{minutes}m {secs:.0f}s"


def render_dashboard(entries: List[HistoryEntry], job_name: Optional[str] = None, last_n: int = 10) -> str:
    lines = []
    title = f"cronwrap dashboard — {job_name}" if job_name else "cronwrap dashboard"
    lines.append(title)
    lines.append("=" * len(title))

    if not entries:
        lines.append("No history available.")
        return "\n".join(lines)

    recent = entries[-last_n:]
    total = len(recent)
    successes = sum(1 for e in recent if e.success)
    lines.append(f"Last {total} runs: {successes}/{total} succeeded")
    lines.append("")
    lines.append(f"{'#':<4} {'Status':<8} {'Started':<22} {'Duration':<12} {'Exit':<6}")
    lines.append("-" * 56)
    for i, entry in enumerate(reversed(recent), 1):
        sym = _status_symbol(entry.success)
        dur = _format_duration(entry.duration)
        lines.append(f"{i:<4} {sym:<8} {entry.started_at:<22} {dur:<12} {entry.exit_code:<6}")

    return "\n".join(lines)


def print_dashboard(job_name: Optional[str] = None, last_n: int = 10) -> None:
    config = HistoryConfig.from_env()
    store = HistoryStore(config)
    entries = store.load(job_name)
    print(render_dashboard(entries, job_name=job_name, last_n=last_n))
