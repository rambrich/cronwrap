"""Tests for cronwrap.smoothing."""
import json
import pytest
from unittest.mock import patch
from cronwrap.smoothing import SmoothingConfig, SmoothingManager, SmoothingResult


@pytest.fixture
def tmp_config(tmp_path):
    return SmoothingConfig(enabled=True, alpha=0.5, state_dir=str(tmp_path))


def test_smoothing_config_disabled_by_default():
    cfg = SmoothingConfig()
    assert cfg.enabled is False


def test_smoothing_config_from_env():
    env = {
        "CRONWRAP_SMOOTHING_ENABLED": "true",
        "CRONWRAP_SMOOTHING_ALPHA": "0.2",
        "CRONWRAP_SMOOTHING_STATE_DIR": "/tmp/sm",
    }
    with patch.dict("os.environ", env):
        cfg = SmoothingConfig.from_env()
    assert cfg.enabled is True
    assert cfg.alpha == pytest.approx(0.2)
    assert cfg.state_dir == "/tmp/sm"


def test_smoothing_config_clamps_alpha():
    with patch.dict("os.environ", {"CRONWRAP_SMOOTHING_ALPHA": "5.0"}):
        cfg = SmoothingConfig.from_env()
    assert cfg.alpha == 1.0


def test_smoothing_config_invalid_alpha_defaults():
    with patch.dict("os.environ", {"CRONWRAP_SMOOTHING_ALPHA": "bad"}):
        cfg = SmoothingConfig.from_env()
    assert cfg.alpha == pytest.approx(0.3)


def test_update_returns_none_when_disabled(tmp_path):
    cfg = SmoothingConfig(enabled=False, state_dir=str(tmp_path))
    mgr = SmoothingManager(cfg)
    assert mgr.update("myjob", 10.0) is None


def test_update_first_sample_equals_duration(tmp_config):
    mgr = SmoothingManager(tmp_config)
    result = mgr.update("job1", 10.0)
    assert isinstance(result, SmoothingResult)
    assert result.smoothed_duration == pytest.approx(10.0)
    assert result.sample_count == 1
    assert result.raw_duration == pytest.approx(10.0)


def test_update_applies_ema(tmp_config):
    mgr = SmoothingManager(tmp_config)  # alpha=0.5
    mgr.update("job1", 10.0)
    result = mgr.update("job1", 20.0)
    # EMA: 0.5 * 20 + 0.5 * 10 = 15
    assert result.smoothed_duration == pytest.approx(15.0)
    assert result.sample_count == 2


def test_update_persists_state(tmp_config, tmp_path):
    mgr = SmoothingManager(tmp_config)
    mgr.update("job2", 5.0)
    state_files = list(tmp_path.iterdir())
    assert len(state_files) == 1
    data = json.loads(state_files[0].read_text())
    assert data["count"] == 1
    assert data["smoothed"] == pytest.approx(5.0)


def test_current_returns_none_when_disabled(tmp_path):
    cfg = SmoothingConfig(enabled=False, state_dir=str(tmp_path))
    mgr = SmoothingManager(cfg)
    assert mgr.current("job") is None


def test_current_returns_smoothed_value(tmp_config):
    mgr = SmoothingManager(tmp_config)
    mgr.update("job3", 8.0)
    assert mgr.current("job3") == pytest.approx(8.0)


def test_reset_removes_state(tmp_config, tmp_path):
    mgr = SmoothingManager(tmp_config)
    mgr.update("job4", 12.0)
    mgr.reset("job4")
    assert mgr.current("job4") is None


def test_result_to_dict(tmp_config):
    mgr = SmoothingManager(tmp_config)
    result = mgr.update("job5", 7.5)
    d = result.to_dict()
    assert d["job"] == "job5"
    assert d["raw_duration"] == pytest.approx(7.5)
    assert "smoothed_duration" in d
    assert d["sample_count"] == 1
