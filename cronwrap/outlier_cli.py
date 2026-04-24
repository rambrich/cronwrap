"""CLI for inspecting outlier detection state."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from cronwrap.outlier import OutlierConfig, OutlierDetector


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronwrap-outlier",
        description="Inspect or reset outlier detection history.",
    )
    sub = parser.add_subparsers(dest="command")

    status = sub.add_parser("status", help="Show recent history for a job")
    status.add_argument("--job", default="default", help="Job name")
    status.add_argument("--state-dir", default=None, help="Override state directory")

    reset = sub.add_parser("reset", help="Clear history for a job")
    reset.add_argument("--job", required=True, help="Job name")
    reset.add_argument("--state-dir", default=None, help="Override state directory")

    return parser


def _manager(args: argparse.Namespace) -> OutlierDetector:
    cfg = OutlierConfig.from_env()
    cfg.enabled = True
    if args.state_dir:
        cfg.state_dir = args.state_dir
    return OutlierDetector(cfg, job=args.job)


def cmd_status(args: argparse.Namespace) -> None:
    det = _manager(args)
    history = det._load_history()
    if not history:
        print(f"No outlier history for job '{args.job}'.")
        return
    import statistics
    mean = statistics.mean(history)
    stddev = statistics.pstdev(history) if len(history) > 1 else 0.0
    print(f"Job:     {args.job}")
    print(f"Samples: {len(history)}")
    print(f"Mean:    {mean:.3f}s")
    print(f"Stddev:  {stddev:.3f}s")
    print(f"Min:     {min(history):.3f}s")
    print(f"Max:     {max(history):.3f}s")
    print(f"Threshold (z): {det.config.threshold}")


def cmd_reset(args: argparse.Namespace) -> None:
    det = _manager(args)
    p = det._state_path()
    if p.exists():
        p.unlink()
        print(f"Outlier history cleared for job '{args.job}'.")
    else:
        print(f"No history found for job '{args.job}'.")


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "status":
        cmd_status(args)
    elif args.command == "reset":
        cmd_reset(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
