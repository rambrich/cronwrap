"""CLI helper for inspecting and testing the sampling configuration."""
from __future__ import annotations

import argparse
import sys

from cronwrap.sampling import SamplingConfig, SamplingManager


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronwrap-sampling",
        description="Inspect or test the cronwrap sampling configuration.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="Show current sampling configuration.")

    sim = sub.add_parser("simulate", help="Simulate N draws and report how many would run.")
    sim.add_argument("-n", "--trials", type=int, default=100, help="Number of trials (default: 100).")
    sim.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility.")

    return parser


def cmd_status(cfg: SamplingConfig) -> None:
    print(f"Enabled : {cfg.enabled}")
    print(f"Rate    : {cfg.rate:.4f}  ({cfg.rate * 100:.1f}%)")
    print(f"Seed    : {cfg.seed if cfg.seed is not None else 'none'}")


def cmd_simulate(cfg: SamplingConfig, trials: int, seed: int | None) -> None:
    sim_cfg = SamplingConfig(enabled=True, rate=cfg.rate, seed=seed)
    mgr = SamplingManager(sim_cfg)
    runs = sum(1 for _ in range(trials) if mgr.should_run())
    pct = runs / trials * 100 if trials else 0
    print(f"Trials  : {trials}")
    print(f"Would run: {runs}  ({pct:.1f}%)")
    print(f"Expected : {cfg.rate * 100:.1f}%")


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    cfg = SamplingConfig.from_env()

    if args.command == "status":
        cmd_status(cfg)
    elif args.command == "simulate":
        cmd_simulate(cfg, trials=args.trials, seed=args.seed)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
