"""Orchestrates hooks, runner, retries, logging, metrics, and alerts."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List

from cronwrap.alerts import AlertManager
from cronwrap.history import HistoryStore
from cronwrap.hooks import HookManager
from cronwrap.logger import log_run_result
from cronwrap.metrics import MetricsCollector
from cronwrap.notifier import Notifier
from cronwrap.retry import RetryPolicy, run_with_retry
from cronwrap.runner import RunResult, run_command

logger = logging.getLogger(__name__)


@dataclass
class Pipeline:
    command: str
    retry_policy: RetryPolicy
    hook_manager: HookManager
    notifier: Notifier
    alert_manager: AlertManager
    metrics_collector: MetricsCollector
    history_store: HistoryStore
    job_name: str = "cron-job"

    def execute(self) -> RunResult:
        logger.info("[%s] Starting job: %s", self.job_name, self.command)

        pre_results = self.hook_manager.run_pre_hooks()
        if pre_results and not all(pre_results):
            logger.warning("[%s] Some pre-hooks failed", self.job_name)

        result = run_with_retry(
            command=self.command,
            policy=self.retry_policy,
            runner=run_command,
        )

        log_run_result(logger, result)
        self.metrics_collector.record(result)
        self.history_store.record(result)
        self.alert_manager.evaluate(result)
        self.notifier.notify(result)

        self.hook_manager.run_post_hooks(result)

        logger.info(
            "[%s] Finished — exit_code=%s duration=%.2fs",
            self.job_name,
            result.exit_code,
            result.duration,
        )
        return result
