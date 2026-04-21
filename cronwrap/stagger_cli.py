"""CLI tool for inspecting and simulating stagger configuration."""
from __future__ import annotations

import argparse
import sys

from cronwrap.stagger import StaggerConfig, StaggerManager, _offset_seconds


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronwrap-stagger",
        description="Inspect or simulate the stagger delay for a cron job.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="Show current stagger configuration.")

    sim = sub.add_parser("simulate", help="Simulate the stagger offset for a given seed.")
    sim.add_argument("--seed", default=None, help="Seed string (e.g. hostname+job).")
    sim.add_argument("--window", type=int, default=60, help="Window in seconds (default: 60).")
    sim.add_argument("--count", type=int, default=5, help="Number of samples to show.")

    return parser


def cmd_status(args: argparse.Namespace) -> None:  # noqa: ARG001
    cfg = StaggerConfig.from_env()
    print(f"enabled       : {cfg.enabled}")
    print(f"window_seconds: {cfg.window_seconds}")
    print(f"seed          : {cfg.seed!r}")
    if cfg.enabled:
        mgr = StaggerManager(cfg)
        print(f"next delay (s): {mgr.delay_seconds():.3f}")
    else:
        print("next delay (s): 0.000  (disabled)")


def cmd_simulate(args: argparse.Namespace) -> None:
    print(f"Simulating {args.count} stagger offset(s) — window={args.window}s, seed={args.seed!r}")
    print()
    if args.seed:
        # Deterministic: show single value repeated to illustrate consistency
        offset = _offset_seconds(args.window, args.seed)
        for i in range(1, args.count + 1):
            print(f"  sample {i:>3}: {offset:.3f}s")
    else:
        import random
        for i in range(1, args.count + 1):
            offset = random.uniform(0, args.window)
            print(f"  sample {i:>3}: {offset:.3f}s")


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "status":
        cmd_status(args)
    elif args.command == "simulate":
        cmd_simulate(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
