"""Redact sensitive values from command strings and environment variables."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import List

_DEFAULT_PATTERNS = [
    r"(?i)(password|passwd|secret|token|api[_-]?key|auth)=[^\s&]+",
]


@dataclass
class RedactConfig:
    enabled: bool = True
    extra_patterns: List[str] = field(default_factory=list)

    @classmethod
    def from_env(cls) -> "RedactConfig":
        enabled = os.environ.get("CRONWRAP_REDACT_ENABLED", "true").lower() != "false"
        raw = os.environ.get("CRONWRAP_REDACT_PATTERNS", "")
        extra = [p.strip() for p in raw.split(",") if p.strip()]
        return cls(enabled=enabled, extra_patterns=extra)


class Redactor:
    def __init__(self, config: RedactConfig) -> None:
        self.config = config
        patterns = _DEFAULT_PATTERNS + config.extra_patterns
        self._regexes = [re.compile(p) for p in patterns]

    def redact(self, text: str) -> str:
        if not self.config.enabled:
            return text
        for regex in self._regexes:
            text = regex.sub(lambda m: _mask_value(m.group(0)), text)
        return text

    def redact_env(self, env: dict) -> dict:
        if not self.config.enabled:
            return env
        sensitive = re.compile(
            r"(?i)(password|passwd|secret|token|api[_-]?key|auth)"
        )
        return {
            k: "***" if sensitive.search(k) else v
            for k, v in env.items()
        }


def _mask_value(match: str) -> str:
    if "=" in match:
        key, _ = match.split("=", 1)
        return f"{key}=***"
    return "***"
