"""Pre-execution output scanning: checks command output against patterns before acting."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import List, Optional

from cronwrap.runner import RunResult


@dataclass
class PrescanConfig:
    enabled: bool = False
    warn_patterns: List[str] = field(default_factory=list)
    fail_patterns: List[str] = field(default_factory=list)

    @classmethod
    def from_env(cls) -> "PrescanConfig":
        enabled = os.environ.get("CRONWRAP_PRESCAN_ENABLED", "false").lower() == "true"
        warn_raw = os.environ.get("CRONWRAP_PRESCAN_WARN_PATTERNS", "")
        fail_raw = os.environ.get("CRONWRAP_PRESCAN_FAIL_PATTERNS", "")
        warn_patterns = [p for p in warn_raw.split(",") if p.strip()]
        fail_patterns = [p for p in fail_raw.split(",") if p.strip()]
        return cls(enabled=enabled, warn_patterns=warn_patterns, fail_patterns=fail_patterns)


@dataclass
class PrescanResult:
    matched_warn: List[str] = field(default_factory=list)
    matched_fail: List[str] = field(default_factory=list)

    @property
    def has_warnings(self) -> bool:
        return bool(self.matched_warn)

    @property
    def has_failures(self) -> bool:
        return bool(self.matched_fail)


class PrescanManager:
    def __init__(self, config: Optional[PrescanConfig] = None) -> None:
        self.config = config or PrescanConfig.from_env()

    def scan(self, result: RunResult) -> Optional[PrescanResult]:
        if not self.config.enabled:
            return None
        output = (result.stdout or "") + (result.stderr or "")
        matched_warn = [
            p for p in self.config.warn_patterns if re.search(p, output)
        ]
        matched_fail = [
            p for p in self.config.fail_patterns if re.search(p, output)
        ]
        return PrescanResult(matched_warn=matched_warn, matched_fail=matched_fail)

    def should_override_failure(self, prescan: Optional[PrescanResult]) -> bool:
        """Return True if prescan detected a fail pattern (forces failure regardless of exit code)."""
        if prescan is None:
            return False
        return prescan.has_failures
