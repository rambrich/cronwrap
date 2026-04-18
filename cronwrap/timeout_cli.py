"""CLI helpers for inspecting and testing timeout configuration."""
from __future__ import annotations
import argparse
import sys
from cronwrap.timeout import TimeoutConfig, TimeoutManager


def build_timeout_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronwrap-timeout",
        description="Inspect cronwrap timeout configuration",
    )
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("show", help="Show current timeout config from environment")

    check = subparsers.add_parser("check", help="Check if elapsed time exceeds timeout")
    check.add_argument("--elapsed", type=float, required=True, help="Elapsed seconds")
    check.add_argument("--returncode", type=int, default=0)

    return parser


def run_timeout_cli(args: argparse.Namespace) -> int:
    cfg = TimeoutConfig.from_env()
    mgr = TimeoutManager(cfg)

    if args.command == "show":
        print(f"enabled:    {cfg.enabled}")
        print(f"seconds:    {cfg.seconds}")
        print(f"kill_after: {cfg.kill_after}")
        print(f"effective:  {mgr.get_timeout()}")
        return 0

    if args.command == "check":
        try:
            mgr.check_result(args.returncode, args.elapsed)
            print("OK: within timeout")
            return 0
        except Exception as e:
            print(f"EXCEEDED: {e}", file=sys.stderr)
            return 1

    print("No command specified. Use --help.", file=sys.stderr)
    return 1


def main() -> None:
    parser = build_timeout_parser()
    args = parser.parse_args()
    sys.exit(run_timeout_cli(args))


if __name__ == "__main__":
    main()
