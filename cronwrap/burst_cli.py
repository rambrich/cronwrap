"""CLI for inspecting and resetting burst detection state."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cronwrap.burst import BurstConfig, BurstManager


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronwrap-burst",
        description="Inspect and manage burst detection state.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    status_p = sub.add_parser("status", help="Show burst state for a job")
    status_p.add_argument("job", help="Job name")

    reset_p = sub.add_parser("reset", help="Reset burst state for a job")
    reset_p.add_argument("job", help="Job name")

    return parser


def _manager(job: str, config: BurstConfig) -> BurstManager:
    return BurstManager(config=config, job=job)


def cmd_status(args: argparse.Namespace, config: BurstConfig) -> None:
    mgr = _manager(args.job, config)
    if not config.enabled:
        print("Burst detection is disabled.")
        return
    count = len(mgr._timestamps)
    print(f"Job          : {args.job}")
    print(f"Window       : {config.window_seconds}s")
    print(f"Max runs     : {config.max_runs}")
    print(f"Runs in window: {count}")
    status = "BURST" if count > config.max_runs else "OK"
    print(f"Status       : {status}")


def cmd_reset(args: argparse.Namespace, config: BurstConfig) -> None:
    mgr = _manager(args.job, config)
    mgr.reset()
    print(f"Burst state reset for job '{args.job}'.")


def main(argv=None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    config = BurstConfig.from_env()

    if args.command == "status":
        cmd_status(args, config)
    elif args.command == "reset":
        cmd_reset(args, config)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
