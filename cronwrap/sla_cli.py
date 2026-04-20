"""CLI for SLA management and reporting."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from cronwrap.sla import SLAConfig, SLAManager, SLAViolation
from cronwrap.sla_report import print_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronwrap-sla",
        description="Inspect and manage SLA state for cron jobs.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    status_p = sub.add_parser("status", help="Show SLA config and failure counts")
    status_p.add_argument("--job", default=None, help="Job name (overrides env)")

    sub.add_parser("report", help="Print SLA violation report from state files")

    reset_p = sub.add_parser("reset", help="Reset SLA failure state for a job")
    reset_p.add_argument("--job", default=None, help="Job name (overrides env)")

    return parser


def _manager(job: str | None = None) -> SLAManager:
    cfg = SLAConfig.from_env()
    if job:
        cfg.job_name = job
    return SLAManager(cfg)


def cmd_status(args: argparse.Namespace) -> None:
    mgr = _manager(getattr(args, "job", None))
    cfg = mgr.config
    print(f"SLA enabled           : {cfg.enabled}")
    print(f"Job name              : {cfg.job_name}")
    print(f"Max duration (s)      : {cfg.max_duration_seconds}")
    print(f"Max failures/day      : {cfg.max_failures_per_day}")
    failures = mgr._load_failures_today()
    print(f"Failures today        : {len(failures)}")


def cmd_report(_args: argparse.Namespace) -> None:
    cfg = SLAConfig.from_env()
    state_dir = Path(cfg.state_dir)
    violations: list[SLAViolation] = []
    if state_dir.exists():
        for f in state_dir.glob("*.json"):
            try:
                data = json.loads(f.read_text())
                for entry in data.get("violations", []):
                    violations.append(
                        SLAViolation(
                            job_name=entry.get("job_name", f.stem),
                            reason=entry.get("reason", ""),
                            value=entry.get("value", 0.0),
                            threshold=entry.get("threshold", 0.0),
                            timestamp=entry.get("timestamp", 0.0),
                        )
                    )
            except (json.JSONDecodeError, OSError):
                continue
    print_report(violations)


def cmd_reset(args: argparse.Namespace) -> None:
    mgr = _manager(getattr(args, "job", None))
    path = mgr._state_path()
    if path.exists():
        path.unlink()
        print(f"Reset SLA state for job '{mgr.config.job_name}'.")
    else:
        print(f"No SLA state found for job '{mgr.config.job_name}'.")


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    dispatch = {"status": cmd_status, "report": cmd_report, "reset": cmd_reset}
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
