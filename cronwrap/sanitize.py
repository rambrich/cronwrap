"""Output sanitization: strip ANSI codes and control characters."""
from __future__ import annotations
import os
import re
from dataclasses import dataclass, field
from typing import List

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[mABCDEFGHJKSTfhilmnprsu]")
_CTRL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


@dataclass
class SanitizeConfig:
    enabled: bool = True
    strip_ansi: bool = True
    strip_control: bool = True
    extra_patterns: List[str] = field(default_factory=list)

    @staticmethod
    def from_env() -> "SanitizeConfig":
        enabled = os.environ.get("CRONWRAP_SANITIZE_ENABLED", "true").lower() != "false"
        strip_ansi = os.environ.get("CRONWRAP_SANITIZE_ANSI", "true").lower() != "false"
        strip_ctrl = os.environ.get("CRONWRAP_SANITIZE_CONTROL", "true").lower() != "false"
        raw = os.environ.get("CRONWRAP_SANITIZE_PATTERNS", "")
        patterns = [p.strip() for p in raw.split(",") if p.strip()]
        return SanitizeConfig(
            enabled=enabled,
            strip_ansi=strip_ansi,
            strip_control=strip_ctrl,
            extra_patterns=patterns,
        )


class Sanitizer:
    def __init__(self, config: SanitizeConfig) -> None:
        self.config = config
        self._extra = [re.compile(p) for p in config.extra_patterns]

    def sanitize(self, text: str) -> str:
        if not self.config.enabled:
            return text
        if self.config.strip_ansi:
            text = _ANSI_RE.sub("", text)
        if self.config.strip_control:
            text = _CTRL_RE.sub("", text)
        for pattern in self._extra:
            text = pattern.sub("", text)
        return text
