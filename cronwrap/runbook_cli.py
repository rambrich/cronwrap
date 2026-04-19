"""CLI for inspecting runbook configuration."""
from __future__ import annotations
import argparse
import os
import sys
from cronwrap.runbook import RunbookConfig


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronwrap-runbook",
        description="Inspect or validate the cronwrap runbook configuration.",
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("status", help="Show current runbook configuration")

    validate = sub.add_parser("validate", help="Validate a runbook URL is reachable")
    validate.add_argument("--url", default=None, help="URL to validate (defaults to env)")

    return parser


def cmd_status(cfg: RunbookConfig) -> None:
    print(f"Enabled:          {cfg.enabled}")
    print(f"URL:              {cfg.url or '(none)'}")
    print(f"Notes:            {cfg.notes or '(none)'}")
    print(f"Print on failure: {cfg.print_on_failure}")
    print(f"Print on success: {cfg.print_on_success}")


def cmd_validate(url: str) -> int:
    try:
        import urllib.request
        with urllib.request.urlopen(url, timeout=5) as resp:
            code = resp.getcode()
            print(f"OK: {url} returned HTTP {code}")
            return 0
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL: {url} — {exc}", file=sys.stderr)
        return 1


def main(argv=None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    cfg = RunbookConfig.from_env()

    if args.command == "status":
        cmd_status(cfg)
    elif args.command == "validate":
        url = args.url or cfg.url
        if not url:
            print("No runbook URL configured.", file=sys.stderr)
            sys.exit(1)
        sys.exit(cmd_validate(url))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
