"""CLI sub-commands for interacting with the audit log."""
from __future__ import annotations

import argparse
import sys

from cronwrap.audit import AuditConfig, AuditLogger
from cronwrap.audit_report import print_report, render_report


def build_audit_parser(subparsers=None) -> argparse.ArgumentParser:
    if subparsers is not None:
        parser = subparsers.add_parser("audit", help="Audit log commands")
    else:
        parser = argparse.ArgumentParser(prog="cronwrap audit")
    sub = parser.add_subparsers(dest="audit_cmd")

    show = sub.add_parser("show", help="Print raw audit log entries")
    show.add_argument("--log", default=None, help="Path to audit log file")
    show.add_argument("--limit", type=int, default=20, help="Max entries to show")

    report = sub.add_parser("report", help="Print summary report")
    report.add_argument("--log", default=None, help="Path to audit log file")
    return parser


def _load_entries(args: argparse.Namespace):
    """Load audit entries from the configured or specified log file.

    Exits with an error message if the log file cannot be read.
    """
    config = AuditConfig.from_env()
    config.enabled = True  # reading always allowed
    if args.log:
        config.log_path = args.log

    logger = AuditLogger(config)
    try:
        return logger.read_all()
    except OSError as exc:
        print(f"Error reading audit log: {exc}", file=sys.stderr)
        sys.exit(1)


def run_audit_cli(args: argparse.Namespace) -> int:
    entries = _load_entries(args)

    if args.audit_cmd == "show":
        for entry in entries[-args.limit:]:
            status = "OK" if entry.success else "FAIL"
            print(f"{entry.timestamp}  [{status}]  {entry.command}  ({entry.duration:.2f}s)")
        return 0

    if args.audit_cmd == "report":
        print_report(entries)
        return 0

    print("No audit sub-command given. Use 'show' or 'report'.", file=sys.stderr)
    return 1


def main() -> None:  # pragma: no cover
    parser = build_audit_parser()
    args = parser.parse_args()
    sys.exit(run_audit_cli(args))
