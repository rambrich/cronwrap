"""Reporting utilities for run metadata."""
from __future__ import annotations

from typing import List, Dict, Any
from collections import Counter

from cronwrap.metadata import RunMetadata


def summarize_metadata(entries: List[RunMetadata]) -> Dict[str, Any]:
    """Return a summary dict from a list of RunMetadata entries."""
    if not entries:
        return {"total": 0, "hostnames": {}, "users": {}, "extra_keys": []}

    hostnames: Counter = Counter()
    users: Counter = Counter()
    extra_keys: Counter = Counter()

    for entry in entries:
        if entry.hostname:
            hostnames[entry.hostname] += 1
        if entry.user:
            users[entry.user] += 1
        for k in entry.extra:
            extra_keys[k] += 1

    return {
        "total": len(entries),
        "hostnames": dict(hostnames),
        "users": dict(users),
        "extra_keys": sorted(extra_keys.keys()),
    }


def render_report(summary: Dict[str, Any]) -> str:
    lines = [
        "=== Metadata Report ===",
        f"Total entries : {summary['total']}",
    ]
    if summary["hostnames"]:
        lines.append("Hostnames:")
        for host, count in sorted(summary["hostnames"].items()):
            lines.append(f"  {host}: {count}")
    if summary["users"]:
        lines.append("Users:")
        for user, count in sorted(summary["users"].items()):
            lines.append(f"  {user}: {count}")
    if summary["extra_keys"]:
        lines.append("Extra keys: " + ", ".join(summary["extra_keys"]))
    return "\n".join(lines)


def print_report(entries: List[RunMetadata]) -> None:  # pragma: no cover
    summary = summarize_metadata(entries)
    print(render_report(summary))
