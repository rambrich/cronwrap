"""CLI for checking dependencies before running a cron job."""
from __future__ import annotations
import argparse
import sys
from cronwrap.dependency import DependencyConfig, DependencyChecker


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronwrap-dep",
        description="Check that required commands and env vars are present.",
    )
    parser.add_argument(
        "--commands",
        default="",
        help="Comma-separated list of commands to check (e.g. curl,jq)",
    )
    parser.add_argument(
        "--env-vars",
        default="",
        dest="env_vars",
        help="Comma-separated list of env vars to check (e.g. API_KEY,DB_URL)",
    )
    return parser


def run_dependency_cli(args: argparse.Namespace) -> int:
    commands = [c.strip() for c in args.commands.split(",") if c.strip()]
    env_vars = [v.strip() for v in args.env_vars.split(",") if v.strip()]
    config = DependencyConfig(enabled=True, commands=commands, env_vars=env_vars)
    checker = DependencyChecker(config)
    error = checker.check()
    if error:
        print(f"[cronwrap-dep] FAILED: {error}", file=sys.stderr)
        return 1
    print("[cronwrap-dep] All dependencies satisfied.")
    return 0


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    sys.exit(run_dependency_cli(args))


if __name__ == "__main__":
    main()
