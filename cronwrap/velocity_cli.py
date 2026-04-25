"""CLI for inspecting velocity state."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from cronwrap.velocity import VelocityConfig, VelocityManager
from cronwrap.velocity_report import print_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronwrap-velocity",
        description="Inspect cronwrap velocity tracking state.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    status_p = sub.add_parser("status", help="Show velocity state for a job")
    status_p.add_argument("job", help="Job name")
    status_p.add_argument(
        "--state-dir",
        default="/tmp/cronwrap/velocity",
        help="State directory",
    )

    reset_p = sub.add_parser("reset", help="Reset velocity state for a job")
    reset_p.add_argument("job", help="Job name")
    reset_p.add_argument(
        "--state-dir",
        default="/tmp/cronwrap/velocity",
        help="State directory",
    )

    report_p = sub.add_parser("report", help="Print velocity report for all jobs")
    report_p.add_argument(
        "--state-dir",
        default="/tmp/cronwrap/velocity",
        help="State directory",
    )
    report_p.add_argument(
        "--window",
        type=int,
        default=3600,
        help="Window in seconds",
    )
    return parser


def cmd_status(args: argparse.Namespace) -> None:
    p = Path(args.state_dir) / f"{args.job}.json"
    if not p.exists():
        print(f"No velocity state found for job '{args.job}'.")
        return
    timestamps = json.loads(p.read_text())
    print(f"Job            : {args.job}")
    print(f"Recorded runs  : {len(timestamps)}")
    if timestamps:
        import time
        age = time.time() - timestamps[-1]
        print(f"Last run ago   : {age:.0f}s")


def cmd_reset(args: argparse.Namespace) -> None:
    cfg = VelocityConfig(enabled=True, state_dir=args.state_dir)
    mgr = VelocityManager(config=cfg, job=args.job)
    mgr.reset()
    print(f"Velocity state reset for job '{args.job}'.")


def cmd_report(args: argparse.Namespace) -> None:
    print_report(args.state_dir, window_seconds=args.window)


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "status":
        cmd_status(args)
    elif args.command == "reset":
        cmd_reset(args)
    elif args.command == "report":
        cmd_report(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
