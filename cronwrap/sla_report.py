"""SLA report rendering utilities."""
from __future__ import annotations

from typing import List

from cronwrap.sla import SLAViolation


def summarize_violations(violations: List[SLAViolation]) -> dict:
    if not violations:
        return {"total": 0, "by_reason": {}, "jobs": []}
    by_reason: dict = {}
    jobs = set()
    for v in violations:
        by_reason[v.reason] = by_reason.get(v.reason, 0) + 1
        jobs.add(v.job_name)
    return {
        "total": len(violations),
        "by_reason": by_reason,
        "jobs": sorted(jobs),
    }


def render_report(violations: List[SLAViolation]) -> str:
    summary = summarize_violations(violations)
    lines = [
        "=== SLA Violation Report ===",
        f"Total violations : {summary['total']}",
        f"Affected jobs    : {', '.join(summary['jobs']) or 'none'}",
        "",
        "By reason:",
    ]
    for reason, count in summary["by_reason"].items():
        lines.append(f"  {reason}: {count}")
    if violations:
        lines.append("")
        lines.append("Details:")
        for v in violations:
            import time
            ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(v.timestamp))
            lines.append(
                f"  [{ts}] {v.job_name} — {v.reason} "
                f"(value={v.value:.2f}, threshold={v.threshold:.2f})"
            )
    return "\n".join(lines)


def print_report(violations: List[SLAViolation]) -> None:
    print(render_report(violations))
