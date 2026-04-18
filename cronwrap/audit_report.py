"""Generate a simple text report from audit log entries."""
from __future__ import annotations

from collections import Counter
from typing import List

from cronwrap.audit import AuditEntry


def summarize_entries(entries: List[AuditEntry]) -> dict:
    """Return aggregate statistics over a list of audit entries."""
    if not entries:
        return {"total": 0, "successes": 0, "failures": 0, "avg_duration": 0.0,
                "commands": {}}
    total = len(entries)
    successes = sum(1 for e in entries if e.success)
    failures = total - successes
    avg_duration = sum(e.duration for e in entries) / total
    command_counts: Counter = Counter(e.command for e in entries)
    return {
        "total": total,
        "successes": successes,
        "failures": failures,
        "avg_duration": round(avg_duration, 3),
        "commands": dict(command_counts),
    }


def render_report(entries: List[AuditEntry]) -> str:
    """Render a human-readable audit report string."""
    stats = summarize_entries(entries)
    lines = [
        "=== Cronwrap Audit Report ===",
        f"Total runs   : {stats['total']}",
        f"Successes    : {stats['successes']}",
        f"Failures     : {stats['failures']}",
        f"Avg duration : {stats['avg_duration']}s",
        "",
        "Commands:",
    ]
    for cmd, count in sorted(stats["commands"].items(), key=lambda x: -x[1]):
        lines.append(f"  {count:>4}x  {cmd}")
    return "\n".join(lines)


def print_report(entries: List[AuditEntry]) -> None:  # pragma: no cover
    print(render_report(entries))
