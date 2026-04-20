"""Run metadata tagging and enrichment for cronwrap."""
from __future__ import annotations

import os
import socket
import getpass
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class MetadataConfig:
    enabled: bool = True
    include_hostname: bool = True
    include_user: bool = True
    extra: Dict[str, str] = field(default_factory=dict)

    @staticmethod
    def from_env() -> "MetadataConfig":
        enabled = os.environ.get("CRONWRAP_METADATA_ENABLED", "true").lower() != "false"
        include_hostname = os.environ.get("CRONWRAP_METADATA_HOSTNAME", "true").lower() != "false"
        include_user = os.environ.get("CRONWRAP_METADATA_USER", "true").lower() != "false"
        extra: Dict[str, str] = {}
        raw = os.environ.get("CRONWRAP_METADATA_EXTRA", "")
        if raw:
            for pair in raw.split(","):
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    extra[k.strip()] = v.strip()
        return MetadataConfig(
            enabled=enabled,
            include_hostname=include_hostname,
            include_user=include_user,
            extra=extra,
        )


@dataclass
class RunMetadata:
    hostname: Optional[str] = None
    user: Optional[str] = None
    extra: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, object]:
        d: Dict[str, object] = {}
        if self.hostname is not None:
            d["hostname"] = self.hostname
        if self.user is not None:
            d["user"] = self.user
        if self.extra:
            d["extra"] = self.extra
        return d


class MetadataManager:
    def __init__(self, config: MetadataConfig) -> None:
        self.config = config

    def collect(self) -> Optional[RunMetadata]:
        if not self.config.enabled:
            return None
        hostname = None
        user = None
        if self.config.include_hostname:
            try:
                hostname = socket.gethostname()
            except Exception:
                hostname = "unknown"
        if self.config.include_user:
            try:
                user = getpass.getuser()
            except Exception:
                user = "unknown"
        return RunMetadata(hostname=hostname, user=user, extra=dict(self.config.extra))
