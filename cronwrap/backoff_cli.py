"""CLI utility for inspecting backoff delay schedule."""
from __future__ import annotations
import argparse
from cronwrap.backoff import BackoffConfig, compute_delay


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="cronwrap-backoff",
        description="Show computed backoff delays for N retry attempts.",
    )
    p.add_argument("--attempts", type=int, default=5, help="Number of attempts to preview")
    p.add_argument("--base-delay", type=float, default=1.0)
    p.add_argument("--max-delay", type=float, default=60.0)
    p.add_argument("--multiplier", type=float, default=2.0)
    p.add_argument("--no-jitter", action="store_true")
    return p


def run_backoff_cli(args: argparse.Namespace) -> None:
    cfg = BackoffConfig(
        enabled=True,
        base_delay=args.base_delay,
        max_delay=args.max_delay,
        multiplier=args.multiplier,
        jitter=not args.no_jitter,
    )
    print(f"{'Attempt':>8}  {'Delay (s)':>12}")
    print("-" * 24)
    for i in range(args.attempts):
        delay = compute_delay(cfg, i)
        print(f"{i:>8}  {delay:>12.3f}")


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    run_backoff_cli(args)


if __name__ == "__main__":
    main()
