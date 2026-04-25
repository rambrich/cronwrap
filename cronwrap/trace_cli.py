"""CLI for inspecting cronwrap trace files."""
from __future__ import annotations

import argparse
import sys

from cronwrap.trace import TraceConfig, TraceManager
from cronwrap.trace_report import print_trace_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronwrap-trace",
        description="Inspect cronwrap execution traces",
    )
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("list", help="List all trace entries")

    show = sub.add_parser("show", help="Show a single trace entry")
    show.add_argument("trace_id", help="Trace ID to show")

    sub.add_parser("report", help="Print summary report")
    return parser


def _manager() -> TraceManager:
    return TraceManager(TraceConfig.from_env())


def cmd_list(args: argparse.Namespace) -> None:
    mgr = _manager()
    traces = mgr.list_traces()
    if not traces:
        print("No traces found.")
        return
    for t in traces:
        ok = "OK" if t.get("success") else "FAIL"
        print(f"{t.get('trace_id','')}  {ok}  {t.get('command','')}  {t.get('duration',0):.2f}s")


def cmd_show(args: argparse.Namespace) -> None:
    """Load and pretty-print a single trace entry by ID."""
    mgr = _manager()
    entry = mgr.load(args.trace_id)
    if entry is None:
        print(f"Trace not found: {args.trace_id}", file=sys.stderr)
        sys.exit(1)
    import json
    print(json.dumps(entry, indent=2))


def cmd_report(args: argparse.Namespace) -> None:
    mgr = _manager()
    traces = mgr.list_traces()
    if not traces:
        print("No traces found.")
        return
    print_trace_report(traces)


def main(argv=None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    dispatch = {"list": cmd_list, "show": cmd_show, "report": cmd_report}
    fn = dispatch.get(args.cmd)
    if fn is None:
        parser.print_help()
        sys.exit(0)
    fn(args)


if __name__ == "__main__":
    main()
