"""Label support for tagging runs with key=value metadata."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class LabelConfig:
    enabled: bool = False
    labels: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_env(cls) -> "LabelConfig":
        raw = os.environ.get("CRONWRAP_LABELS", "").strip()
        if not raw:
            return cls(enabled=False)
        labels = parse_labels(raw)
        return cls(enabled=True, labels=labels)


def parse_labels(raw: str) -> Dict[str, str]:
    """Parse 'key=value,key2=value2' into a dict."""
    result: Dict[str, str] = {}
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        if "=" in part:
            k, _, v = part.partition("=")
            result[k.strip()] = v.strip()
        else:
            result[part] = ""
    return result


def matches_labels(labels: Dict[str, str], selector: Dict[str, str]) -> bool:
    """Return True if all selector key/value pairs are present in labels."""
    for k, v in selector.items():
        if labels.get(k) != v:
            return False
    return True


@dataclass
class LabelManager:
    config: LabelConfig

    def get_labels(self) -> Dict[str, str]:
        if not self.config.enabled:
            return {}
        return dict(self.config.labels)

    def annotate(self, data: dict) -> dict:
        """Merge labels into a copy of data under 'labels' key."""
        result = dict(data)
        result["labels"] = self.get_labels()
        return result

    def filter_entries(self, entries: List[dict], selector: Dict[str, str]) -> List[dict]:
        """Return entries whose labels match the selector."""
        if not selector:
            return entries
        return [
            e for e in entries
            if matches_labels(e.get("labels") or {}, selector)
        ]
