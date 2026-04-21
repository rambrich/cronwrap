"""Reporting utilities for prescan results across multiple run outputs."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from cronwrap.prescan import PrescanResult


@dataclass
class PrescanSummary:
    total: int = 0
    total_with_warnings: int = 0
    total_with_failures: int = 0
    top_warn_patterns: dict = field(default_factory=dict)
    top_fail_patterns: dict = field(default_factory=dict)


def summarize_results(results: List[Optional[PrescanResult]]) -> PrescanSummary:
    summary = PrescanSummary()
    for r in results:
        if r is None:
            continue
        summary.total += 1
        if r.has_warnings:
            summary.total_with_warnings += 1
            for p in r.matched_warn:
                summary.top_warn_patterns[p] = summary.top_warn_patterns.get(p, 0) + 1
        if r.has_failures:
            summary.total_with_failures += 1
            for p in r.matched_fail:
                summary.top_fail_patterns[p] = summary.top_fail_patterns.get(p, 0) + 1
    return summary


def render_report(summary: PrescanSummary) -> str:
    lines = [
        "=== Prescan Report ===",
        f"Total scanned    : {summary.total}",
        f"With warnings    : {summary.total_with_warnings}",
        f"With failures    : {summary.total_with_failures}",
    ]
    if summary.top_warn_patterns:
        lines.append("Top warn patterns:")
        for pattern, count in sorted(summary.top_warn_patterns.items(), key=lambda x: -x[1]):
            lines.append(f"  {pattern}: {count}")
    if summary.top_fail_patterns:
        lines.append("Top fail patterns:")
        for pattern, count in sorted(summary.top_fail_patterns.items(), key=lambda x: -x[1]):
            lines.append(f"  {pattern}: {count}")
    return "\n".join(lines)


def print_report(summary: PrescanSummary) -> None:
    print(render_report(summary))
