"""Dependency check: ensure external commands/services are available before running."""
from __future__ import annotations
import os
import shutil
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class DependencyConfig:
    enabled: bool = False
    commands: List[str] = field(default_factory=list)
    env_vars: List[str] = field(default_factory=list)

    @staticmethod
    def from_env() -> "DependencyConfig":
        enabled = os.environ.get("CRONWRAP_DEP_CHECK", "").lower() in ("1", "true")
        commands = [
            c.strip()
            for c in os.environ.get("CRONWRAP_DEP_COMMANDS", "").split(",")
            if c.strip()
        ]
        env_vars = [
            v.strip()
            for v in os.environ.get("CRONWRAP_DEP_ENV_VARS", "").split(",")
            if v.strip()
        ]
        return DependencyConfig(enabled=enabled, commands=commands, env_vars=env_vars)


@dataclass
class MissingDependencyError:
    missing_commands: List[str] = field(default_factory=list)
    missing_env_vars: List[str] = field(default_factory=list)

    def __bool__(self) -> bool:
        return bool(self.missing_commands or self.missing_env_vars)

    def __str__(self) -> str:
        parts = []
        if self.missing_commands:
            parts.append("Missing commands: " + ", ".join(self.missing_commands))
        if self.missing_env_vars:
            parts.append("Missing env vars: " + ", ".join(self.missing_env_vars))
        return "; ".join(parts)


class DependencyChecker:
    def __init__(self, config: Optional[DependencyConfig] = None) -> None:
        self.config = config or DependencyConfig.from_env()

    def check(self) -> Optional[MissingDependencyError]:
        if not self.config.enabled:
            return None
        missing_cmds = [
            cmd for cmd in self.config.commands if shutil.which(cmd) is None
        ]
        missing_vars = [
            var for var in self.config.env_vars if var not in os.environ
        ]
        error = MissingDependencyError(missing_commands=missing_cmds, missing_env_vars=missing_vars)
        return error if error else None
