"""CLI tool to inspect and reset circuit breaker state."""
from __future__ import annotations
import argparse
import json
import sys
import time
from pathlib import Path
from cronwrap.circuit_breaker import CircuitBreakerConfig


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="cronwrap-circuit",
        description="Inspect or reset circuit breaker state for a job.",
    )
    p.add_argument("job", help="Job name")
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("status", help="Show current circuit state")
    sub.add_parser("reset", help="Reset circuit to closed state")
    return p


def _state_path(cfg: CircuitBreakerConfig, job: str) -> Path:
    return Path(cfg.state_dir) / f"{job}.json"


def cmd_status(cfg: CircuitBreakerConfig, job: str) -> None:
    path = _state_path(cfg, job)
    if not path.exists():
        print(f"[{job}] No state found — circuit CLOSED")
        return
    data = json.loads(path.read_text())
    failures = data.get("failures", [])
    opened_at = data.get("opened_at")
    now = time.time()
    recent = [t for t in failures if t > now - cfg.window]
    if opened_at and (now - opened_at) < cfg.cooldown:
        remaining = cfg.cooldown - (now - opened_at)
        print(f"[{job}] Circuit OPEN — cooldown {remaining:.0f}s remaining")
    else:
        print(f"[{job}] Circuit CLOSED — {len(recent)} failure(s) in window")


def cmd_reset(cfg: CircuitBreakerConfig, job: str) -> None:
    path = _state_path(cfg, job)
    if path.exists():
        path.write_text(json.dumps({"failures": [], "opened_at": None}))
        print(f"[{job}] Circuit reset to CLOSED")
    else:
        print(f"[{job}] No state to reset")


def main(argv=None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.cmd:
        parser.print_help()
        sys.exit(1)
    cfg = CircuitBreakerConfig.from_env()
    if args.cmd == "status":
        cmd_status(cfg, args.job)
    elif args.cmd == "reset":
        cmd_reset(cfg, args.job)


if __name__ == "__main__":
    main()
