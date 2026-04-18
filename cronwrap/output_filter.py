"""Filter and truncate command output before logging or alerting."""
from __future__ import annotations
import os
import re
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class OutputFilterConfig:
    enabled: bool = True
    max_bytes: int = 65536  # 64 KB
    strip_ansi: bool = True
    exclude_patterns: List[str] = field(default_factory=list)

    @classmethod
    def from_env(cls) -> "OutputFilterConfig":
        enabled = os.environ.get("CRONWRAP_OUTPUT_FILTER_ENABLED", "true").lower() != "false"
        max_bytes = int(os.environ.get("CRONWRAP_OUTPUT_MAX_BYTES", "65536"))
        strip_ansi = os.environ.get("CRONWRAP_OUTPUT_STRIP_ANSI", "true").lower() != "false"
        raw_patterns = os.environ.get("CRONWRAP_OUTPUT_EXCLUDE_PATTERNS", "")
        patterns = [p.strip() for p in raw_patterns.split(",") if p.strip()]
        return cls(enabled=enabled, max_bytes=max_bytes, strip_ansi=strip_ansi, exclude_patterns=patterns)


_ANSI_ESCAPE = re.compile(r"\x1B[@-_][0-?]*[ -/]*[@-~]")


class OutputFilter:
    def __init__(self, config: Optional[OutputFilterConfig] = None) -> None:
        self.config = config or OutputFilterConfig()
        self._compiled = [re.compile(p) for p in self.config.exclude_patterns]

    def filter(self, text: str) -> str:
        if not self.config.enabled:
            return text
        if self.config.strip_ansi:
            text = _ANSI_ESCAPE.sub("", text)
        if self._compiled:
            lines = text.splitlines(keepends=True)
            lines = [l for l in lines if not any(p.search(l) for p in self._compiled)]
            text = "".join(lines)
        if len(text.encode()) > self.config.max_bytes:
            encoded = text.encode()
            truncated = encoded[: self.config.max_bytes]
            text = truncated.decode(errors="replace") + "\n[output truncated]"
        return text
