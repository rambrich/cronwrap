"""CLI for spike detection management."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from cronwrap.spike import SpikeConfig, SpikeDetector


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronwrap-spike",
        description="Manage spike detection state",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    status_p = sub.add_parser("status", help="Show spike detection config and history")
    status_p.add_argument("--job", default="default", help="Job name")

    reset_p = sub.add_parser("reset", help="Reset spike history for a job")
    reset_p.add_argument("--job", default="default", help="Job name")

    simulate_p = sub.add_parser("simulate", help="Simulate a duration check")
    simulate_p.add_argument("--job", default="default", help="Job name")
    simulate_p.add_argument("--duration", type=float, required=True, help="Duration in seconds")

    return parser


def _manager(cfg: SpikeConfig, job: str) -> SpikeDetector:
    return SpikeDetector(cfg, job=job)


def cmd_status(args: argparse.Namespace, cfg: SpikeConfig) -> None:
    det = _manager(cfg, args.job)
    history = det._load_history()
    print(f"Spike detection enabled : {cfg.enabled}")
    print(f"Job                     : {args.job}")
    print(f"Window                  : {cfg.window}")
    print(f"Z-threshold             : {cfg.z_threshold}")
    print(f"Min samples             : {cfg.min_samples}")
    print(f"Stored samples          : {len(history)}")
    if history:
        from statistics import mean
        print(f"Mean duration           : {mean(history):.3f}s")


def cmd_reset(args: argparse.Namespace, cfg: SpikeConfig) -> None:
    det = _manager(cfg, args.job)
    det.reset()
    print(f"Spike history reset for job: {args.job}")


def cmd_simulate(args: argparse.Namespace, cfg: SpikeConfig) -> None:
    from cronwrap.runner import RunResult
    det = _manager(cfg, args.job)
    fake = RunResult(
        command="simulate",
        returncode=0,
        stdout="",
        stderr="",
        duration=args.duration,
        timed_out=False,
    )
    result = det.check(fake)
    if result is None:
        print("Spike detection is disabled.")
        return
    print(json.dumps(result.to_dict(), indent=2))


def main(argv=None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    cfg = SpikeConfig.from_env()

    if args.command == "status":
        cmd_status(args, cfg)
    elif args.command == "reset":
        cmd_reset(args, cfg)
    elif args.command == "simulate":
        cmd_simulate(args, cfg)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
