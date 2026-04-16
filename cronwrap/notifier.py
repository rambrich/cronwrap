"""Alert/notification support for cronwrap."""

import smtplib
import os
from email.mime.text import MIMEText
from dataclasses import dataclass, field
from typing import Optional

from cronwrap.runner import RunResult


@dataclass
class NotifierConfig:
    smtp_host: str = "localhost"
    smtp_port: int = 25
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    from_addr: str = "cronwrap@localhost"
    to_addrs: list = field(default_factory=list)
    use_tls: bool = False

    @classmethod
    def from_env(cls) -> "NotifierConfig":
        return cls(
            smtp_host=os.environ.get("CRONWRAP_SMTP_HOST", "localhost"),
            smtp_port=int(os.environ.get("CRONWRAP_SMTP_PORT", "25")),
            smtp_user=os.environ.get("CRONWRAP_SMTP_USER"),
            smtp_password=os.environ.get("CRONWRAP_SMTP_PASSWORD"),
            from_addr=os.environ.get("CRONWRAP_FROM", "cronwrap@localhost"),
            to_addrs=[
                a.strip()
                for a in os.environ.get("CRONWRAP_ALERT_TO", "").split(",")
                if a.strip()
            ],
            use_tls=os.environ.get("CRONWRAP_SMTP_TLS", "").lower() in ("1", "true"),
        )


class Notifier:
    def __init__(self, config: NotifierConfig):
        self.config = config

    def should_notify(self) -> bool:
        return bool(self.config.to_addrs)

    def notify_failure(self, result: RunResult, job_name: str = "cron job") -> None:
        if not self.should_notify():
            return
        subject = f"[cronwrap] FAILED: {job_name}"
        body = (
            f"Job '{job_name}' failed.\n\n"
            f"Command: {result.command}\n"
            f"Exit code: {result.returncode}\n"
            f"Attempts: {result.attempts}\n\n"
            f"--- stdout ---\n{result.stdout}\n\n"
            f"--- stderr ---\n{result.stderr}\n"
        )
        self._send(subject, body)

    def notify_success(self, result: RunResult, job_name: str = "cron job") -> None:
        if not self.should_notify():
            return
        subject = f"[cronwrap] OK: {job_name}"
        body = (
            f"Job '{job_name}' succeeded.\n\n"
            f"Command: {result.command}\n"
            f"Exit code: {result.returncode}\n"
            f"Attempts: {result.attempts}\n\n"
            f"--- stdout ---\n{result.stdout}\n"
        )
        self._send(subject, body)

    def _send(self, subject: str, body: str) -> None:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = self.config.from_addr
        msg["To"] = ", ".join(self.config.to_addrs)

        smtp_cls = smtplib.SMTP
        with smtp_cls(self.config.smtp_host, self.config.smtp_port) as server:
            if self.config.use_tls:
                server.starttls()
            if self.config.smtp_user and self.config.smtp_password:
                server.login(self.config.smtp_user, self.config.smtp_password)
            server.sendmail(self.config.from_addr, self.config.to_addrs, msg.as_string())
