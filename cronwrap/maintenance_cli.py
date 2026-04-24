"""CLI for managing maintenance windows."""
from __future__ import annotations

import argparse
import sys
import time
from cronwrap.maintenance import MaintenanceConfig, MaintenanceManager


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronwrap-maintenance",
        description="Manage cronwrap maintenance windows",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="Show current maintenance window status")

    enable_p = sub.add_parser("enable", help="Enable a maintenance window")
    enable_p.add_argument("--duration", type=int, default=3600, help="Duration in seconds (default: 3600)")
    enable_p.add_argument("--reason", default="", help="Reason for maintenance")

    sub.add_parser("disable", help="Clear the active maintenance window")

    return parser


def _manager() -> MaintenanceManager:
    config = MaintenanceConfig.from_env()
    config.enabled = True  # CLI always operates regardless of env flag
    return MaintenanceManager(config)


def cmd_status(args: argparse.Namespace) -> None:
    mgr = _manager()
    window = mgr.status()
    if window is None:
        print("No maintenance window set.")
        return
    now = time.time()
    active = window.is_active(now)
    remaining = max(0, window.end - now)
    print(f"Status   : {'ACTIVE' if active else 'INACTIVE'}")
    print(f"Start    : {window.start:.0f}")
    print(f"End      : {window.end:.0f}")
    print(f"Remaining: {remaining:.0f}s")
    if window.reason:
        print(f"Reason   : {window.reason}")


def cmd_enable(args: argparse.Namespace) -> None:
    """Enable a maintenance window, validating that duration is positive."""
    if args.duration <= 0:
        print(f"Error: --duration must be a positive integer, got {args.duration}.", file=sys.stderr)
        sys.exit(1)
    mgr = _manager()
    window = mgr.set_window(args.duration, reason=args.reason)
    print(f"Maintenance window enabled for {args.duration}s (ends at {window.end:.0f}).")
    if args.reason:
        print(f"Reason: {args.reason}")


def cmd_disable(args: argparse.Namespace) -> None:
    mgr = _manager()
    mgr.clear()
    print("Maintenance window cleared.")


def main(argv=None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    dispatch = {"status": cmd_status, "enable": cmd_enable, "disable": cmd_disable}
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
