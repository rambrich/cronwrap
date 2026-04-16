"""Tests for cronwrap.metrics module."""
import json
import os
import tempfile

import pytest

from cronwrap.metrics import MetricsCollector, MetricsConfig, RunMetric
from cronwrap.runner import RunResult


def _make_result(exit_code: int = 0, duration: float = 1.5) -> RunResult:
    return RunResult(
        exit_code=exit_code,
        stdout="out",
        stderr="",
        duration_seconds=duration,
        attempts=1,
    )


def test_metrics_config_disabled_by_default(monkeypatch):
    monkeypatch.delenv("CRONWRAP_METRICS_FILE", raising=False)
    config = MetricsConfig.from_env()
    assert not config.enabled
    assert config.metrics_file is None


def test_metrics_config_enabled_from_env(monkeypatch, tmp_path):
    metrics_file = str(tmp_path / "metrics.jsonl")
    monkeypatch.setenv("CRONWRAP_METRICS_FILE", metrics_file)
    config = MetricsConfig.from_env()
    assert config.enabled
    assert config.metrics_file == metrics_file


def test_record_returns_metric():
    config = MetricsConfig(enabled=False)
    collector = MetricsCollector(config)
    result = _make_result(exit_code=0, duration=2.0)
    metric = collector.record("my-job", result, retries=1)
    assert isinstance(metric, RunMetric)
    assert metric.job_name == "my-job"
    assert metric.exit_code == 0
    assert metric.success is True
    assert metric.retries == 1
    assert metric.duration_seconds == 2.0


def test_record_failure_metric():
    config = MetricsConfig(enabled=False)
    collector = MetricsCollector(config)
    result = _make_result(exit_code=1)
    metric = collector.record("fail-job", result)
    assert metric.success is False


def test_record_appends_to_file(tmp_path):
    metrics_file = str(tmp_path / "metrics.jsonl")
    config = MetricsConfig(metrics_file=metrics_file, enabled=True)
    collector = MetricsCollector(config)
    collector.record("job-a", _make_result(exit_code=0))
    collector.record("job-b", _make_result(exit_code=1))
    lines = open(metrics_file).readlines()
    assert len(lines) == 2
    first = json.loads(lines[0])
    assert first["job_name"] == "job-a"
    assert first["success"] is True


def test_get_records_returns_all():
    config = MetricsConfig(enabled=False)
    collector = MetricsCollector(config)
    collector.record("j1", _make_result())
    collector.record("j2", _make_result())
    assert len(collector.get_records()) == 2
