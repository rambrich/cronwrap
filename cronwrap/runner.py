import subprocess
import time
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class RunResult:
    command: str
    returncode: int
    stdout: str
    stderr: str
    duration: float
    attempts: int
    success: bool


def run_command(
    command: str,
    timeout: Optional[int] = None,
    retries: int = 0,
    retry_delay: float = 5.0,
) -> RunResult:
    """Execute a shell command with optional retries.

    Args:
        command: Shell command string to execute.
        timeout: Seconds before the command is killed. None means no limit.
        retries: Number of additional attempts after first failure.
        retry_delay: Seconds to wait between retry attempts.

    Returns:
        RunResult with execution details.
    """
    attempts = 0
    max_attempts = retries + 1
    last_result = None

    while attempts < max_attempts:
        attempts += 1
        logger.info("Running command (attempt %d/%d): %s", attempts, max_attempts, command)
        start = time.monotonic()

        try:
            proc = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            duration = time.monotonic() - start
            last_result = RunResult(
                command=command,
                returncode=proc.returncode,
                stdout=proc.stdout,
                stderr=proc.stderr,
                duration=duration,
                attempts=attempts,
                success=proc.returncode == 0,
            )
        except subprocess.TimeoutExpired:
            duration = time.monotonic() - start
            logger.warning("Command timed out after %.1fs", duration)
            last_result = RunResult(
                command=command,
                returncode=-1,
                stdout="",
                stderr=f"Command timed out after {timeout}s",
                duration=duration,
                attempts=attempts,
                success=False,
            )

        if last_result.success:
            logger.info("Command succeeded in %.2fs", last_result.duration)
            return last_result

        if attempts < max_attempts:
            logger.warning(
                "Command failed (rc=%d). Retrying in %.1fs...",
                last_result.returncode,
                retry_delay,
            )
            time.sleep(retry_delay)

    last_result.attempts = attempts
    logger.error("Command failed after %d attempt(s).", attempts)
    return last_result
