"""Pattern-based output matching: flag runs whose output matches known patterns."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import List, Optional

from cronwrap.runner import RunResult


@dataclass
class PatternConfig:
    enabled: bool = False
    warn_patterns: List[str] = field(default_factory=list)
    fail_patterns: List[str] = field(default_factory=list)

    @classmethod
    def from_env(cls) -> "PatternConfig":
        enabled = os.environ.get("CRONWRAP_PATTERN_ENABLED", "").lower() == "true"
        warn_raw = os.environ.get("CRONWRAP_PATTERN_WARN", "")
        fail_raw = os.environ.get("CRONWRAP_PATTERN_FAIL", "")
        warn_patterns = [p.strip() for p in warn_raw.split(",") if p.strip()]
        fail_patterns = [p.strip() for p in fail_raw.split(",") if p.strip()]
        return cls(enabled=enabled, warn_patterns=warn_patterns, fail_patterns=fail_patterns)


@dataclass
class PatternMatch:
    level: str  # "warn" or "fail"
    pattern: str
    matched_line: str

    def to_dict(self) -> dict:
        return {"level": self.level, "pattern": self.pattern, "matched_line": self.matched_line}


@dataclass
class PatternResult:
    matches: List[PatternMatch] = field(default_factory=list)

    @property
    def has_failures(self) -> bool:
        return any(m.level == "fail" for m in self.matches)

    @property
    def has_warnings(self) -> bool:
        return any(m.level == "warn" for m in self.matches)


class PatternMatcher:
    def __init__(self, config: PatternConfig) -> None:
        self.config = config

    def check(self, result: RunResult) -> Optional[PatternResult]:
        if not self.config.enabled:
            return None
        output = (result.stdout or "") + (result.stderr or "")
        matches: List[PatternMatch] = []
        for line in output.splitlines():
            for pat in self.config.fail_patterns:
                if re.search(pat, line):
                    matches.append(PatternMatch(level="fail", pattern=pat, matched_line=line))
            for pat in self.config.warn_patterns:
                if re.search(pat, line):
                    matches.append(PatternMatch(level="warn", pattern=pat, matched_line=line))
        return PatternResult(matches=matches)
