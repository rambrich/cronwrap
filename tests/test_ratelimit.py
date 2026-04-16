"""Tests for cronwrap.ratelimit."""
import json
import time
import pytest
from unittest.mock import patch, MagicMock
from cronwrap.ratelimit import RateLimitConfig, RateLimiter


@pytest.fixture
def tmp_state(tmp_path):
    return str(tmp_path / "ratelimit.json")


def _config(tmp_state, enabled=True, window=3600, max_events=3):
    return RateLimitConfig(enabled=enabled, window_seconds=window, max_events=max_events, state_file=tmp_state)


def test_ratelimit_config_disabled_by_default():
    with patch.dict("os.environ", {}, clear=True):
        cfg = RateLimitConfig.from_env()
    assert cfg.enabled is False


def test_ratelimit_config_from_env(tmp_state):
    env = {
        "CRONWRAP_RATELIMIT_ENABLED": "true",
        "CRONWRAP_RATELIMIT_WINDOW": "1800",
        "CRONWRAP_RATELIMIT_MAX_EVENTS": "10",
        "CRONWRAP_RATELIMIT_STATE_FILE": tmp_state,
    }
    with patch.dict("os.environ", env):
        cfg = RateLimitConfig.from_env()
    assert cfg.enabled is True
    assert cfg.window_seconds == 1800
    assert cfg.max_events == 10


def test_allowed_when_disabled(tmp_state):
    cfg = _config(tmp_state, enabled=False)
    limiter = RateLimiter(cfg, "job1")
    for _ in range(20):
        assert limiter.is_allowed() is True


def test_allows_up_to_max_events(tmp_state):
    cfg = _config(tmp_state, max_events=3)
    limiter = RateLimiter(cfg, "job1")
    assert limiter.is_allowed() is True
    assert limiter.is_allowed() is True
    assert limiter.is_allowed() is True
    assert limiter.is_allowed() is False


def test_remaining_decrements(tmp_state):
    cfg = _config(tmp_state, max_events=3)
    limiter = RateLimiter(cfg, "job1")
    assert limiter.remaining() == 3
    limiter.is_allowed()
    assert limiter.remaining() == 2


def test_events_outside_window_ignored(tmp_state):
    cfg = _config(tmp_state, window=60, max_events=2)
    limiter = RateLimiter(cfg, "job1")
    old_time = time.time() - 120
    state = {"job1": [old_time, old_time]}
    import json
    from pathlib import Path
    Path(tmp_state).write_text(json.dumps(state))
    assert limiter.is_allowed() is True


def test_separate_jobs_independent(tmp_state):
    cfg = _config(tmp_state, max_events=1)
    l1 = RateLimiter(cfg, "job_a")
    l2 = RateLimiter(cfg, "job_b")
    assert l1.is_allowed() is True
    assert l1.is_allowed() is False
    assert l2.is_allowed() is True
