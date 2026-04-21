"""CLI commands for inspecting and managing baseline state."""
from __future__ import annotations

import argparse
import sys

from cronwrap.baseline import BaselineConfig, BaselineManager


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronwrap-baseline",
        description="Manage cronwrap baseline performance data",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    status_p = sub.add_parser("status", help="Show baseline stats for a command")
    status_p.add_argument("cmd", help="The command string to look up")

    reset_p = sub.add_parser("reset", help="Clear baseline data for a command")
    reset_p.add_argument("cmd", help="The command string to reset")

    return parser


def _manager() -> BaselineManager:
    return BaselineManager(BaselineConfig.from_env())


def cmd_status(args: argparse.Namespace, mgr: BaselineManager | None = None) -> None:
    mgr = mgr or _manager()
    stats = mgr.stats(args.cmd)
    if stats["samples"] == 0:
        print(f"No baseline data for: {args.cmd}")
        return
    print(f"Baseline stats for: {args.cmd}")
    print(f"  Samples : {stats['samples']}")
    print(f"  Avg     : {stats['avg']:.2f}s")
    print(f"  Min     : {stats['min']:.2f}s")
    print(f"  Max     : {stats['max']:.2f}s")


def cmd_reset(args: argparse.Namespace, mgr: BaselineManager | None = None) -> None:
    mgr = mgr or _manager()
    mgr.reset(args.cmd)
    print(f"Baseline data cleared for: {args.cmd}")


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    mgr = _manager()
    if args.command == "status":
        cmd_status(args, mgr)
    elif args.command == "reset":
        cmd_reset(args, mgr)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
