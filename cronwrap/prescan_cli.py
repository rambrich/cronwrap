"""CLI for inspecting prescan configuration and testing patterns."""
from __future__ import annotations

import argparse
import sys

from cronwrap.prescan import PrescanConfig, PrescanManager
from cronwrap.runner import RunResult


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronwrap-prescan",
        description="Inspect or test prescan pattern configuration.",
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("status", help="Show current prescan configuration")

    test_p = sub.add_parser("test", help="Test patterns against sample output")
    test_p.add_argument("text", help="Sample output text to scan")

    return parser


def cmd_status(config: PrescanConfig) -> None:
    print(f"Prescan enabled : {config.enabled}")
    print(f"Warn patterns   : {', '.join(config.warn_patterns) or '(none)'}")
    print(f"Fail patterns   : {', '.join(config.fail_patterns) or '(none)'}")


def cmd_test(config: PrescanConfig, text: str) -> None:
    if not config.enabled:
        print("Prescan is disabled. Enable with CRONWRAP_PRESCAN_ENABLED=true.")
        return
    manager = PrescanManager(config)
    fake_result = RunResult(
        command="<test>",
        returncode=0,
        stdout=text,
        stderr="",
        duration=0.0,
    )
    prescan = manager.scan(fake_result)
    if prescan is None:
        print("No scan performed (disabled).")
        return
    if prescan.has_warnings:
        print(f"WARN matches : {', '.join(prescan.matched_warn)}")
    else:
        print("WARN matches : (none)")
    if prescan.has_failures:
        print(f"FAIL matches : {', '.join(prescan.matched_fail)}")
    else:
        print("FAIL matches : (none)")


def main(argv=None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    config = PrescanConfig.from_env()

    if args.command == "status":
        cmd_status(config)
    elif args.command == "test":
        cmd_test(config, args.text)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
