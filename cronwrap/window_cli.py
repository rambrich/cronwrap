"""CLI helpers for inspecting the execution-window configuration."""
from __future__ import annotations

import argparse
import sys
from datetime import time
from typing import List, Optional

from cronwrap.window import WindowConfig, WindowManager


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronwrap-window",
        description="Inspect or test the cronwrap execution window.",
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("status", help="Show current window configuration.")

    check_p = sub.add_parser("check", help="Check whether a given time is allowed.")
    check_p.add_argument(
        "--at",
        metavar="HH:MM",
        default=None,
        help="Time to check (default: now).",
    )
    return parser


def cmd_status(config: WindowConfig) -> None:
    print(f"enabled : {config.enabled}")
    print(f"timezone: {config.timezone}")
    if config.windows:
        ranges = ", ".join(
            f"{s.isoformat()}-{e.isoformat()}" for s, e in config.windows
        )
        print(f"windows : {ranges}")
    else:
        print("windows : (none)")


def cmd_check(config: WindowConfig, at_str: Optional[str]) -> None:
    at: Optional[time] = None
    if at_str:
        try:
            at = time.fromisoformat(at_str)
        except ValueError:
            print(f"Invalid time format: {at_str!r}. Expected HH:MM or HH:MM:SS.",
                  file=sys.stderr)
            sys.exit(2)

    mgr = WindowManager(config)
    allowed = mgr.is_allowed(at)
    label = at.isoformat() if at else "now"
    if allowed:
        print(f"ALLOWED  — {label} is within an execution window.")
    else:
        print(f"BLOCKED  — {label} is outside all execution windows.")
        sys.exit(1)


def main(argv: Optional[List[str]] = None) -> None:  # pragma: no cover
    parser = build_parser()
    args = parser.parse_args(argv)
    config = WindowConfig.from_env()

    if args.command == "status":
        cmd_status(config)
    elif args.command == "check":
        cmd_check(config, args.at)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":  # pragma: no cover
    main()
