"""Runbook: attach a URL or notes to a job for on-call reference."""
from __future__ import annotations
import os
from dataclasses import dataclass, field
from typing import Optional
from cronwrap.runner import RunResult


@dataclass
class RunbookConfig:
    enabled: bool = False
    url: str = ""
    notes: str = ""
    print_on_failure: bool = True
    print_on_success: bool = False

    @classmethod
    def from_env(cls) -> "RunbookConfig":
        url = os.environ.get("CRONWRAP_RUNBOOK_URL", "")
        enabled = bool(url)
        return cls(
            enabled=enabled,
            url=url,
            notes=os.environ.get("CRONWRAP_RUNBOOK_NOTES", ""),
            print_on_failure=os.environ.get("CRONWRAP_RUNBOOK_ON_FAILURE", "true").lower() != "false",
            print_on_success=os.environ.get("CRONWRAP_RUNBOOK_ON_SUCCESS", "false").lower() == "true",
        )


@dataclass
class RunbookEntry:
    url: str
    notes: str
    command: str
    success: bool

    def render(self) -> str:
        lines = ["=== Runbook ==="]
        if self.url:
            lines.append(f"URL:   {self.url}")
        if self.notes:
            lines.append(f"Notes: {self.notes}")
        lines.append(f"Job:   {self.command}")
        status = "SUCCESS" if self.success else "FAILURE"
        lines.append(f"Status: {status}")
        return "\n".join(lines)


class RunbookManager:
    def __init__(self, config: RunbookConfig):
        self.config = config

    def should_print(self, result: RunResult) -> bool:
        if not self.config.enabled:
            return False
        if not result.success and self.config.print_on_failure:
            return True
        if result.success and self.config.print_on_success:
            return True
        return False

    def build_entry(self, result: RunResult) -> Optional[RunbookEntry]:
        if not self.should_print(result):
            return None
        return RunbookEntry(
            url=self.config.url,
            notes=self.config.notes,
            command=result.command,
            success=result.success,
        )

    def print_runbook(self, result: RunResult) -> Optional[str]:
        entry = self.build_entry(result)
        if entry is None:
            return None
        rendered = entry.render()
        print(rendered)
        return rendered
