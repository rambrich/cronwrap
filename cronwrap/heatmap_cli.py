"""CLI for inspecting heatmap state."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cronwrap.heatmap import HeatmapConfig, HeatmapManager, HeatmapState

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="cronwrap-heatmap", description="Heatmap CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    st = sub.add_parser("status", help="Show heatmap for a job")
    st.add_argument("job", help="Job name")

    rs = sub.add_parser("reset", help="Clear heatmap state for a job")
    rs.add_argument("job", help="Job name")

    return p


def _manager(args: argparse.Namespace) -> HeatmapManager:
    cfg = HeatmapConfig.from_env()
    return HeatmapManager(cfg, args.job)


def cmd_status(args: argparse.Namespace) -> None:
    mgr = _manager(args)
    if not mgr.config.enabled:
        print("Heatmap is disabled (set CRONWRAP_HEATMAP_ENABLED=true).")
        return
    state = mgr.load()
    if state is None or not state.counts:
        print(f"No heatmap data for job '{args.job}'.")
        return
    print(f"Heatmap for '{args.job}' (UTC)")
    print(f"  {'':4s}" + "".join(f"{h:3d}" for h in range(24)))
    for d in range(7):
        row = state.counts.get(str(d), {})
        cells = "".join(f"{row.get(str(h), 0):3d}" for h in range(24))
        print(f"  {DAYS[d]:4s}{cells}")
    hot = state.hottest_slot()
    if hot:
        print(f"  Hottest slot: {DAYS[hot[0]]} {hot[1]:02d}:00 UTC")


def cmd_reset(args: argparse.Namespace) -> None:
    mgr = _manager(args)
    p = mgr._state_path()
    if p.exists():
        p.unlink()
        print(f"Heatmap state for '{args.job}' cleared.")
    else:
        print(f"No heatmap state found for '{args.job}'.")


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.cmd == "status":
        cmd_status(args)
    elif args.cmd == "reset":
        cmd_reset(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
