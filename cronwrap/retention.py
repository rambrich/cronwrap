"""Retention policy for cleaning up old log, history, and audit files."""

from __future__ import annotations

import os
import time
import glob
import logging
from dataclasses import dataclass, field
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class RetentionConfig:
    """Configuration for the retention policy."""

    enabled: bool = False
    max_age_days: float = 30.0
    paths: List[str] = field(default_factory=list)
    dryn
    @staticmethod
    def from_env() -> "RetentionConfig":
        """Load retention configuration from environment variables.

        Environment variables:
            CRONWRAP_RETENTION_ENABLED:      Enable retention cleanup (default: false)
            CRONWRAP_RETENTION_MAX_AGE_DAYS: Maximum age of files in days (default: 30)
            CRONWRAP_RETENTION_PATHS:        Colon-separated glob patterns to clean up
            CRONWRAP_RETENTION_DRY_RUN:      Log deletions without removing files (default: false)
        """
        enabled = os.environ.get("CRONWRAP_RETENTION_ENABLED", "").lower() in ("1", "true", "yes")
        dry_run = os.environ.get("CRONWRAP_RETENTION_DRY_RUN", "").lower() in ("1", "true", "yes")

        try:
            max_age_days = float(os.environ.get("CRONWRAP_RETENTION_MAX_AGE_DAYS", "30"))
        except ValueError:
            max_age_days = 30.0

        raw_paths = os.environ.get("CRONWRAP_RETENTION_PATHS", "")
        paths = [p.strip() for p in raw_paths.split(":") if p.strip()] if raw_paths else []

        return RetentionConfig(
            enabled=enabled,
            max_age_days=max_age_days,
            paths=paths,
            dry_run=dry_run,
        )


@dataclass
class RetentionResult:
    """Result of a retention cleanup run."""

    deleted: List[str] = field(default_factory=list)
    skipped: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    @property
    def total_deleted(self) -> int:
        return len(self.deleted)

    @property
    def total_errors(self) -> int:
        return len(self.errors)


class RetentionManager:
    """Applies the retention policy by deleting files older than max_age_days."""

    def __init__(self, config: Optional[RetentionConfig] = None) -> None:
        self.config = config or RetentionConfig.from_env()

    def apply(self) -> RetentionResult:
        """Scan configured paths and delete files exceeding the retention age.

        Returns a RetentionResult summarising what was deleted, skipped, or errored.
        """
        result = RetentionResult()

        if not self.config.enabled:
            logger.debug("Retention policy disabled; skipping cleanup.")
            return result

        if not self.config.paths:
            logger.debug("Retention policy enabled but no paths configured.")
            return result

        cutoff = time.time() - self.config.max_age_days * 86400

        for pattern in self.config.paths:
            matched = glob.glob(pattern, recursive=True)
            for filepath in matched:
                if not os.path.isfile(filepath):
                    result.skipped.append(filepath)
                    continue
                try:
                    mtime = os.path.getmtime(filepath)
                    if mtime < cutoff:
                        if self.config.dry_run:
                            logger.info("[dry-run] Would delete: %s", filepath)
                        else:
                            os.remove(filepath)
                            logger.info("Deleted: %s", filepath)
                        result.deleted.append(filepath)
                    else:
                        result.skipped.append(filepath)
                except OSError as exc:
                    logger.warning("Error processing %s: %s", filepath, exc)
                    result.errors.append(filepath)

        return result
