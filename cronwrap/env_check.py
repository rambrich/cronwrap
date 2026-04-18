"""Validates required environment variables before running a cron job."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class EnvCheckConfig:
    enabled: bool = False
    required_vars: List[str] = field(default_factory=list)

    @staticmethod
    def from_env() -> "EnvCheckConfig":
        raw = os.environ.get("CRONWRAP_REQUIRED_ENV", "").strip()
        if not raw:
            return EnvCheckConfig(enabled=False)
        vars_ = [v.strip() for v in raw.split(",") if v.strip()]
        return EnvCheckConfig(enabled=bool(vars_), required_vars=vars_)


@dataclass
class MissingVarsError(Exception):
    missing: List[str]

    def __str__(self) -> str:
        return f"Missing required environment variables: {', '.join(self.missing)}"


class EnvChecker:
    def __init__(self, config: EnvCheckConfig) -> None:
        self.config = config

    def check(self) -> Optional[MissingVarsError]:
        """Return MissingVarsError if any required vars are absent, else None."""
        if not self.config.enabled:
            return None
        missing = [v for v in self.config.required_vars if v not in os.environ]
        if missing:
            return MissingVarsError(missing=missing)
        return None

    def assert_ok(self) -> None:
        """Raise MissingVarsError if any required vars are absent."""
        err = self.check()
        if err:
            raise err
