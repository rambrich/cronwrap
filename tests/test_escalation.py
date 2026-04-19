import json
import pytest
from cronwrap.escalation import EscalationConfig, EscalationManager
from cronwrap.runner import RunResult


def _result(success: bool) -> RunResult:
    return RunResult(command="echo hi", returncode=0 if success else 1,
                     stdout="", stderr="", duration=1.0, success=success,
                     attempts=1)


@pytest.fixture
def tmp_config(tmp_path):
    return EscalationConfig(
        enabled=True, threshold=3,
        recipients=["ops@example.com"],
        state_file=str(tmp_path / "esc.json")
    )


def test_config_disabled_by_default():
    cfg = EscalationConfig()
    assert not cfg.enabled


def test_config_from_env(monkeypatch):
    monkeypatch.setenv("CRONWRAP_ESCALATION_ENABLED", "true")
    monkeypatch.setenv("CRONWRAP_ESCALATION_THRESHOLD", "5")
    monkeypatch.setenv("CRONWRAP_ESCALATION_RECIPIENTS", "a@b.com,c@d.com")
    cfg = EscalationConfig.from_env()
    assert cfg.enabled
    assert cfg.threshold == 5
    assert cfg.recipients == ["a@b.com", "c@d.com"]


def test_record_noop_when_disabled(tmp_path):
    cfg = EscalationConfig(enabled=False, state_file=str(tmp_path / "esc.json"))
    mgr = EscalationManager(cfg)
    mgr.record(_result(False), "echo hi")
    assert not (tmp_path / "esc.json").exists()


def test_consecutive_failures_increments(tmp_config):
    mgr = EscalationManager(tmp_config)
    mgr.record(_result(False), "echo hi")
    mgr.record(_result(False), "echo hi")
    assert mgr.consecutive_failures("echo hi") == 2


def test_success_resets_count(tmp_config):
    mgr = EscalationManager(tmp_config)
    mgr.record(_result(False), "echo hi")
    mgr.record(_result(True), "echo hi")
    assert mgr.consecutive_failures("echo hi") == 0


def test_should_escalate_after_threshold(tmp_config):
    mgr = EscalationManager(tmp_config)
    for _ in range(3):
        mgr.record(_result(False), "echo hi")
    assert mgr.should_escalate("echo hi")


def test_should_not_escalate_below_threshold(tmp_config):
    mgr = EscalationManager(tmp_config)
    for _ in range(2):
        mgr.record(_result(False), "echo hi")
    assert not mgr.should_escalate("echo hi")


def test_reset_clears_state(tmp_config):
    mgr = EscalationManager(tmp_config)
    mgr.record(_result(False), "echo hi")
    mgr.reset("echo hi")
    assert mgr.consecutive_failures("echo hi") == 0


def test_state_persists_across_instances(tmp_config):
    mgr1 = EscalationManager(tmp_config)
    mgr1.record(_result(False), "echo hi")
    mgr1.record(_result(False), "echo hi")
    mgr2 = EscalationManager(tmp_config)
    assert mgr2.consecutive_failures("echo hi") == 2
