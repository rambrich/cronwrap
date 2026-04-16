"""Core command execution logic for cronwrap."""
from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class RunResult:
    returncode: int
    stdout: str
    stderr: str
    duration: float
    timed_out: bool = False
    attempts: int = 1


def run_command(
    cmd: List[str],
    timeout: Optional[float] = None,
    env: Optional[dict] = None,
) -> RunResult:
    """Execute a command and return a RunResult."""
    start = time.monotonic()
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
        duration = time.monotonic() - start
        return RunResult(
            returncode=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
            duration=duration,
        )
    except subprocess.TimeoutExpired as exc:
        duration = time.monotonic() - start
        return RunResult(
            returncode=1,
            stdout=exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or ""),
            stderr=exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or ""),
            duration=duration,
            timed_out=True,
        )
    except FileNotFoundError as exc:
        duration = time.monotonic() - start
        return RunResult(
            returncode=127,
            stdout="",
            stderr=str(exc),
            duration=duration,
        )
