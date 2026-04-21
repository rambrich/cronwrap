"""CLI for inspecting and resetting forecast state."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from cronwrap.forecast import ForecastConfig, ForecastManager


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronwrap-forecast",
        description="Manage cronwrap run forecasts",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    status_p = sub.add_parser("status", help="Show forecast for a job")
    status_p.add_argument("job_id", help="Job identifier")
    status_p.add_argument("--json", dest="as_json", action="store_true")

    reset_p = sub.add_parser("reset", help="Clear forecast history for a job")
    reset_p.add_argument("job_id", help="Job identifier")

    return parser


def _manager() -> ForecastManager:
    return ForecastManager(config=ForecastConfig.from_env())


def cmd_status(args: argparse.Namespace) -> None:
    mgr = _manager()
    if not mgr.config.enabled:
        print("Forecast is disabled (set CRONWRAP_FORECAST_ENABLED=true to enable)")
        return
    result = mgr.predict(args.job_id)
    if result is None:
        print(f"No forecast data for job '{args.job_id}'")
        return
    if args.as_json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        sym = "✓" if result.predicted_success else "✗"
        print(f"Forecast for '{args.job_id}': {sym}")
        print(f"  Samples      : {result.sample_size}")
        print(f"  Failure rate : {result.failure_rate:.1%}")
        print(f"  Avg duration : {result.avg_duration:.1f}s")
        print(f"  Prediction   : {'success' if result.predicted_success else 'failure'}")


def cmd_reset(args: argparse.Namespace) -> None:
    mgr = _manager()
    path = mgr._state_path(args.job_id)
    if path.exists():
        path.unlink()
        print(f"Forecast history cleared for '{args.job_id}'")
    else:
        print(f"No forecast history found for '{args.job_id}'")


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "status":
        cmd_status(args)
    elif args.command == "reset":
        cmd_reset(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
