"""CLI for inspecting and resetting smoothing state."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cronwrap.smoothing import SmoothingConfig, SmoothingManager


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronwrap-smoothing",
        description="Inspect or reset EMA smoothing state for cron jobs.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    status_p = sub.add_parser("status", help="Show smoothed value for a job")
    status_p.add_argument("job", help="Job name")
    status_p.add_argument(
        "--state-dir",
        default=None,
        help="Override state directory",
    )

    reset_p = sub.add_parser("reset", help="Reset smoothing state for a job")
    reset_p.add_argument("job", help="Job name")
    reset_p.add_argument("--state-dir", default=None)

    list_p = sub.add_parser("list", help="List all jobs with smoothing state")
    list_p.add_argument("--state-dir", default=None)

    return parser


def _manager(args: argparse.Namespace) -> SmoothingManager:
    cfg = SmoothingConfig.from_env()
    cfg.enabled = True
    if getattr(args, "state_dir", None):
        cfg.state_dir = args.state_dir
    return SmoothingManager(cfg)


def cmd_status(args: argparse.Namespace) -> None:
    mgr = _manager(args)
    value = mgr.current(args.job)
    if value is None:
        print(f"No smoothing data for job: {args.job}")
    else:
        print(f"Job:              {args.job}")
        print(f"Smoothed (EMA):   {value:.4f}s")


def cmd_reset(args: argparse.Namespace) -> None:
    mgr = _manager(args)
    mgr.reset(args.job)
    print(f"Smoothing state reset for job: {args.job}")


def cmd_list(args: argparse.Namespace) -> None:
    cfg = SmoothingConfig.from_env()
    if getattr(args, "state_dir", None):
        cfg.state_dir = args.state_dir
    state_path = Path(cfg.state_dir)
    if not state_path.exists():
        print("No smoothing state directory found.")
        return
    files = sorted(state_path.glob("*.json"))
    if not files:
        print("No smoothing state found.")
        return
    for f in files:
        print(f.stem)


def main(argv=None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    dispatch = {"status": cmd_status, "reset": cmd_reset, "list": cmd_list}
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
