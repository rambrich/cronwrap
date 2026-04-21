"""Tests for cronwrap.flap (flap detection)."""
import json
import pytest
from unittest.mock import MagicMock

from cronwrap.flap import FlapConfig, FlapDetector, FlapState
from cronwrap.runner import RunResult


def _result(exit_code: int = 0) -> RunResult:
    r = MagicMock(spec=RunResult)
    r.exit_code = exit_code
    r.stdout = ""
    r.stderr = ""
    r.duration = 1.0
    return r


@pytest.fixture
def tmp_config(tmp_path):
    return FlapConfig(enabled=True, window=5, threshold=3, state_dir=str(tmp_path))


def test_flap_config_disabled_by_default():
    cfg = FlapConfig()
    assert cfg.enabled is False


def test_flap_config_from_env(monkeypatch):
    monkeypatch.setenv("CRONWRAP_FLAP_ENABLED", "true")
    monkeypatch.setenv("CRONWRAP_FLAP_WINDOW", "6")
    monkeypatch.setenv("CRONWRAP_FLAP_THRESHOLD", "4")
    cfg = FlapConfig.from_env()
    assert cfg.enabled is True
    assert cfg.window == 6
    assert cfg.threshold == 4


def test_record_returns_none_when_disabled(tmp_config):
    tmp_config.enabled = False
    det = FlapDetector(tmp_config, "myjob")
    assert det.record(_result(0)) is None


def test_record_writes_state(tmp_config):
    det = FlapDetector(tmp_config, "myjob")
    state = det.record(_result(0))
    assert state is not None
    assert state.job == "myjob"
    assert state.outcomes == [True]


def test_not_flapping_on_all_success(tmp_config):
    det = FlapDetector(tmp_config, "stable")
    for _ in range(5):
        det.record(_result(0))
    assert not det.is_flapping()


def test_not_flapping_on_all_failure(tmp_config):
    det = FlapDetector(tmp_config, "broken")
    for _ in range(5):
        det.record(_result(1))
    assert not det.is_flapping()


def test_detects_flapping(tmp_config):
    det = FlapDetector(tmp_config, "flapy")
    # alternating success/failure => 4 alternations in 5 runs => flapping
    for i in range(5):
        det.record(_result(0 if i % 2 == 0 else 1))
    assert det.is_flapping()


def test_window_limits_history(tmp_config):
    tmp_config.window = 3
    det = FlapDetector(tmp_config, "windowed")
    # Push 10 successes, then record; only last 3 kept
    for _ in range(10):
        det.record(_result(0))
    state = det._load()
    assert len(state.outcomes) == 3


def test_reset_clears_state(tmp_config):
    det = FlapDetector(tmp_config, "resetme")
    det.record(_result(0))
    det.reset()
    assert not det._state_path().exists()


def test_is_flapping_false_when_disabled(tmp_config):
    tmp_config.enabled = False
    det = FlapDetector(tmp_config, "x")
    assert det.is_flapping() is False


def test_flap_state_round_trip():
    s = FlapState(job="j", outcomes=[True, False, True], flapping=True, updated_at=1234.0)
    d = s.to_dict()
    s2 = FlapState.from_dict(d)
    assert s2.job == "j"
    assert s2.outcomes == [True, False, True]
    assert s2.flapping is True
