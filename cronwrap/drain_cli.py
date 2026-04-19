"""CLI for managing drain mode."""
from __future__ import annotations

import argparse
import sys

from cronwrap.drain import DrainConfig, DrainManager


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cronwrap-drain", description="Manage cronwrap drain mode")
    parser.add_argument("--job", required=True, help="Job name")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status", help="Show drain status")
    sub.add_parser("enable", help="Enable drain mode")
    sub.add_parser("disable", help="Disable drain mode")
    sub.add_parser("reset", help="Remove drain state file")
    return parser


def _manager(args: argparse.Namespace) -> DrainManager:
    config = DrainConfig.from_env()
    config.enabled = True  # CLI always operates regardless of env flag
    return DrainManager(config, args.job)


def cmd_status(args: argparse.Namespace) -> None:
    mgr = _manager(args)
    draining = mgr.is_draining()
    print(f"Job '{args.job}' drain mode: {'ENABLED' if draining else 'DISABLED'}")


def cmd_enable(args: argparse.Namespace) -> None:
    mgr = _manager(args)
    mgr.set_draining(True)
    print(f"Drain mode ENABLED for job '{args.job}'")


def cmd_disable(args: argparse.Namespace) -> None:
    mgr = _manager(args)
    mgr.set_draining(False)
    print(f"Drain mode DISABLED for job '{args.job}'")


def cmd_reset(args: argparse.Namespace) -> None:
    mgr = _manager(args)
    mgr.reset()
    print(f"Drain state reset for job '{args.job}'")


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    dispatch = {"status": cmd_status, "enable": cmd_enable, "disable": cmd_disable, "reset": cmd_reset}
    dispatch[args.cmd](args)


if __name__ == "__main__":
    main()
