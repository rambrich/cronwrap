"""CLI for testing sanitize rules against sample input."""
from __future__ import annotations
import argparse
import sys
from cronwrap.sanitize import SanitizeConfig, Sanitizer


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="cronwrap-sanitize",
        description="Sanitize text using cronwrap sanitize rules.",
    )
    p.add_argument("input", nargs="?", help="Text to sanitize (reads stdin if omitted)")
    p.add_argument("--no-ansi", dest="strip_ansi", action="store_false", default=True)
    p.add_argument("--no-control", dest="strip_control", action="store_false", default=True)
    p.add_argument(
        "--pattern",
        dest="patterns",
        action="append",
        default=[],
        metavar="REGEX",
        help="Extra regex pattern to strip (repeatable)",
    )
    return p


def run_sanitize_cli(args: argparse.Namespace) -> None:
    text = args.input if args.input is not None else sys.stdin.read()
    cfg = SanitizeConfig(
        enabled=True,
        strip_ansi=args.strip_ansi,
        strip_control=args.strip_control,
        extra_patterns=args.patterns,
    )
    sanitizer = Sanitizer(cfg)
    result = sanitizer.sanitize(text)
    sys.stdout.write(result)
    if result and not result.endswith("\n"):
        sys.stdout.write("\n")


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    run_sanitize_cli(args)


if __name__ == "__main__":
    main()
