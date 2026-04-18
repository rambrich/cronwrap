"""Render a summary report from trace entries."""
from __future__ import annotations

from typing import List


def summarize_traces(entries: List[dict]) -> dict:
    if not entries:
        return {"total": 0, "successes": 0, "failures": 0, "avg_duration": 0.0}
    total = len(entries)
    successes = sum(1 for e in entries if e.get("success"))
    failures = total - successes
    avg_duration = sum(e.get("duration", 0.0) for e in entries) / total
    return {
        "total": total,
        "successes": successes,
        "failures": failures,
        "avg_duration": round(avg_duration, 3),
    }


def render_trace_report(entries: List[dict]) -> str:
    summary = summarize_traces(entries)
    lines = [
        "=== Trace Report ===",
        f"Total runs : {summary['total']}",
        f"Successes  : {summary['successes']}",
        f"Failures   : {summary['failures']}",
        f"Avg duration: {summary['avg_duration']}s",
        "",
        f"{'TRACE ID':<38} {'CMD':<20} {'OK':>4} {'DUR':>7}",
        "-" * 72,
    ]
    for e in entries:
        ok = "✓" if e.get("success") else "✗"
        cmd = (e.get("command") or "")[:20]
        dur = f"{e.get('duration', 0.0):.2f}s"
        tid = e.get("trace_id", "")[:36]
        lines.append(f"{tid:<38} {cmd:<20} {ok:>4} {dur:>7}")
    return "\n".join(lines)


def print_trace_report(entries: List[dict]) -> None:
    print(render_trace_report(entries))
