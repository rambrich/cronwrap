"""Correlation ID management for cronwrap.

Generates and propagates a unique correlation ID for each run,
enabling tracing across logs, audit entries, webhooks, and other
output sinks.
"""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CorrelationConfig:
    """Configuration for correlation ID generation."""

    enabled: bool = True
    # If set, use this fixed prefix for generated IDs (e.g. job name)
    prefix: str = ""
    # Allow callers to inject an existing ID (e.g. from a parent system)
    inject_env_var: str = "CRONWRAP_CORRELATION_ID"

    @staticmethod
    def from_env() -> "CorrelationConfig":
        """Build config from environment variables."""
        enabled = os.environ.get("CRONWRAP_CORRELATION_ENABLED", "true").lower() not in (
            "false",
            "0",
            "no",
        )
        prefix = os.environ.get("CRONWRAP_CORRELATION_PREFIX", "")
        inject_env_var = os.environ.get(
            "CRONWRAP_CORRELATION_INJECT_VAR", "CRONWRAP_CORRELATION_ID"
        )
        return CorrelationConfig(
            enabled=enabled,
            prefix=prefix,
            inject_env_var=inject_env_var,
        )


@dataclass
class CorrelationManager:
    """Manages the lifecycle of a correlation ID for a single run."""

    config: CorrelationConfig
    _correlation_id: Optional[str] = field(default=None, init=False, repr=False)

    def generate(self) -> Optional[str]:
        """Generate or retrieve the correlation ID for this run.

        Priority:
          1. Already generated (idempotent within a run)
          2. Injected via environment variable
          3. Freshly generated UUID (with optional prefix)
          4. None if disabled
        """
        if not self.config.enabled:
            return None

        if self._correlation_id is not None:
            return self._correlation_id

        # Check for an injected ID from the environment
        injected = os.environ.get(self.config.inject_env_var, "").strip()
        if injected:
            self._correlation_id = injected
            return self._correlation_id

        # Generate a new ID
        unique = uuid.uuid4().hex
        if self.config.prefix:
            self._correlation_id = f"{self.config.prefix}-{unique}"
        else:
            self._correlation_id = unique

        return self._correlation_id

    @property
    def current(self) -> Optional[str]:
        """Return the current correlation ID without generating a new one."""
        return self._correlation_id

    def reset(self) -> None:
        """Clear the stored correlation ID (useful between runs in tests)."""
        self._correlation_id = None

    def as_dict(self) -> dict:
        """Return the correlation ID as a dict suitable for log enrichment."""
        cid = self._correlation_id
        if cid is None:
            return {}
        return {"correlation_id": cid}
