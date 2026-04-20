"""Render a human-readable report from the notification log."""
from __future__ import annotations

from typing import Dict, List

from cronwrap.notification_log import NotificationEntry


def summarize_entries(entries: List[NotificationEntry]) -> Dict:
    total = len(entries)
    sent = sum(1 for e in entries if e.success)
    failed = total - sent
    by_channel: Dict[str, int] = {}
    for e in entries:
        by_channel[e.channel] = by_channel.get(e.channel, 0) + 1
    return {
        "total": total,
        "sent": sent,
        "failed": failed,
        "by_channel": by_channel,
    }


def render_report(entries: List[NotificationEntry]) -> str:
    summary = summarize_entries(entries)
    lines = [
        "=== Notification Log Report ===",
        f"Total:  {summary['total']}",
        f"Sent:   {summary['sent']}",
        f"Failed: {summary['failed']}",
        "",
        "By channel:",
    ]
    for channel, count in sorted(summary["by_channel"].items()):
        lines.append(f"  {channel}: {count}")
    if entries:
        lines.append("")
        lines.append("Recent entries:")
        for e in entries[-10:]:
            status = "OK" if e.success else "FAIL"
            lines.append(f"  [{status}] {e.sent_at}  {e.channel}  {e.event}  -> {e.recipient}")
    return "\n".join(lines)


def print_report(entries: List[NotificationEntry]) -> None:
    print(render_report(entries))
