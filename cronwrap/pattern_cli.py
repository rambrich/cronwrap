"""CLI for inspecting pattern-matching configuration and testing patterns."""
from __future__ import annotations

import argparse
import re
import sys

from cronwrap.pattern import PatternConfig, PatternMatcher
from cronwrap.runner import RunResult


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronwrap-pattern",
        description="Inspect and test cronwrap output pattern matching.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="Show current pattern configuration.")

    test_p = sub.add_parser("test", help="Test a string against configured patterns.")
    test_p.add_argument("text", help="Text to match against patterns.")

    return parser


def cmd_status(config: PatternConfig) -> None:
    print(f"enabled : {config.enabled}")
    if config.warn_patterns:
        print("warn patterns:")
        for p in config.warn_patterns:
            print(f"  - {p}")
    else:
        print("warn patterns: (none)")
    if config.fail_patterns:
        print("fail patterns:")
        for p in config.fail_patterns:
            print(f"  - {p}")
    else:
        print("fail patterns: (none)")


def cmd_test(config: PatternConfig, text: str) -> None:
    if not config.enabled:
        print("Pattern matching is disabled. Set CRONWRAP_PATTERN_ENABLED=true to enable.")
        return
    dummy = RunResult(command="test", returncode=0, stdout=text, stderr="", duration=0.0)
    matcher = PatternMatcher(config)
    result = matcher.check(dummy)
    if result is None or not result.matches:
        print("No matches found.")
        return
    for m in result.matches:
        print(f"[{m.level.upper()}] pattern={m.pattern!r} line={m.matched_line!r}")


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    config = PatternConfig.from_env()
    if args.command == "status":
        cmd_status(config)
    elif args.command == "test":
        cmd_test(config, args.text)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
