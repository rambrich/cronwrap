"""Window execution report: summarize OutsideWindowError occurrences across runs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class WindowViolation:
    """A single record of a window constraint violation."""
    timestamp: str
    command: str
    reason: str
    window_spec: str = ""


@dataclass
class WindowSummary:
    """Aggregated summary of window violations."""
    total_violations: int = 0
    commands: dict = field(default_factory=dict)  # command -> count
    reasons: List[str] = field(default_factory=list)


def summarize_violations(violations: List[WindowViolation]) -> WindowSummary:
    """Aggregate a list of WindowViolation records into a summary."""
    summary = WindowSummary(total_violations=len(violations))
    for v in violations:
        summary.commands[v.command] = summary.commands.get(v.command, 0) + 1
        summary.reasons.append(v.reason)
    return summary


def render_report(
    violations: List[WindowViolation],
    title: str = "Window Violation Report",
) -> str:
    """Render a human-readable report of window violations.

    Args:
        violations: List of WindowViolation instances to report on.
        title: Optional title string for the report header.

    Returns:
        A formatted multi-line string report.
    """
    lines: List[str] = []
    lines.append(f"=== {title} ===")

    if not violations:
        lines.append("No window violations recorded.")
        return "\n".join(lines)

    summary = summarize_violations(violations)
    lines.append(f"Total violations : {summary.total_violations}")
    lines.append("")

    # Per-command breakdown
    if summary.commands:
        lines.append("Violations by command:")
        for cmd, count in sorted(summary.commands.items(), key=lambda x: -x[1]):
            lines.append(f"  {cmd!r:40s}  {count}")
        lines.append("")

    # Detail rows
    lines.append(f"{'Timestamp':<26}  {'Command':<30}  Reason")
    lines.append("-" * 80)
    for v in violations:
        cmd_short = v.command[:28] + ".." if len(v.command) > 30 else v.command
        lines.append(f"{v.timestamp:<26}  {cmd_short:<30}  {v.reason}")

    return "\n".join(lines)


def print_report(
    violations: List[WindowViolation],
    title: str = "Window Violation Report",
) -> None:
    """Print the window violation report to stdout."""
    print(render_report(violations, title=title))
