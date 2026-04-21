"""Run fingerprinting — generates a stable identifier for a command invocation."""
from __future__ import annotations

import hashlib
import os
import socket
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class FingerprintConfig:
    enabled: bool = True
    include_hostname: bool = True
    include_user: bool = True
    extra_fields: dict = field(default_factory=dict)

    @staticmethod
    def from_env() -> "FingerprintConfig":
        enabled = os.environ.get("CRONWRAP_FINGERPRINT_ENABLED", "true").lower() != "false"
        include_hostname = os.environ.get("CRONWRAP_FINGERPRINT_HOSTNAME", "true").lower() != "false"
        include_user = os.environ.get("CRONWRAP_FINGERPRINT_USER", "true").lower() != "false"
        extra_raw = os.environ.get("CRONWRAP_FINGERPRINT_EXTRA", "")
        extra: dict = {}
        if extra_raw.strip():
            for pair in extra_raw.split(","):
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    extra[k.strip()] = v.strip()
        return FingerprintConfig(
            enabled=enabled,
            include_hostname=include_hostname,
            include_user=include_user,
            extra_fields=extra,
        )


@dataclass
class Fingerprint:
    command: str
    digest: str
    components: dict


class FingerprintManager:
    def __init__(self, config: Optional[FingerprintConfig] = None) -> None:
        self.config = config or FingerprintConfig.from_env()

    def generate(self, command: str, run_id: Optional[str] = None) -> Optional[Fingerprint]:
        """Return a Fingerprint for the given command, or None if disabled."""
        if not self.config.enabled:
            return None

        components: dict = {"command": command}

        if self.config.include_hostname:
            components["hostname"] = socket.gethostname()

        if self.config.include_user:
            components["user"] = os.environ.get("USER", os.environ.get("USERNAME", ""))

        if run_id is not None:
            components["run_id"] = run_id

        components.update(self.config.extra_fields)

        raw = "|".join(f"{k}={v}" for k, v in sorted(components.items()))
        digest = hashlib.sha256(raw.encode()).hexdigest()[:16]

        return Fingerprint(command=command, digest=digest, components=components)
