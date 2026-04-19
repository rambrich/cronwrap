"""CLI for inspecting and resetting concurrency state."""
from __future__ import annotations

import argparse
import sys

from cronwrap.concurrency import ConcurrencyConfig, ConcurrencyManager


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronwrap-concurrency",
        description="Inspect or reset cronwrap concurrency slots.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    status_p = sub.add_parser("status", help="Show active slot count for a job.")
    status_p.add_argument("job", help="Job name")

    reset_p = sub.add_parser("reset", help="Clear all slots for a job.")
    reset_p.add_argument("job", help="Job name")

    return parser


def _manager(job: str) -> ConcurrencyManager:
    cfg = ConcurrencyConfig.from_env()
    cfg.enabled = True  # force enabled for CLI inspection
    return ConcurrencyManager(cfg, job)


def cmd_status(args: argparse.Namespace) -> None:
    mgr = _manager(args.job)
    count = mgr.active_count()
    max_c = mgr.config.max_concurrent
    print(f"Job '{args.job}': {count}/{max_c} slots active")


def cmd_reset(args: argparse.Namespace) -> None:
    mgr = _manager(args.job)
    path = mgr._state_path()
    if path.exists():
        path.write_text("[]")
        print(f"Slots reset for job '{args.job}'.")
    else:
        print(f"No state found for job '{args.job}'.")


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "status":
        cmd_status(args)
    elif args.command == "reset":
        cmd_reset(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
