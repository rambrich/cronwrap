"""Pre/post execution hooks for cronwrap."""
from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass, field
from typing import List, Optional

from cronwrap.runner import RunResult

logger = logging.getLogger(__name__)


@dataclass
class HooksConfig:
    pre_hooks: List[str] = field(default_factory=list)
    post_hooks: List[str] = field(default_factory=list)
    enabled: bool = True

    @classmethod
    def from_env(cls, env: dict) -> "HooksConfig":
        pre_raw = env.get("CRONWRAP_PRE_HOOKS", "")
        post_raw = env.get("CRONWRAP_POST_HOOKS", "")
        pre = [h.strip() for h in pre_raw.split(",") if h.strip()]
        post = [h.strip() for h in post_raw.split(",") if h.strip()]
        enabled = env.get("CRONWRAP_HOOKS_ENABLED", "true").lower() != "false"
        return cls(pre_hooks=pre, post_hooks=post, enabled=enabled)


def _run_hook(command: str, timeout: int = 30) -> bool:
    """Run a single hook command. Returns True on success."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            timeout=timeout,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            logger.warning("Hook failed [%s]: %s", command, result.stderr.strip())
            return False
        logger.debug("Hook succeeded [%s]", command)
        return True
    except subprocess.TimeoutExpired:
        logger.warning("Hook timed out [%s]", command)
        return False
    except Exception as exc:  # noqa: BLE001
        logger.warning("Hook error [%s]: %s", command, exc)
        return False


@dataclass
class HookManager:
    config: HooksConfig

    def run_pre_hooks(self) -> List[bool]:
        if not self.config.enabled:
            return []
        results = []
        for hook in self.config.pre_hooks:
            logger.info("Running pre-hook: %s", hook)
            results.append(_run_hook(hook))
        return results

    def run_post_hooks(self, result: Optional[RunResult] = None) -> List[bool]:
        if not self.config.enabled:
            return []
        results = []
        for hook in self.config.post_hooks:
            logger.info("Running post-hook: %s", hook)
            results.append(_run_hook(hook))
        return results

    def all_pre_hooks_passed(self) -> bool:
        """Run all pre-hooks and return True only if every hook succeeded.

        Returns True when there are no pre-hooks configured (vacuously true).
        """
        results = self.run_pre_hooks()
        return all(results) if results else True
