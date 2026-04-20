"""CLI sub-tool for inspecting the notification log."""
from __future__ import annotations

import argparse
import sys

from cronwrap.notification_log import NotificationLogConfig, NotificationLogger
from cronwrap.notification_log_report import print_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronwrap-notif-log",
        description="Inspect the cronwrap notification log",
    )
    sub = parser.add_subparsers(dest="command")

    ls = sub.add_parser("list", help="List notifications for a job")
    ls.add_argument("job", help="Job name")
    ls.add_argument("--limit", type=int, default=20, help="Max entries to show")

    rp = sub.add_parser("report", help="Print summary report for a job")
    rp.add_argument("job", help="Job name")

    cl = sub.add_parser("clear", help="Clear log for a job")
    cl.add_argument("job", help="Job name")
    return parser


def _manager() -> NotificationLogger:
    return NotificationLogger(NotificationLogConfig.from_env())


def cmd_list(args: argparse.Namespace) -> None:
    mgr = _manager()
    entries = mgr.load(args.job)
    if not entries:
        print(f"No notification log entries for job '{args.job}'.")
        return
    for e in entries[-args.limit:]:
        status = "OK" if e.success else "FAIL"
        print(f"[{status}] {e.sent_at}  {e.channel}  {e.event}  -> {e.recipient}")


def cmd_report(args: argparse.Namespace) -> None:
    mgr = _manager()
    entries = mgr.load(args.job)
    print_report(entries)


def cmd_clear(args: argparse.Namespace) -> None:
    mgr = _manager()
    path = mgr._log_path(args.job)
    if path.exists():
        path.unlink()
        print(f"Cleared notification log for '{args.job}'.")
    else:
        print(f"No log file found for '{args.job}'.")


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    dispatch = {"list": cmd_list, "report": cmd_report, "clear": cmd_clear}
    if args.command in dispatch:
        dispatch[args.command](args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
