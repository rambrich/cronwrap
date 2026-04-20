"""CLI for inspecting cronwrap event logs."""
from __future__ import annotations

import argparse
import sys
from datetime import datetime

from cronwrap.eventlog import EventLogConfig, EventLogger


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronwrap-eventlog",
        description="Inspect cronwrap structured event logs",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    ls = sub.add_parser("list", help="List events for a command")
    ls.add_argument("command", help="Command to look up events for")
    ls.add_argument("--event", default=None, help="Filter by event type")
    ls.add_argument("--limit", type=int, default=20, help="Max entries to show")

    sub.add_parser("status", help="Show eventlog configuration")
    return parser


def _manager() -> EventLogger:
    return EventLogger(EventLogConfig.from_env())


def cmd_list(args: argparse.Namespace) -> None:
    mgr = _manager()
    if not mgr.config.enabled:
        print("Event log is disabled. Set CRONWRAP_EVENTLOG_ENABLED=1 to enable.")
        sys.exit(1)
    entries = mgr.load(args.command)
    if args.event:
        entries = [e for e in entries if e.event == args.event]
    entries = entries[-args.limit :]
    if not entries:
        print("No events found.")
        return
    print(f"{'Timestamp':<22} {'Event':<20} {'Exit':>5} {'Duration':>10}  Detail")
    print("-" * 72)
    for e in entries:
        ts = datetime.fromtimestamp(e.timestamp).strftime("%Y-%m-%d %H:%M:%S")
        dur = f"{e.duration:.2f}s" if e.duration is not None else "-"
        code = str(e.exit_code) if e.exit_code is not None else "-"
        print(f"{ts:<22} {e.event:<20} {code:>5} {dur:>10}  {e.detail}")


def cmd_status(args: argparse.Namespace) -> None:
    cfg = EventLogConfig.from_env()
    print(f"enabled:    {cfg.enabled}")
    print(f"log_dir:    {cfg.log_dir}")
    print(f"max_events: {cfg.max_events}")


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.cmd == "list":
        cmd_list(args)
    elif args.cmd == "status":
        cmd_status(args)


if __name__ == "__main__":
    main()
