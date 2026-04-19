"""Render a summary report of escalation state across all tracked commands."""
from __future__ import annotations
import json
from typing import Dict, List
from cronwrap.escalation import EscalationConfig, EscalationManager


def load_state(config: EscalationConfig) -> Dict[str, int]:
    """Return raw failure counts keyed by command."""
    try:
        with open(config.state_file) as f:
            data = json.load(f)
        return {k: v for k, v in data.items() if isinstance(v, int)}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def render_report(config: EscalationConfig) -> str:
    state = load_state(config)
    if not state:
        return "No escalation state recorded.\n"

    lines: List[str] = []
    lines.append(f"{'Command':<50} {'Failures':>8} {'Escalated':>10}")
    lines.append("-" * 72)
    for cmd, count in sorted(state.items(), key=lambda x: -x[1]):
        escalated = "YES" if count >= config.threshold else "no"
        lines.append(f"{cmd:<50} {count:>8} {escalated:>10}")
    lines.append("")
    escalated_count = sum(1 for c in state.values() if c >= config.threshold)
    lines.append(f"Total commands tracked : {len(state)}")
    lines.append(f"Currently escalated   : {escalated_count}")
    return "\n".join(lines) + "\n"


def print_report(config: EscalationConfig | None = None) -> None:
    if config is None:
        config = EscalationConfig.from_env()
    print(render_report(config))


if __name__ == "__main__":
    print_report()
