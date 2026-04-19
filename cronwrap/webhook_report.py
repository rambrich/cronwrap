"""Webhook delivery report utilities."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List


@dataclass
class WebhookAttempt:
    command: str
    success: bool
    http_status: int | None
    delivered: bool


@dataclass
class WebhookReport:
    total: int = 0
    delivered: int = 0
    failed: int = 0
    attempts: List[WebhookAttempt] = field(default_factory=list)


def summarize_attempts(attempts: List[WebhookAttempt]) -> WebhookReport:
    if not attempts:
        return WebhookReport()
    delivered = sum(1 for a in attempts if a.delivered)
    failed = len(attempts) - delivered
    return WebhookReport(
        total=len(attempts),
        delivered=delivered,
        failed=failed,
        attempts=attempts,
    )


def render_report(report: WebhookReport) -> str:
    lines = [
        "=== Webhook Delivery Report ===",
        f"Total:     {report.total}",
        f"Delivered: {report.delivered}",
        f"Failed:    {report.failed}",
        "",
    ]
    for a in report.attempts:
        status_str = str(a.http_status) if a.http_status else "N/A"
        mark = "✓" if a.delivered else "✗"
        lines.append(f"  {mark} [{status_str}] {a.command}")
    return "\n".join(lines)


def print_report(report: WebhookReport) -> None:
    print(render_report(report))
