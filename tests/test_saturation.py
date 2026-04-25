"""Tests for cronwrap.saturation."""
import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from cronwrap.saturation import SaturationConfig, SaturationManager, SaturationResult


def _result(duration: float = 1.0, exit_code: int = 0) -> MagicMock:
    r = MagicMock()
    r.duration = duration
    r.exit_code = exit_code
    return r


@pytest.fixture()
def tmp_config(tmp_path):
    return SaturationConfig(
        enabled=True,
        window=5,
        threshold=0.80,
        max_duration=10.0,
        state_dir=str(tmp_path / "saturation"),
    )


def test_saturation_config_disabled_by_default():
    cfg = SaturationConfig()
    assert cfg.enabled is False


def test_saturation_config_from_env(monkeypatch):
    monkeypatch.setenv("CRONWRAP_SATURATION_ENABLED", "true")
    monkeypatch.setenv("CRONWRAP_SATURATION_WINDOW", "8")
    monkeypatch.setenv("CRONWRAP_SATURATION_THRESHOLD", "0.75")
    monkeypatch.setenv("CRONWRAP_SATURATION_MAX_DURATION", "60")
    cfg = SaturationConfig.from_env()
    assert cfg.enabled is True
    assert cfg.window == 8
    assert cfg.threshold == 0.75
    assert cfg.max_duration == 60.0


def test_record_returns_none_when_disabled(tmp_path):
    cfg = SaturationConfig(enabled=False, state_dir=str(tmp_path))
    mgr = SaturationManager(config=cfg)
    assert mgr.record(_result(5.0)) is None


def test_record_returns_result(tmp_config):
    mgr = SaturationManager(config=tmp_config)
    res = mgr.record(_result(5.0))
    assert isinstance(res, SaturationResult)
    assert res.sample_count == 1


def test_not_saturated_below_threshold(tmp_config):
    mgr = SaturationManager(config=tmp_config)
    # avg = 5.0, ceiling = 10.0, ratio = 0.5 < 0.80
    res = mgr.record(_result(5.0))
    assert res.saturated is False
    assert pytest.approx(res.ratio, abs=1e-3) == 0.5


def test_saturated_at_or_above_threshold(tmp_config):
    mgr = SaturationManager(config=tmp_config)
    # avg = 9.0, ceiling = 10.0, ratio = 0.9 >= 0.80
    res = mgr.record(_result(9.0))
    assert res.saturated is True


def test_history_persisted_to_disk(tmp_config):
    mgr = SaturationManager(config=tmp_config)
    mgr.record(_result(3.0))
    mgr.record(_result(4.0))
    state_file = Path(tmp_config.state_dir) / "history.json"
    assert state_file.exists()
    data = json.loads(state_file.read_text())
    assert data == [3.0, 4.0]


def test_history_loaded_on_init(tmp_config):
    mgr1 = SaturationManager(config=tmp_config)
    mgr1.record(_result(7.0))
    # second manager reads persisted state
    mgr2 = SaturationManager(config=tmp_config)
    assert 7.0 in mgr2._history


def test_reset_clears_history(tmp_config):
    mgr = SaturationManager(config=tmp_config)
    mgr.record(_result(8.0))
    mgr.reset()
    assert mgr._history == []
    state_file = Path(tmp_config.state_dir) / "history.json"
    assert not state_file.exists()


def test_to_dict_keys(tmp_config):
    mgr = SaturationManager(config=tmp_config)
    res = mgr.record(_result(6.0))
    d = res.to_dict()
    assert set(d.keys()) == {"saturated", "ratio", "avg_duration", "ceiling", "sample_count"}


def test_window_limits_sample_count(tmp_config):
    mgr = SaturationManager(config=tmp_config)
    for i in range(10):
        res = mgr.record(_result(float(i + 1)))
    # window=5, so only last 5 samples used
    assert res.sample_count == 5
