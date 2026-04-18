"""CLI tool to inspect/reset debounce state for a job."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from cronwrap.debounce import DebounceConfig


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronwrap-debounce",
        description="Inspect or reset debounce state for a cron job.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    status_p = sub.add_parser("status", help="Show last-run timestamp for a job")
    status_p.add_argument("job_id", help="Job identifier")

    reset_p = sub.add_parser("reset", help="Clear debounce state for a job")
    reset_p.add_argument("job_id", help="Job identifier")

    return parser


def _state_path(cfg: DebounceConfig, job_id: str) -> Path:
    return Path(cfg.state_dir) / f"{job_id}.json"


def cmd_status(cfg: DebounceConfig, job_id: str) -> None:
    path = _state_path(cfg, job_id)
    if not path.exists():
        print(f"No debounce state found for job '{job_id}'.")
        return
    data = json.loads(path.read_text())
    last_run = data.get("last_run", "unknown")
    print(f"Job '{job_id}' last run: {last_run}")


def cmd_reset(cfg: DebounceConfig, job_id: str) -> None:
    path = _state_path(cfg, job_id)
    if path.exists():
        path.unlink()
        print(f"Debounce state cleared for job '{job_id}'.")
    else:
        print(f"No debounce state to clear for job '{job_id}'.")


def main(argv=None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    cfg = DebounceConfig.from_env()

    if args.command == "status":
        cmd_status(cfg, args.job_id)
    elif args.command == "reset":
        cmd_reset(cfg, args.job_id)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
